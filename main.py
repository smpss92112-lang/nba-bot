import requests
import time
from datetime import datetime, timedelta

# ===== 🔥 直接寫死 =====
BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
ODDS_API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

history = {}
yesterday_picks = []

# ===== 中文隊名 =====
TEAM_MAP = {
    "Atlanta Hawks": "老鷹",
    "Boston Celtics": "塞爾提克",
    "Brooklyn Nets": "籃網",
    "Charlotte Hornets": "黃蜂",
    "Chicago Bulls": "公牛",
    "Cleveland Cavaliers": "騎士",
    "Dallas Mavericks": "獨行俠",
    "Denver Nuggets": "金塊",
    "Detroit Pistons": "活塞",
    "Golden State Warriors": "勇士",
    "Houston Rockets": "火箭",
    "Indiana Pacers": "溜馬",
    "LA Clippers": "快艇",
    "Los Angeles Clippers": "快艇",
    "Los Angeles Lakers": "湖人",
    "Memphis Grizzlies": "灰熊",
    "Miami Heat": "熱火",
    "Milwaukee Bucks": "公鹿",
    "Minnesota Timberwolves": "灰狼",
    "New Orleans Pelicans": "鵜鶘",
    "New York Knicks": "尼克",
    "Oklahoma City Thunder": "雷霆",
    "Orlando Magic": "魔術",
    "Philadelphia 76ers": "76人",
    "Phoenix Suns": "太陽",
    "Portland Trail Blazers": "拓荒者",
    "Sacramento Kings": "國王",
    "San Antonio Spurs": "馬刺",
    "Toronto Raptors": "暴龍",
    "Utah Jazz": "爵士",
    "Washington Wizards": "巫師"
}

def normalize(name):
    return TEAM_MAP.get(name, name)

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== 抓明日盤 =====
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

# ===== 傷兵 =====
def get_injury(team):
    try:
        data = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries").json()
    except:
        return 0, "傷兵未知"

    impact = 0
    notes = []

    for t in data.get("teams", []):
        team_name = normalize(t["team"]["displayName"])

        if team_name in team:
            for p in t.get("injuries", []):
                status = p["status"]

                if status == "Out":
                    impact -= 1
                    notes.append("❌主力缺席")

                elif status == "Questionable":
                    notes.append("⚠️出賽不確定")

    return impact, " / ".join(notes) if notes else "陣容完整"

# ===== 市場 =====
def market(game):
    prev = history.get(game["match"])

    if not prev:
        history[game["match"]] = game["spread"]
        return 0, None

    diff = game["spread"] - prev
    history[game["match"]] = game["spread"]

    if abs(diff) >= 2:
        return 2, "🔥異常變盤"
    elif abs(diff) >= 1:
        return 1, "變盤"
    return 0, None

# ===== 模型 =====
def model(game):
    score = 0
    notes = []

    if game["total"] >= 226:
        score += 2
        notes.append("高節奏→大分")

    elif game["total"] <= 210:
        score -= 2
        notes.append("低節奏→小分")

    if game["spread"] <= -8:
        score -= 1
        notes.append("深盤風險")

    inj_score, inj_note = get_injury(game["match"])
    score += inj_score
    notes.append(inj_note)

    m_score, m_note = market(game)
    score += m_score
    if m_note:
        notes.append(m_note)

    if score >= 3:
        return "🔥主推", score, notes
    elif score >= 1:
        return "👉次推", score, notes
    elif score <= -2:
        return "❌避開", score, notes
    else:
        return "⚠️觀望", score, notes

# ===== 分析 =====
def run_analysis():
    global yesterday_picks

    games = fetch_odds()

    if not games:
        send("⚠️ 無明日賽事")
        return

    msg = "📊 NBA職業分析（明日）\n\n"
    picks = []

    for g in games:
        level, score, notes = model(g)

        msg += f"{g['match']}\n"
        msg += f"讓分:{g['spread']} | 大小:{g['total']}\n"
        msg += f"信心:{score}\n"
        msg += f"原因:{' | '.join(notes)}\n"
        msg += f"{level}\n\n"

        if level in ["🔥主推","👉次推"]:
            picks.append({"match": g["match"], "pick": level})

    yesterday_picks = picks
    send(msg)

# ===== 復盤 =====
def review():
    data = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard").json()

    msg = "📊 昨日復盤\n\n"

    for e in data["events"]:
        t = e["competitions"][0]["competitors"]

        home = normalize(t[0]["team"]["displayName"])
        away = normalize(t[1]["team"]["displayName"])

        score = f"{t[1]['score']}-{t[0]['score']}"

        msg += f"{away} vs {home}\n"
        msg += f"比分:{score}\n\n"

    send(msg)

# ===== 排程 =====
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
    send("🚀 最終職業AI版本啟動")
    run_analysis()
    scheduler()
