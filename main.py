import requests
import time
import json
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
ODDS_API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

STATS_FILE = "stats.json"

def load_stats():
    try:
        with open(STATS_FILE,"r") as f:
            return json.load(f)
    except:
        return {
            "weekly":{"unit":0},
            "monthly":{"unit":0},
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

# ===== AI市場狀態 =====
def ai_mode():
    hist = stats["history"][-3:]
    if len(hist)<3:
        return "normal"

    win = sum(1 for x in hist if x>0)
    lose = sum(1 for x in hist if x<0)

    if lose>=2:
        return "safe"
    if lose>=3:
        return "stop"
    if win>=2:
        return "good"

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

# ===== 評分 =====
def evaluate(g):
    score = 0

    if g["total"]>=228:
        score = 3
        pick = "大分"
    elif g["total"]<=212:
        score = 3
        pick = "小分"
    elif g["total"]>=226 or g["total"]<=214:
        score = 2
        pick = "大分" if g["total"]>=226 else "小分"
    else:
        return None

    return {
        "match":g["match"],
        "pick":pick,
        "line":g["total"],
        "score":score
    }

# ===== 選場 =====
def select(games):
    res=[]
    for g in games:
        r=evaluate(g)
        if r:
            res.append(r)

    res.sort(key=lambda x:x["score"],reverse=True)
    return res[:3]

# ===== 💰 資金管理 =====
def apply_bankroll(picks, mode):
    final=[]
    total_risk=0
    max_risk=3  # 每日上限 3U

    for p in picks:
        if mode=="stop":
            continue

        # 基礎單位
        if p["score"]>=3:
            unit=1.5
        else:
            unit=1

        # 風控縮放
        if mode=="safe":
            unit*=0.7

        # 控制總風險
        if total_risk + unit > max_risk:
            continue

        p["unit"]=round(unit,2)
        total_risk+=unit
        final.append(p)

    return final

# ===== 分析 =====
def analyze():
    global picks

    mode=ai_mode()
    games=fetch()
    raw=select(games)

    picks=apply_bankroll(raw,mode)

    msg="📊 AI資金管理推薦\n\n"
    msg+=f"模式:{mode}\n\n"

    for p in picks:
        msg+=f"{p['match']}\n"
        msg+=f"{p['pick']} ({p['line']}) {p['unit']}U\n\n"

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

        unit_sum += p["unit"] if win else -p["unit"]

    stats["history"].append(unit_sum)
    stats["weekly"]["unit"]+=unit_sum
    stats["monthly"]["unit"]+=unit_sum

    save_stats()

    msg="📊 結算\n\n"
    msg+=f"今日:{round(unit_sum,2)}U\n"
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
    send("🚀 資金管理系統啟動")

    while True:
        run()
        time.sleep(30)
