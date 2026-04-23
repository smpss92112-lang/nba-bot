import requests
import time
from datetime import datetime

API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"
BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"

URL = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/?apiKey={API_KEY}&regions=us&markets=spreads,totals"

previous_data = {}
history = {}
daily_log = []

team_map = {
    "Oklahoma City Thunder": "雷霆",
    "Phoenix Suns": "太陽",
    "Los Angeles Lakers": "湖人",
    "Houston Rockets": "火箭",
    "Boston Celtics": "塞爾提克",
    "Philadelphia 76ers": "76人",
}

def send(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg})

def analyze(away, home, old_spread, spread, total, game_id):
    score = 0
    tags = []

    diff = spread - old_spread

    if abs(spread) >= 10:
        tags.append("深盤")
        score += 2

    if diff >= 1.5:
        tags.append("拉盤")
        score += 1

    if game_id in history:
        if abs(history[game_id] - spread) >= 1.5:
            tags.append("洗盤")
            score += 2

    history[game_id] = spread

    if total:
        if total <= 210:
            tags.append("小分盤")
            score += 2
        elif total >= 225:
            tags.append("大分盤")
            score += 1

    return score, tags


def daily_summary():
    if not daily_log:
        return

    sorted_games = sorted(daily_log, key=lambda x: x["score"], reverse=True)[:3]

    msg = "📊 今日盤口總結\n\n"

    for i, g in enumerate(sorted_games, 1):
        msg += f"{i}️⃣ {g['match']}\n"
        msg += f"→ {' / '.join(g['tags'])}\n\n"

    msg += "━━━━━━━━━━━━━━\n"
    msg += "🎯 今日策略\n"

    msg += "✔ 主打：小分\n"
    msg += "✔ 次選：受讓\n"
    msg += "❌ 避開：深盤讓分\n"

    send(msg)


print("🔥 V9系統啟動")

last_sent_date = None

while True:
    res = requests.get(URL)

    if res.status_code != 200:
        time.sleep(60)
        continue

    data = res.json()

    for game in data:
        game_id = game['id']
        home = game['home_team']
        away = game['away_team']

        spread = None
        total = None

        for b in game['bookmakers']:
            for m in b['markets']:
                if m['key'] == 'spreads':
                    spread = m['outcomes'][0]['point']
                if m['key'] == 'totals':
                    total = m['outcomes'][0]['point']

        if spread is None:
            continue

        if game_id in previous_data:
            old_spread = previous_data[game_id]['spread']
            old_total = previous_data[game_id]['total']

            if old_spread != spread or old_total != total:

                score, tags = analyze(away, home, old_spread, spread, total, game_id)

                match = f"{team_map.get(away, away)} vs {team_map.get(home, home)}"

                daily_log.append({
                    "match": match,
                    "score": score,
                    "tags": tags
                })

        previous_data[game_id] = {
            "spread": spread,
            "total": total
        }

    # 🕗 晚上8點發送
    now = datetime.now()

    if now.hour == 20:
        if last_sent_date != now.date():
            daily_summary()
            last_sent_date = now.date()

    time.sleep(60)