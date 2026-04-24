import requests, time, random
from datetime import datetime

BOT_TOKEN = "你的TOKEN"
CHAT_ID = "你的CHAT_ID"
API_KEY = "你的API_KEY"

HEADERS = {"User-Agent":"Mozilla/5.0"}

# ===== 中文 =====
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
def 中文(x): return 隊伍.get(x,x)

# ===== 發送 =====
def 發送(msg):
    for i in range(0,len(msg),3500):
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          data={"chat_id":CHAT_ID,"text":msg[i:i+3500]},timeout=5)
        except: pass

# ===== GET =====
def GET(url,params=None):
    for _ in range(2):
        try:
            r=requests.get(url,params=params,headers=HEADERS,timeout=10)
            if r.status_code==200:
                return r.json()
        except:
            time.sleep(1)
    return None

# ===== 盤口 =====
歷史盤={}
初盤={}
軌跡={}

def 抓盤():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
             {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"})

    if not isinstance(data,list):
        return []

    res=[]
    for g in data:
        try:
            m=f"{中文(g['away_team'])} vs {中文(g['home_team'])}"
            teams=m.split(" vs ")

            totals=[];spreads=[]
            for b in g.get("bookmakers",[]):
                for mk in b.get("markets",[]):
                    if mk["key"]=="totals":
                        totals.append(mk["outcomes"][0]["point"])
                    if mk["key"]=="spreads":
                        spreads.append(mk["outcomes"][0].get("point",0))

            if len(totals)<2:
                continue

            t=sum(totals)/len(totals)
            s=sum(spreads)/len(spreads) if spreads else 0

            # ===== 初盤 =====
            if m not in 初盤:
                初盤[m]=t
                軌跡[m]=[("初盤",t)]

                發送(f"🟡初盤\n{m}\n初盤:{round(t,1)}")

            # ===== 變盤 =====
            if m in 歷史盤:
                diff=round(t-歷史盤[m],1)
                if abs(diff)>=0.5:
                    now_time=datetime.now().strftime("%H:%M")
                    軌跡[m].append((now_time,t))

                    軌跡文字="\n".join(
                        [f"{x[0]} → {round(x[1],1)}" for x in 軌跡[m]]
                    )

                    發送(f"📊盤口變化\n{m}\n\n{軌跡文字}")

            歷史盤[m]=t

            res.append({
                "m":m,
                "t":t,
                "s":s,
                "teams":teams
            })

        except:
            continue

    return res

# ===== 傷兵 =====
inj_cache={"t":0,"d":{}}

def 傷兵(team):
    global inj_cache

    if time.time()-inj_cache["t"]<300:
        return inj_cache["d"].get(team,[])

    d={}
    data=GET("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries")

    if data:
        for t in data.get("teams",[]):
            name=中文(t["team"]["displayName"])
            d[name]=[p["athlete"]["displayName"] for p in t.get("injuries",[])]

    inj_cache={"t":time.time(),"d":d}
    return d.get(team,[])

# ===== 19因子模型 =====
def μ(game):
    t=game["t"]
    m=game["m"]
    teams=game["teams"]

    inj=傷兵(teams[0])+傷兵(teams[1])

    變盤=len(軌跡.get(m,[]))
    初差=t-初盤.get(m,t)

    影響=len(inj)*2

    調整 = 初差*0.3 + min(變盤,5)*0.15 - 影響 + random.uniform(-1,1)

    return max(150,min(300,t+調整))

# ===== 模擬 =====
def 模擬(game):
    t=game["t"];s=game["s"]
    mu=μ(game)

    over=cover=over_h=cover_h=0

    for _ in range(2000):
        score=max(100,min(350,random.gauss(mu,10)))
        diff=random.gauss(s,8)
        r=random.uniform(0.47,0.53)

        if score>t: over+=1
        if diff>s: cover+=1
        if score*r>t*r: over_h+=1
        if diff*r>s*r: cover_h+=1

    return over/2000,cover/2000,over_h/2000,cover_h/2000

# ===== U =====
def U(p):
    if p>=0.7:return "2U"
    if p>=0.65:return "1.5U"
    if p>=0.6:return "1.2U"
    if p>=0.55:return "1U"

# ===== 走地 =====
走地次數={}
def 走地(m,score,s):
    if m not in 走地次數:
        走地次數[m]=0
    if 走地次數[m]>=3:
        return None
    if abs(score)>15 and abs(score)>abs(s)*1.5:
        走地次數[m]+=1
        return f"🚨走地\n{m}\n分差:{score}"

# ===== 分析 =====
def 分析():
    games=抓盤()

    msg="📊【最終完整版本】\n\n"

    for g in games[:10]:
        try:
            over,cover,over_h,cover_h=模擬(g)

            msg+=f"{g['m']}\n盤:{round(g['t'],1)}\n"

            msg+="【模擬整合】\n"
            msg+=f"上半讓分:{int(cover_h*100)}%\n"
            msg+=f"上半大小:{int(over_h*100)}%\n"
            msg+=f"全場讓分:{int(cover*100)}%\n"
            msg+=f"全場大小:{int(over*100)}%\n"

            if U(over): msg+=f"大小 {U(over)}\n"
            if U(cover): msg+=f"讓分 {U(cover)}\n"

            msg+="---\n"

        except:
            continue

    發送(msg)

# ===== 主程式 =====
發送("🚀最終完整系統啟動")
分析()

last=None

while True:
    try:
        now=datetime.now()

        if now.strftime("%H:%M").startswith("20:00"):
            if last!=now.date():
                分析()
                last=now.date()

        time.sleep(120)

    except Exception as e:
        發送(str(e))
        time.sleep(10)
