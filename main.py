import requests
import time
import os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

# ===== 中文隊名 =====
team_map = {
    "Los Angeles Lakers": "湖人",
    "Golden State Warriors": "勇士",
    "Boston Celtics": "塞爾提克",
    "Miami Heat": "熱火",
    "Denver Nuggets": "金塊",
    "Phoenix Suns": "太陽",
}

# ===== Telegram =====
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== 抓NBA盤口 =====
def get_odds():
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "spreads,totals",
    }

    res = requests.get(url, params=params).json()

    games = []

    for game in res:
        home = team_map.get(game["home_team"], game["home_team"])
        away = team_map.get(game["away_team"], game["away_team"])

        for book in game["bookmakers"]:
            for market in book["markets"]:
                if market["key"] == "spreads":
                    spread = market["outcomes"][0]["point"]
                if market["key"] == "totals":
                    total = market["outcomes"][0]["point"]

        games.append({
            "match": f"{away} vs {home}",
            "spread": spread,
            "total": total
        })

    return games

# ===== 模擬傷兵（你之後可升級）=====
def get_injury(team):
    # 可改接API
    if "湖人" in team:
        return "主力出戰成疑"
    return "正常"

# ===== 分析 =====
def analyze(game):
    score = 0
    reasons = []

    # 節奏
    if game["total"] > 225:
        score += 1
        reasons.append("節奏偏快")

    # 讓分
    if game["spread"] < -6:
        score -= 1
        reasons.append("讓分過深")

    # 傷兵
    injury = get_injury(game["match"])
    if "成疑" in injury:
        score -= 1
        reasons.append("主力不確定")

    # 推薦
    if score >= 1:
        pick = "🔥 推薦：大分"
    elif score <= -1:
        pick = "🔥 推薦：小分"
    else:
        pick = "⚠️ 觀望"

    return pick, reasons, injury

# ===== 主流程 =====
def run():
    games = get_odds()

    msg = "📊 NBA完整分析\n\n"

    for g in games:
        pick, reasons, injury = analyze(g)

        msg += f"🏀 {g['match']}\n"
        msg += f"讓分: {g['spread']} | 大小: {g['total']}\n"
        msg += f"🩺 傷兵: {injury}\n"
        msg += f"📈 判斷: {', '.join(reasons)}\n"
        msg += f"{pick}\n\n"

    send(msg)

# ===== 定時 =====
def scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")

        if now == "20:00":
            run()
            time.sleep(60)

        time.sleep(30)

# ===== 啟動 =====
if __name__ == "__main__":
    send("🚀 最強分析系統啟動")
    scheduler()
