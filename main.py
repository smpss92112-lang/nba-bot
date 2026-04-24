import requests
import time
from datetime import datetime, timedelta

# ===== KEY =====
BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
ODDS_API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

history = {}
movement_log = {}

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
    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "spreads,totals"}

    data = requests.get(url, params=params).json()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date()

    games = []

    for g in data:
        game_date = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).date()
        if game_date != tomorrow:
            continue

        home = normalize(g["home_team"])
        away = normalize(g["away_team"])

        spread = None
        total = None

        for b in g["bookmakers"]:
            for m in b["markets"]:
                if m["key"] == "spreads":
                    spread = m["outcomes"][0]["point"]
                if m["key"] == "totals":
                    total = m["outcomes"][0]["point"]

        if spread and total:
            games.append({"match": f"{away} vs {home}", "spread": spread, "total": total})

    return games

# ===== 盤口紀錄 =====
def track(game):
    now = datetime.now().strftime("%H:%M")

    if game["match"] not in movement_log:
        movement_log[game["match"]] = []

    prev = history.get(game["match"])

    if prev is not None and prev != game["spread"]:
        movement_log[game["match"]].append(f"{now} {prev}→{game['spread']}")

    history[game["match"]] = game["spread"]

# ===== 模型 =====
def model(game):
    score = 0

    if game["total"] >= 226:
        score += 2
    elif game["total"] <= 210:
        score -= 2

    if game["spread"] <= -8:
        score -= 1

    moves = movement_log.get(game["match"], [])
    if len(moves) >= 2:
        score += 2

    if score >= 4:
        return "主推", 1.5
    elif score >= 2:
        return "次推", 1
    else:
        return "觀望", 0

# ===== 模擬結算（簡化）=====
def settle(unit):
    # 隨機模擬勝負（你之後可接真比分）
    import random
    return unit if random.random() > 0.5 else -unit

# ===== 主流程 =====
def run():
    global weekly_profit, monthly_profit, current_week, current_month

    now = datetime.now()
    week = now.isocalendar()[1]
    month = now.month

    # ===== 重置 =====
    if week != current_week:
        weekly_profit = 0
        current_week = week

    if month != current_month:
        monthly_profit = 0
        current_month = month

    games = fetch_odds()

    msg = "📊 今日分析\n\n"

    for g in games:
        track(g)

        level, unit = model(g)

        if unit > 0:
            result = settle(unit)
            weekly_profit += result
            monthly_profit += result

        msg += f"{g['match']}\n"
        msg += f"{level} {unit}U\n\n"

    msg += f"📈 本週: {round(weekly_profit,2)}U\n"
    msg += f"📊 本月: {round(monthly_profit,2)}U\n"

    send(msg)

# ===== 啟動 =====
if __name__ == "__main__":
    send("🚀 最終交易系統啟動")

    while True:
        run()
        time.sleep(600)
