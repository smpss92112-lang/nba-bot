import requests
import time
import os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

previous_odds = {}
yesterday_picks = []

# ===== 中文隊名 =====
TEAM_MAP = {
    "Los Angeles Lakers": "湖人",
    "Golden State Warriors": "勇士",
    "Boston Celtics": "塞爾提克",
    "Miami Heat": "熱火",
    "Denver Nuggets": "金塊",
    "Phoenix Suns": "太陽",
    "Milwaukee Bucks": "公鹿",
    "Dallas Mavericks": "獨行俠",
    "Philadelphia 76ers": "76人",
    "LA Clippers": "快艇",
    "New York Knicks": "尼克",
    "Chicago Bulls": "公牛",
    "Cleveland Cavaliers": "騎士",
    "Atlanta Hawks": "老鷹",
    "Toronto Raptors": "暴龍"
}

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== 抓盤（只抓隔天）=====
def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "spreads,totals",
    }

    data = requests.get(url, params=params).json()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date()

    games = []

    for game in data:
        game_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).date()

        if game_time != tomorrow:
            continue

        home = TEAM_MAP.get(game["home_team"], game["home_team"])
        away = TEAM_MAP.get(game["away_team"], game["away_team"])

        spread = None
        total = None

        for book in game["bookmakers"]:
            for market in book["markets"]:
                if market["key"] == "spreads":
                    spread = market["outcomes"][0]["point"]
                if market["key"] == "totals":
                    total = market["outcomes"][0]["point"]

        if spread and total:
            games.append({
                "match": f"{away} vs {home}",
                "spread": spread,
                "total": total
            })

    return games

# ===== 分析 =====
def analyze(game):
    score = 0
    notes = []

    if game["total"] >= 225:
        score += 1
        notes.append("快節奏 → 大分")

    if game["total"] <= 210:
        score -= 1
        notes.append("慢節奏 → 小分")

    if game["spread"] <= -8:
        score -= 1
        notes.append("深盤風險")

    if score >= 1:
        pick = "大分"
    elif score <= -1:
        pick = "小分"
    else:
        pick = "觀望"

    return pick, notes

# ===== 推薦 =====
def run_analysis():
    global yesterday_picks

    games = fetch_odds()

    if not games:
        send("⚠️ 明日無賽事或抓取失敗")
        return

    msg = "📊 明日NBA分析\n\n"
    picks = []

    for g in games:
        pick, notes = analyze(g)

        msg += f"{g['match']}\n"
        msg += f"讓分:{g['spread']} | 大小:{g['total']}\n"
        msg += f"分析:{','.join(notes)}\n"
        msg += f"👉 推薦:{pick}\n\n"

        picks.append({"match": g["match"], "pick": pick})

    yesterday_picks = picks
    send(msg)

# ===== 抓比分 =====
def fetch_results():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    data = requests.get(url).json()

    results = []

    for event in data["events"]:
        teams = event["competitions"][0]["competitors"]

        home = teams[0]["team"]["displayName"]
        away = teams[1]["team"]["displayName"]

        home_score = teams[0]["score"]
        away_score = teams[1]["score"]

        results.append({
            "match": f"{away} vs {home}",
            "score": f"{away_score}-{home_score}"
        })

    return results

# ===== 復盤 =====
def review():
    if not yesterday_picks:
        return

    results = fetch_results()

    msg = "📊 昨日復盤\n\n"

    for pick in yesterday_picks:
        match = pick["match"]
        result = next((r for r in results if match.split(" vs ")[0] in r["match"]), None)

        if not result:
            continue

        msg += f"{match}\n"
        msg += f"推薦:{pick['pick']}\n"
        msg += f"比分:{result['score']}\n"

        msg += "檢討: 需加強盤口與節奏判斷\n\n"

    send(msg)

# ===== 定時 =====
def scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")

        if now == "20:00":
            run_analysis()
            time.sleep(60)

        if now == "10:00":
            review()
            time.sleep(60)

        time.sleep(30)

# ===== 啟動 =====
if __name__ == "__main__":
    send("🚀 最終職業系統啟動")
    run_analysis()
    scheduler()
