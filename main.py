import requests
import time
import json
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
ODDS_API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

STATS_FILE = "stats.json"

# ===== 載入 =====
def load_stats():
    try:
        with open(STATS_FILE,"r") as f:
            return json.load(f)
    except:
        return {
            "weekly":{"win":0,"lose":0,"unit":0},
            "monthly":{"win":0,"lose":0,"unit":0},
            "history":[]
        }

def save_stats():
    with open(STATS_FILE,"w") as f:
        json.dump(stats,f)

stats = load_stats()
picks = []

TEAM_MAP = {
    "Los Angeles Lakers":"湖人","Houston Rockets":"火箭",
    "Phoenix Suns":"太陽","Oklahoma City Thunder":"雷霆"
}

def normalize(n):
    return TEAM_MAP.get(n,n)

def send(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  data={"chat_id":CHAT_ID,"text":msg})

# ===== AI判斷市場狀態 =====
def ai_market_state():
    hist = stats["history"][-3:]

    if len(hist) < 3:
        return "normal"

    total_win = sum(1 for x in hist if x > 0)
    total_loss = sum(1 for x in hist if x < 0)

    if total_win >= 2:
        return "good"
    elif total_loss >= 2:
        return "bad"
    return "normal"

# ===== 抓盤 =====
def fetch():
    url="https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params={"apiKey":ODDS_API_KEY,"regions":"us","markets":"totals"}
    data=requests.get(url,params=params).json()

    tomorrow=(datetime.utcnow()+timedelta(days=1)).date()
    games=[]

    for g in data:
        d=datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).date()
        if d!=tomorrow:
            continue

        total=None
        for b in g["bookmakers"]:
            for m in b["markets"]:
                if m["key"]=="totals":
                    total=m["outcomes"][0]["point"]

        if total:
            games.append({
                "match":f"{normalize(g['away_team'])} vs {normalize(g['home_team'])}",
                "total":total
            })
    return games

# ===== AI評分 =====
def evaluate(g, mode):
    score = 0

    # ===== 動態條件 =====
    if mode == "bad":
        if g["total"]>=230 or g["total"]<=210:
            score += 2
        else:
            return None
    else:
        if g["total"]>=228 or g["total"]<=212:
            score += 2
        else:
            return None

    pick = "大分" if g["total"]>=228 else "小分"

    return {
        "match":g["match"],
        "pick":pick,
        "line":g["total"],
        "score":score
    }

# ===== AI選場 =====
def select(games, mode):
    res=[]

    for g in games:
        r=evaluate(g,mode)
        if r:
            res.append(r)

    res.sort(key=lambda x:x["score"],reverse=True)

    if mode=="good":
        return res[:3]
    elif mode=="normal":
        return res[:2]
    else:
        return res[:1]

# ===== 分析 =====
def analyze():
    global picks

    mode = ai_market_state()
    games = fetch()
    picks = select(games,mode)

    msg="📊 AI判斷推薦\n\n"
    msg+=f"市場狀態:{mode}\n\n"

    for p in picks:
        p["unit"]=1.5
        msg+=f"{p['match']}\n{p['pick']} ({p['line']}) 1.5U\n\n"

    send(msg)

# ===== 結算 =====
def settle():
    data=requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard").json()

    results={}
    for e in data["events"]:
        t=e["competitions"][0]["competitors"]
        home=normalize(t[0]["team"]["displayName"])
        away=normalize(t[1]["team"]["displayName"])
        total=int(t[0]["score"])+int(t[1]["score"])
        results[f"{away} vs {home}"]=total

    unit_sum=0

    for p in picks:
        if p["match"] not in results:
            continue

        score=results[p["match"]]
        win=(p["pick"]=="大分" and score>p["line"]) or (p["pick"]=="小分" and score<p["line"])

        unit_sum += 1.5 if win else -1.5

    stats["history"].append(unit_sum)
    stats["weekly"]["unit"] += unit_sum
    stats["monthly"]["unit"] += unit_sum

    save_stats()

    msg="📊 AI結算\n\n"
    msg+=f"今日:{unit_sum}U\n"
    msg+=f"近3日:{stats['history'][-3:]}\n"
    msg+=f"本週:{round(stats['weekly']['unit'],2)}U\n"
    msg+=f"本月:{round(stats['monthly']['unit'],2)}U\n"

    send(msg)

# ===== 排程 =====
def run():
    now=datetime.now().strftime("%H:%M")

    if now=="20:00":
        analyze()

    if now=="12:00":
        settle()

if __name__=="__main__":
    send("🚀 AI判斷系統啟動")

    while True:
        run()
        time.sleep(30)
