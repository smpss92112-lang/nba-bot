import requests
import time
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

歷史盤 = {}
初盤 = {}
比賽時間 = {}

最後回報時間 = None

# ===== 發送 =====
def 發送(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg})

# ===== 抓盤 =====
def 抓盤():
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    data = requests.get(url, params={
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "totals"
    }).json()

    games = []

    for g in data:
        match = f"{g['away_team']} vs {g['home_team']}"
        time_ = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00"))
        比賽時間[match] = time_

        total = None
        for b in g["bookmakers"]:
            for m in b["markets"]:
                if m["key"] == "totals":
                    total = m["outcomes"][0]["point"]

        if total:
            games.append({"match": match, "total": total})

    return games

# ===== 是否已開賽 =====
def 已開賽(match):
    return datetime.utcnow() > 比賽時間.get(match)

# ===== 即時監控 =====
def 監控():
    games = 抓盤()

    for g in games:
        m = g["match"]
        t = g["total"]

        if 已開賽(m):
            continue

        if m not in 初盤:
            初盤[m] = t
            歷史盤[m] = t
            continue

        diff = t - 歷史盤[m]

        if abs(diff) >= 1:
            發送(f"📊變盤\n{m}\n{歷史盤[m]} → {t}")

        歷史盤[m] = t

# ===== 定時回報 =====
def 定時回報():
    global 最後回報時間

    now = datetime.now()

    if 最後回報時間 is None:
        最後回報時間 = now
        return

    hours = (now - 最後回報時間).seconds / 3600

    # 白天2小時
    if 10 <= now.hour < 22:
        if hours < 2:
            return
    else:
        # 晚上4小時
        if hours < 4:
            return

    games = 抓盤()

    msg = "📊盤口回報\n\n"

    for g in games:
        m = g["match"]
        t = g["total"]

        if 已開賽(m):
            continue

        msg += f"{m}\n"
        msg += f"初盤:{初盤.get(m,'-')}\n"
        msg += f"目前:{t}\n\n"

    發送(msg)
    最後回報時間 = now

# ===== 啟動訊息 =====
def 啟動():
    games = 抓盤()

    msg = "🚀 系統啟動\n\n目前監控賽事：\n"

    for g in games:
        msg += f"{g['match']}（{g['total']}）\n"

    發送(msg)

# ===== 主程式 =====
if __name__ == "__main__":
    啟動()

    while True:
        監控()
        定時回報()
        time.sleep(60)
