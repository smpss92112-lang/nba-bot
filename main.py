import time
from datetime import datetime, timedelta

# ===== 🔥 你的KEY（已填）=====
# ===== KEY =====
BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
ODDS_API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

history = {}
movement_log = {}

# ===== 中文隊名 =====
weekly_profit = 0
monthly_profit = 0

current_week = datetime.now().isocalendar()[1]
current_month = datetime.now().month

TEAM_MAP = {
    "Atlanta Hawks": "老鷹","Boston Celtics": "塞爾提克","Brooklyn Nets": "籃網",
    "Charlotte Hornets": "黃蜂","Chicago Bulls": "公牛","Cleveland Cavaliers": "騎士",
    "Dallas Mavericks": "獨行俠","Denver Nuggets": "金塊","Detroit Pistons": "活塞",
    "Golden State Warriors": "勇士","Houston Rockets": "火箭","Indiana Pacers": "溜馬",
    "LA Clippers": "快艇","Los Angeles Clippers": "快艇","Los Angeles Lakers": "湖人",
    "Memphis Grizzlies": "灰熊","Miami Heat": "熱火","Milwaukee Bucks": "公鹿",
    "Minnesota Timberwolves": "灰狼","New Orleans Pelicans": "鵜鶘",
    "New York Knicks": "尼克","Oklahoma City Thunder": "雷霆","Orlando Magic": "魔術",
    "Philadelphia 76ers": "76人","Phoenix Suns": "太陽","Portland Trail Blazers": "拓荒者",
    "Sacramento Kings": "國王","San Antonio Spurs": "馬刺","Toronto Raptors": "暴龍",
    "Utah Jazz": "爵士","Washington Wizards": "巫師"
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
@@ -32,7 +34,7 @@ def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== 抓明日盤 =====
# ===== 抓盤 =====
def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {"apiKey": ODDS_API_KEY, "regions": "us", "markets": "spreads,totals"}
@@ -66,7 +68,7 @@ def fetch_odds():
    return games

# ===== 盤口紀錄 =====
def track_movement(game):
def track(game):
    now = datetime.now().strftime("%H:%M")

    if game["match"] not in movement_log:
@@ -75,147 +77,81 @@ def track_movement(game):
    prev = history.get(game["match"])

    if prev is not None and prev != game["spread"]:
        movement_log[game["match"]].append(
            f"{now} {prev} → {game['spread']}"
        )
        movement_log[game["match"]].append(f"{now} {prev}→{game['spread']}")

    history[game["match"]] = game["spread"]

# ===== 傷兵 =====
def injury_signal(team):
    try:
        data = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries").json()
    except:
        return 0, "傷兵未知"

    impact = 0
    notes = []

    for t in data.get("teams", []):
        if normalize(t["team"]["displayName"]) in team:
            for p in t.get("injuries", []):
                if p["status"] == "Out":
                    impact -= 1
                    notes.append("❌主力缺席")
                elif p["status"] == "Questionable":
                    notes.append("⚠️不確定")

    return impact, " / ".join(notes) if notes else "完整"

# ===== 資金流模型 =====
def money_flow(game):
    notes = []
    score = 0

    moves = movement_log.get(game["match"], [])

    if len(moves) < 2:
        return 0, []

    try:
        first = float(moves[0].split()[1])
        last = float(moves[-1].split()[-1])
    except:
        return 0, []

    diff = last - first

    if diff > 0:
        notes.append("🔴市場順盤")
        score -= 1

    if diff < 0:
        notes.append("🟢逆盤（莊家方向）")
        score += 2

    if abs(diff) >= 2:
        notes.append("🟡誘盤")
        score -= 1

    if len(moves) >= 3:
        notes.append("🔥殺盤")
        score += 1

    return score, notes

# ===== 分析模型 =====
# ===== 模型 =====
def model(game):
    score = 0
    notes = []

    # 節奏
    if game["total"] >= 226:
        score += 2
        notes.append("快節奏")
    elif game["total"] <= 210:
        score -= 2
        notes.append("慢節奏")

    # 深盤
    if game["spread"] <= -8:
        score -= 1
        notes.append("深盤")

    # 傷兵
    inj_score, inj_note = injury_signal(game["match"])
    score += inj_score
    notes.append(inj_note)

    # 變盤
    moves = movement_log.get(game["match"], [])
    if len(moves) >= 2:
        score += 2
        notes.append("連續變盤")

    # 資金流
    flow_score, flow_notes = money_flow(game)
    score += flow_score
    notes += flow_notes

    # 分級
    if score >= 4:
        level = "🔥主推"
        return "主推", 1.5
    elif score >= 2:
        level = "👉次推"
    elif score <= -2:
        level = "❌避開"
        return "次推", 1
    else:
        level = "⚠️觀望"
        return "觀望", 0

    return level, score, notes
# ===== 模擬結算（簡化）=====
def settle(unit):
    # 隨機模擬勝負（你之後可接真比分）
    import random
    return unit if random.random() > 0.5 else -unit

# ===== 主流程 =====
def run():
    games = fetch_odds()
    global weekly_profit, monthly_profit, current_week, current_month

    now = datetime.now()
    week = now.isocalendar()[1]
    month = now.month

    if not games:
        send("⚠️ 無明日賽事")
        return
    # ===== 重置 =====
    if week != current_week:
        weekly_profit = 0
        current_week = week

    msg = "📊 NBA職業最終分析\n\n"
    if month != current_month:
        monthly_profit = 0
        current_month = month

    games = fetch_odds()

    msg = "📊 今日分析\n\n"

    for g in games:
        track_movement(g)
        level, score, notes = model(g)
        track(g)

        msg += f"{g['match']}\n"
        msg += f"讓分:{g['spread']} | 大小:{g['total']}\n"
        level, unit = model(g)

        if unit > 0:
            result = settle(unit)
            weekly_profit += result
            monthly_profit += result

        moves = movement_log.get(g["match"], [])
        if moves:
            msg += "變盤紀錄:\n"
            for m in moves[-5:]:
                msg += f"  {m}\n"
        msg += f"{g['match']}\n"
        msg += f"{level} {unit}U\n\n"

        msg += f"信心:{score}\n"
        msg += f"原因:{' | '.join(notes)}\n"
        msg += f"{level}\n\n"
    msg += f"📈 本週: {round(weekly_profit,2)}U\n"
    msg += f"📊 本月: {round(monthly_profit,2)}U\n"

    send(msg)

# ===== 啟動 =====
if __name__ == "__main__":
    send("🚀 FINAL系統啟動")
    send("🚀 最終交易系統啟動")

    while True:
        run()
