import requests
import time
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
ODDS_API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

history = {}
movement_log = {}
picks = []

weekly_profit = 0
monthly_profit = 0

current_week = datetime.now().isocalendar()[1]
current_month = datetime.now().month

TEAM_MAP = {
    "Los Angeles Lakers": "湖人",
    "Houston Rockets": "火箭",
    "San Antonio Spurs": "馬刺",
    "Portland Trail Blazers": "拓荒者",
    "Detroit Pistons": "活塞",
    "Orlando Magic": "魔術",
    "Oklahoma City Thunder": "雷霆",
    "Phoenix Suns": "太陽"
}

def normalize(name):
    return TEAM_MAP.get(name, name)

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== 抓盤 =====
def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "totals"}

    data = requests.get(url, params=params).json()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date()

    games = []

    for g in data:
        game_date = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).date()
        if game_date != tomorrow:
            continue

        home = normalize(g["home_team"])
        away = normalize(g["away_team"])

        total = None

        for b in g["bookmakers"]:
            for m in b["markets"]:
                if m["key"] == "totals":
                    total = m["outcomes"][0]["point"]

        if total:
            games.append({
                "match": f"{away} vs {home}",
                "total": total
            })

    return games

# ===== 模型 =====
def model(game):
    if game["total"] >= 226:
        return "大分", 1.5
    elif game["total"] <= 210:
        return "小分", 1.5
    else:
        return "觀望", 0

# ===== 分析 =====
def analyze():
    global picks

    games = fetch_odds()
    picks = []

    msg = "📊 明日下注\n\n"

    for g in games:
        direction, unit = model(g)

        if unit > 0:
            picks.append({
                "match": g["match"],
                "line": g["total"],
                "pick": direction,
                "unit": unit
            })

        msg += f"{g['match']}\n"
        msg += f"{direction} ({g['total']}) {unit}U\n\n"

    send(msg)

# ===== 抓比分 =====
def fetch_results():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    data = requests.get(url).json()

    results = {}

    for e in data["events"]:
        t = e["competitions"][0]["competitors"]

        home = normalize(t[0]["team"]["displayName"])
        away = normalize(t[1]["team"]["displayName"])

        total_score = int(t[0]["score"]) + int(t[1]["score"])

        results[f"{away} vs {home}"] = total_score

    return results

# ===== 結算 =====
def settle():
    global weekly_profit, monthly_profit

    results = fetch_results()

    msg = "📊 今日結算\n\n"

    for p in picks:
        match = p["match"]

        if match not in results:
            continue

        score = results[match]

        if p["pick"] == "大分":
            win = score > p["line"]
        else:
            win = score < p["line"]

        result = p["unit"] if win else -p["unit"]

        weekly_profit += result
        monthly_profit += result

        msg += f"{match}\n"
        msg += f"{p['pick']} {p['line']}\n"
        msg += f"比分:{score}\n"
        msg += f"{'✅贏' if win else '❌輸'} {result}U\n\n"

    msg += f"📈 本週: {round(weekly_profit,2)}U\n"
    msg += f"📊 本月: {round(monthly_profit,2)}U\n"

    send(msg)

# ===== 主控 =====
def run():
    now = datetime.now().strftime("%H:%M")

    if now == "20:00":
        analyze()

    if now == "12:00":
        settle()

# ===== 啟動 =====
if __name__ == "__main__":
    send("🚀 100%交易系統啟動")

    while True:
        run()
        time.sleep(30)
