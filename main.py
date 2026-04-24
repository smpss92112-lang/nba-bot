import requests,time,random,json,os
from datetime import datetime,timedelta

BOT_TOKEN="你的TOKEN"
CHAT_ID="你的CHAT_ID"
API_KEY="你的API_KEY"

HEADERS={"User-Agent":"Mozilla/5.0"}

# ===== 中文 =====
隊伍={
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
def 中文(x):return 隊伍.get(x,x)

# ===== DB =====
DB_FILE="db.json"
def load():
    if os.path.exists(DB_FILE):
        return json.load(open(DB_FILE))
    return {"bets":[],"profit":0,"bias":0}
def save(): json.dump(DB,open(DB_FILE,"w"))
DB=load()

# ===== 發送 =====
def 發送(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id":CHAT_ID,"text":msg})
    except: pass

# ===== API =====
def GET(url,p=None):
    for _ in range(2):
        try:
            r=requests.get(url,params=p,headers=HEADERS,timeout=10)
            if r.status_code==200:return r.json()
        except: time.sleep(1)
    return None

# ===== 盤口 =====
歷史盤={}
初盤={}
軌跡={}

def 判讀(m):
    if m not in 軌跡:return ""
    c=[x[1] for x in 軌跡[m]]
    if len(c)<2:return ""
    d=c[-1]-c[0]
    if d>=1:return "🔥主力拉高"
    if d<=-1:return "🔻壓低"
    return "⚖正常"

def 投注比例(m):
    if m not in 軌跡:return "50/50"
    c=[x[1] for x in 軌跡[m]]
    d=c[-1]-c[0]
    if d>1:return "大70%"
    if d<-1:return "小70%"
    return "50/50"

# ===== 抓盤 =====
def 抓盤():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
    {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"})
    if not isinstance(data,list):return []

    games=[]
    for g in data:
        try:
            m=f"{中文(g['away_team'])} vs {中文(g['home_team'])}"

            totals=[];spreads=[]
            for b in g.get("bookmakers",[]):
                for mk in b.get("markets",[]):
                    if mk["key"]=="totals": totals.append(mk["outcomes"][0]["point"])
                    if mk["key"]=="spreads": spreads.append(mk["outcomes"][0].get("point",0))

            if len(totals)<2:continue
            t=sum(totals)/len(totals)
            s=sum(spreads)/len(spreads) if spreads else 0

            if m not in 初盤:
                初盤[m]=t
                軌跡[m]=[("初盤",t)]
                發送(f"🟡初盤\n{m}:{round(t,1)}")

            if m in 歷史盤:
                diff=round(t-歷史盤[m],1)

                if abs(diff)>=0.5:
                    軌跡[m].append((datetime.now().strftime("%H:%M"),t))

                if abs(diff)>=1:
                    log="\n".join([f"{x[0]}→{round(x[1],1)}" for x in 軌跡[m]])
                    發送(f"🚨重大變盤\n{m}\n{log}\n{判讀(m)}")

            歷史盤[m]=t
            games.append({"m":m,"t":t,"s":s})

        except:continue

    return games

# ===== 模型 =====
def μ(g):
    t=g["t"];m=g["m"];s=g["s"]
    diff=t-初盤.get(m,t)
    return t + diff*0.4 + len(軌跡.get(m,[]))*0.1 + DB["bias"] - abs(s)*0.2

# ===== 模擬 =====
def 模擬(g):
    t=g["t"];s=g["s"];mu=μ(g)
    o=c=oh=ch=0
    for _ in range(1000):
        score=random.gauss(mu,10)
        diff=random.gauss(s,8)
        r=random.uniform(0.47,0.53)
        if score>t:o+=1
        if diff>s:c+=1
        if score*r>t*r:oh+=1
        if diff*r>s*r:ch+=1
    return o/1000,c/1000,oh/1000,ch/1000

def U(p):
    return 2 if p>=0.7 else 1.5 if p>=0.65 else 1 if p>=0.55 else 0

# ===== 記錄推薦 =====
def 記錄推薦(m,line,pick,u):
    DB["bets"].append({
        "match":m,
        "line":line,
        "pick":pick,
        "u":u,
        "status":"pending",
        "time":str(datetime.now())
    })
    save()

# ===== 結算 =====
def 結算():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/scores/",
    {"apiKey":API_KEY})

    if not data:return

    for game in data:
        home=中文(game["home_team"])
        away=中文(game["away_team"])
        total=game.get("scores",{}).get("home",0)+game.get("scores",{}).get("away",0)

        for b in DB["bets"]:
            if b["status"]!="pending":continue
            if home in b["match"] or away in b["match"]:
                win = total > b["line"] if b["pick"]=="over" else total < b["line"]
                b["status"]="win" if win else "lose"

                if win:
                    DB["profit"]+=b["u"]
                    DB["bias"]+=0.2
                else:
                    DB["profit"]-=b["u"]
                    DB["bias"]-=0.2

    save()

# ===== 報表 =====
def 報表():
    now=datetime.now()
    d=w=m=0
    for b in DB["bets"]:
        if b["status"]=="pending":continue
        t=datetime.fromisoformat(b["time"])
        val=b["u"] if b["status"]=="win" else -b["u"]
        if t.date()==now.date():d+=val
        if (now-t).days<7:w+=val
        if t.month==now.month:m+=val

    發送(f"📊報表 今日:{d}U 本週:{w}U 本月:{m}U")

# ===== 分析 =====
def 分析():
    games=抓盤()
    picks=[]

    for g in games:
        o,c,oh,ch=模擬(g)
        edge=max(o,c)
        picks.append((edge,g,o,c,oh,ch))

    picks=sorted(picks,reverse=True)[:3]

    msg="📊20:00分析\n\n"
    for edge,g,o,c,oh,ch in picks:
        m=g["m"];t=g["t"]
        msg+=f"{m}\n盤:{round(t,1)}\n"
        msg+=f"{判讀(m)} {投注比例(m)}\n"
        msg+=f"全:{int(o*100)}% 半:{int(oh*100)}%\n"

        u=U(edge)
        if u>0:
            msg+=f"💰{u}U\n"
            記錄推薦(m,t,"over",u)

        msg+="---\n"

    發送(msg)
    報表()

# ===== 定時回報 =====
last_report=None
def 定時回報():
    global last_report
    now=datetime.now()
    interval=2 if now.hour<22 else 4
    if last_report is None or (now-last_report)>=timedelta(hours=interval):
        發送("📊盤口監控中（無重大變動）")
        last_report=now

# ===== 主程式 =====
發送("🚀系統啟動")

last=None
while True:
    try:
        抓盤()
        定時回報()

        now=datetime.now()

        if now.strftime("%H:%M")=="20:00" and last!=now.date():
            分析()
            last=now.date()

        if now.strftime("%H:%M")=="06:00":
            結算()

        time.sleep(120)

    except Exception as e:
        發送(str(e))
        time.sleep(10)
