import requests
import time
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
ODDS_API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

# ===== 全局 =====
history = {}          # 最新盤
timeline = {}         # 時間軌跡
open_line = {}        # 初盤
game_dates = {}       # 比賽日期

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== 抓全部盤 =====
def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "totals"
    }

    data = requests.get(url, params=params).json()
    games = []

    for g in data:
        match = f"{g['away_team']} vs {g['home_team']}"

        date = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).date()
        game_dates[match] = date

        total = None
        for b in g["bookmakers"]:
            for m in b["markets"]:
                if m["key"] == "totals":
                    total = m["outcomes"][0]["point"]

        if total:
            games.append({
                "match": match,
                "total": total
            })

    return games

# ===== 判斷是否隔天 =====
def is_tomorrow(match):
    if match not in game_dates:
        return False
    return game_dates[match] == (datetime.utcnow() + timedelta(days=1)).date()

# ===== 核心監控 =====
def monitor():
    games = fetch_odds()

    for g in games:
        match = g["match"]
        total = g["total"]
        now = datetime.now().strftime("%H:%M")

        # ===== 初盤 =====
        if match not in open_line:
            open_line[match] = total
            history[match] = total
            timeline[match] = [f"初盤:{total}"]

            continue

        prev = history.get(match)

        if prev is not None:
            diff = abs(total - prev)

            # ===== 變盤 =====
            if diff >= 1:
                timeline[match].append(f"{now}:{total}")

                # ===== 只通知隔天 =====
                if is_tomorrow(match):
                    msg = f"📊 變盤\n{match}\n"
                    msg += "\n".join(timeline[match][-5:])  # 最近5筆
                    send(msg)

        history[match] = total

# ===== 分析（只隔天）=====
def analyze():
    msg = "📊 明日完整盤口軌跡\n\n"

    found = False

    for match in timeline:
        if not is_tomorrow(match):
            continue

        found = True

        msg += f"{match}\n"
        msg += "\n".join(timeline[match]) + "\n\n"

    if not found:
        msg += "無資料"

    send(msg)

# ===== 排程 =====
def run():
    now = datetime.now().strftime("%H:%M")

    # 20:00 發分析（只明天）
    if now == "20:00":
        analyze()

# ===== 啟動 =====
if __name__ == "__main__":
    send("🚀 盤口監控 + 初盤系統啟動")

    while True:
        monitor()
        run()
        time.sleep(60)
