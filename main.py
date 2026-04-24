import requests
import time
import random
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

# ===== 中文隊名 =====
隊伍 = {
"Los Angeles Lakers":"湖人","Houston Rockets":"火箭","Golden State Warriors":"勇士",
"Phoenix Suns":"太陽","San Antonio Spurs":"馬刺","Denver Nuggets":"金塊",
"Boston Celtics":"塞爾提克","Miami Heat":"熱火","Milwaukee Bucks":"公鹿",
"Dallas Mavericks":"獨行俠","New York Knicks":"尼克","Philadelphia 76ers":"76人",
"Chicago Bulls":"公牛","Cleveland Cavaliers":"騎士","Indiana Pacers":"溜馬",
"Utah Jazz":"爵士","Memphis Grizzlies":"灰熊","Sacramento Kings":"國王",
"Toronto Raptors":"暴龍","Washington Wizards":"巫師","Orlando Magic":"魔術",
"Brooklyn Nets":"籃網","Detroit Pistons":"活塞","Atlanta Hawks":"老鷹",
"Charlotte Hornets":"黃蜂","Minnesota Timberwolves":"灰狼","Oklahoma City Thunder":"雷霆",
"Portland Trail Blazers":"拓荒者","New Orleans Pelicans":"鵜鶘"
}

def 中文(x):
    return 隊伍.get(x,x)

# ===== 發送 =====
def 發送(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  data={"chat_id":CHAT_ID,"text":msg})

# ===== 全局 =====
歷史盤={}
初盤={}
軌跡={}
走地次數={}
學習誤差=[]

# ===== 抓盤 =====
def 抓盤():
    data=requests.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
    params={"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"}).json()

    res=[]
    for g in data:
        m=f"{中文(g['away_team'])} vs {中文(g['home_team'])}"

        total=None
        spread=0

        for b in g["bookmakers"]:
            for mk in b["markets"]:
                if mk["key"]=="totals":
                    total=mk["outcomes"][0]["point"]
                if mk["key"]=="spreads":
                    spread=mk["outcomes"][0]["point"]

        if total:
            res.append({"m":m,"t":total,"s":spread})
    return res

# ===== 傷兵 =====
def 傷兵(team):
    try:
        d=requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries").json()
    except:
        return []
    r=[]
    for t in d.get("teams",[]):
        if team in t["team"]["displayName"]:
            for p in t.get("injuries",[]):
                r.append(p["athlete"]["displayName"])
    return r

# ===== 模型 =====
def μ(total,inj):
    return total + random.uniform(-5,5) - len(inj)*2

# ===== 模擬 =====
def 模擬(total,spread,inj):
    over=cover=over_h=cover_h=0
    mu=μ(total,inj)

    for _ in range(2000):
        score=random.gauss(mu,10)
        diff=random.gauss(spread,8)

        if score>total: over+=1
        if diff>spread: cover+=1
        if score*0.5>total*0.5: over_h+=1
        if diff*0.5>spread*0.5: cover_h+=1

    return over/2000,cover/2000,over_h/2000,cover_h/2000

# ===== 盤口判讀 =====
def 判讀(old,new):
    if new-old>1: return "🔥主力拉高"
    if old-new>1: return "🔻壓低"
    return "⚖ 正常"

# ===== U =====
def U(p):
    p=int(p*100)
    if p>=70:return "2U"
    if p>=65:return "1.5U"
    if p>=60:return "1.2U"
    if p>=55:return "1U"
    return None

# ===== 走地 =====
def 走地(match,score,spread):
    if match not in 走地次數:
        走地次數[match]=0

    if 走地次數[match]>=3:
        return None

    if abs(score)>15:
        走地次數[match]+=1
        return f"🚨走地機會\n{match}\n分差:{score}\n盤:{spread}\n👉可能過度反應"

    return None

# ===== 分析 =====
def 分析():
    games=抓盤()
    msg="📊【最終交易版】\n\n"

    for g in games:
        m=g["m"]; t=g["t"]; s=g["s"]

        teams=m.split(" vs ")
        inj=傷兵(teams[0])+傷兵(teams[1])

        over,cover,over_h,cover_h=模擬(t,s,inj)

        msg+=f"{m}\n"
        msg+=f"盤:{t}\n"

        msg+=f"【傷兵】{','.join(inj) or '無'}\n"

        msg+="【模擬整合】\n"
        msg+=f"上半讓分：{'主隊' if cover_h>0.5 else '客隊'}（{int(cover_h*100)}%）\n"
        msg+=f"上半大小分：{'大分' if over_h>0.5 else '小分'}（{int(over_h*100)}%）\n"
        msg+=f"全場讓分：{'主隊' if cover>0.5 else '客隊'}（{int(cover*100)}%）\n"
        msg+=f"全場大小分：{'大分' if over>0.5 else '小分'}（{int(over*100)}%）\n"

        msg+="🎯推薦\n"
        if U(over): msg+=f"全場大小 {U(over)}\n"
        if U(cover): msg+=f"讓分 {U(cover)}\n"
        if U(over_h): msg+=f"半場大小 {U(over_h)}\n"
        if U(cover_h): msg+=f"半場讓分 {U(cover_h)}\n"

        msg+="\n---\n"

    發送(msg)

# ===== 啟動 =====
發送("🚀最終交易版系統啟動")

while True:
    now=datetime.now().strftime("%H:%M")

    if now=="20:00":
        分析()

    time.sleep(60)
