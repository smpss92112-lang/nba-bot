import requests,time,random,json,os
from datetime import datetime

BOT_TOKEN="你的TOKEN"
CHAT_ID="你的CHAT_ID"
API_KEY="你的API_KEY"

HEADERS={"User-Agent":"Mozilla/5.0"}

DB_FILE="db.json"

# ===== 中文隊名 =====
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
def 中文(x): return 隊伍.get(x,x)

# ===== DB =====
def load():
    if os.path.exists(DB_FILE):
        return json.load(open(DB_FILE))
    return {"bets":[],"profit":0,"bias":0}

def save():
    json.dump(DB,open(DB_FILE,"w"))

DB=load()

# ===== 發送 =====
def 發送(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id":CHAT_ID,"text":msg})
    except: pass

# ===== GET =====
def GET(url,p=None):
    for _ in range(2):
        try:
            r=requests.get(url,params=p,headers=HEADERS,timeout=10)
            if r.status_code==200:return r.json()
        except: time.sleep(1)
    return None

歷史盤={}
初盤={}
軌跡={}
走地次數={}

# ===== 判讀 =====
def 判讀(m):
    if m not in 軌跡 or len(軌跡[m])<2:return ""
    c=[x[1] for x in 軌跡[m]]
    d=c[-1]-c[0]
    if d>=1:return "🔥主力資金（大分）"
    if d<=-1:return "🔻壓低（小分）"
    if len(c)>=3 and c[1]>c[0] and c[-1]<c[1]:
        return "⚠誘盤"
    return "⚖散戶盤"

# ===== 投注比例 =====
def 投注比例(m):
    if m not in 軌跡 or len(軌跡[m])<2:return "50/50"
    c=[x[1] for x in 軌跡[m]]
    d=c[-1]-c[0]
    if d>1:return "大70% / 小30%"
    if d<-1:return "小70% / 大30%"
    return "50/50"

# ===== 抓盤（即時監控）=====
def 抓盤():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
    {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"})

    if not isinstance(data,list):return []

    games=[]
    for g in data:
        try:
            away=中文(g['away_team'])
            home=中文(g['home_team'])
            m=f"{away} vs {home}"

            totals=[];spreads=[]
            for b in g.get("bookmakers",[]):
                for mk in b.get("markets",[]):
                    if mk["key"]=="totals":
                        totals.append(mk["outcomes"][0]["point"])
                    if mk["key"]=="spreads":
                        spreads.append(mk["outcomes"][0].get("point",0))

            if len(totals)<2:continue

            t=sum(totals)/len(totals)
            s=sum(spreads)/len(spreads) if spreads else 0

            # 初盤
            if m not in 初盤:
                初盤[m]=t
                軌跡[m]=[("初盤",t)]
                發送(f"🟡初盤\n{m}\n{round(t,1)}")

            # 變盤（即時）
            if m in 歷史盤:
                d=t-歷史盤[m]
                if abs(d)>=0.5:
                    now=datetime.now().strftime("%H:%M")
                    軌跡[m].append((now,t))
                    log="\n".join([f"{x[0]}→{round(x[1],1)}" for x in 軌跡[m]])
                    發送(f"📊變盤\n{m}\n{log}\n{判讀(m)}")

            歷史盤[m]=t

            games.append({"m":m,"t":t,"s":s})
        except: continue

    return games

# ===== 模型 =====
def μ(g):
    t=g["t"];m=g["m"]
    var=len(軌跡.get(m,[]))
    diff=t-初盤.get(m,t)
    return max(150,min(300,t+diff*0.3+var*0.1+DB["bias"]))

# ===== 模擬 =====
def 模擬(g):
    t=g["t"];s=g["s"]
    mu=μ(g)

    o=c=oh=ch=0
    for _ in range(2000):
        score=random.gauss(mu,10)
        diff=random.gauss(s,8)
        r=random.uniform(0.47,0.53)

        if score>t:o+=1
        if diff>s:c+=1
        if score*r>t*r:oh+=1
        if diff*r>s*r:ch+=1

    return o/2000,c/2000,oh/2000,ch/2000

# ===== U =====
def U(p):
    if p>=0.7:return 2
    if p>=0.65:return 1.5
    if p>=0.6:return 1.2
    if p>=0.55:return 1
    return 0

# ===== 報表 =====
def 報表():
    now=datetime.now()
    d=w=m=0

    for b in DB["bets"]:
        t=datetime.fromisoformat(b["t"])
        val=b["u"] if b["w"] else -b["u"]

        if t.date()==now.date():d+=val
        if (now-t).days<7:w+=val
        if t.month==now.month:m+=val

    發送(f"📊報表\n今日:{d}U\n本週:{w}U\n本月:{m}U")

# ===== 分析 =====
def 分析():
    games=抓盤()

    picks=[]
    for g in games:
        o,c,oh,ch=模擬(g)
        edge=max(o,c)
        picks.append((edge,g,o,c,oh,ch))

    picks=sorted(picks,reverse=True)[:3]

    msg="📊最終完整版\n\n"

    for edge,g,o,c,oh,ch in picks:
        m=g["m"];t=g["t"]
        mu=μ(g)
        u=U(edge)

        軌="\n".join([f"{x[0]}→{round(x[1],1)}" for x in 軌跡.get(m,[])])

        msg+=f"{m}\n盤:{round(t,1)}\n\n"
        msg+="📊盤口\n"+軌+"\n"+判讀(m)+"\n\n"
        msg+="📊投注比例\n"+投注比例(m)+"\n\n"
        msg+=f"μ:{round(mu,1)}\n\n"
        msg+=f"全讓:{int(c*100)}% 全大:{int(o*100)}%\n"
        msg+=f"半讓:{int(ch*100)}% 半大:{int(oh*100)}%\n\n"

        if u>0:
            msg+=f"💰{u}U\n"

        msg+="----------------\n"

    發送(msg)
    報表()

# ===== 主程式 =====
發送("🚀最終完整版啟動")

last=None

while True:
    try:
        抓盤()  # 👉即時監控

        now=datetime.now()
        if now.strftime("%H:%M").startswith("20:00"):
            if last!=now.date():
                分析()
                last=now.date()

        time.sleep(120)

    except Exception as e:
        發送(str(e))
        time.sleep(10)
