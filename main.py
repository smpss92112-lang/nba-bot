import requests, time, random, json, os
from datetime import datetime

BOT_TOKEN = "你的TOKEN"
CHAT_ID = "你的CHAT_ID"
API_KEY = "你的API_KEY"

HEADERS = {"User-Agent":"Mozilla/5.0"}

# ===== 檔案 =====
DATA_FILE = "records.json"

def load():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"bets":[], "profit":0}

def save(d):
    json.dump(d, open(DATA_FILE,"w"))

DB = load()

# ===== 中文 =====
隊伍 = {...}  # 保持完整30隊

def 中文(x): return 隊伍.get(x,x)

# ===== 發送 =====
def 發送(msg):
    for i in range(0,len(msg),3500):
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id":CHAT_ID,"text":msg[i:i+3500]}
            )
        except: pass

# ===== GET =====
def GET(url,params=None):
    for _ in range(2):
        try:
            r=requests.get(url,params=params,headers=HEADERS,timeout=10)
            if r.status_code==200:
                return r.json()
        except: time.sleep(1)
    return None

# ===== 盤口 =====
歷史盤={}
初盤={}
軌跡={}

def 判讀盤口(m):
    if m not in 軌跡 or len(軌跡[m])<2: return ""
    c=[x[1] for x in 軌跡[m]]
    d=c[-1]-c[0]
    if d>=1: return "🔥主力進場（大分）"
    if d<=-1: return "🔻壓低（小分）"
    if len(c)>=3 and c[1]>c[0] and c[-1]<c[1]:
        return "⚠ 誘盤"
    return "⚖ 正常"

def 抓盤():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
             {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"})
    if not isinstance(data,list): return []

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

            if len(totals)<2: continue

            t=sum(totals)/len(totals)
            s=sum(spreads)/len(spreads) if spreads else 0

            if m not in 初盤:
                初盤[m]=t
                軌跡[m]=[("初盤",t)]
                發送(f"🟡初盤\n{m}\n{round(t,1)}")

            if m in 歷史盤:
                diff=round(t-歷史盤[m],1)
                if abs(diff)>=0.5:
                    now=datetime.now().strftime("%H:%M")
                    軌跡[m].append((now,t))
                    log="\n".join([f"{x[0]}→{round(x[1],1)}" for x in 軌跡[m]])
                    發送(f"📊變盤\n{m}\n{log}\n{判讀盤口(m)}")

            歷史盤[m]=t
            res.append({"m":m,"t":t,"s":s,"teams":teams})
        except: continue
    return res

# ===== 模型 =====
def μ(game):
    t=game["t"]
    m=game["m"]
    inj=0
    變盤=len(軌跡.get(m,[]))
    初差=t-初盤.get(m,t)
    return max(150,min(300,t+初差*0.3+min(變盤,5)*0.15-inj*2+random.uniform(-1,1)))

# ===== 模擬 =====
def 模擬(game):
    t=game["t"];s=game["s"]
    mu=μ(game)

    o=c=oh=ch=0
    for _ in range(2000):
        score=max(100,min(350,random.gauss(mu,10)))
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
def 記錄(market,u,win):
    DB["bets"].append({
        "time":str(datetime.now()),
        "u":u,
        "win":win
    })
    DB["profit"] += u if win else -u
    save(DB)

def 報表():
    today=week=month=0
    now=datetime.now()

    for b in DB["bets"]:
        t=datetime.fromisoformat(b["time"])
        val=b["u"] if b["win"] else -b["u"]

        if t.date()==now.date(): today+=val
        if (now-t).days<7: week+=val
        if t.month==now.month: month+=val

    發送(f"📊報表\n今日:{today}U\n本週:{week}U\n本月:{month}U")

# ===== 分析 =====
def 分析():
    games=抓盤()
    msg="📊【最終完整版】\n\n"

    for g in games[:5]:
        over,cover,oh,ch=模擬(g)

        msg+=f"{g['m']}\n盤:{round(g['t'],1)}\n"
        msg+="【模擬整合】\n"
        msg+=f"上半讓分:{int(ch*100)}%\n"
        msg+=f"上半大小:{int(oh*100)}%\n"
        msg+=f"全場讓分:{int(cover*100)}%\n"
        msg+=f"全場大小:{int(over*100)}%\n"

        u1=U(over); u2=U(cover)
        if u1>0: msg+=f"大小 {u1}U\n"
        if u2>0: msg+=f"讓分 {u2}U\n"

        msg+="---\n"

    發送(msg)
    報表()

# ===== 主程式 =====
發送("🚀最終完整版啟動")
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
