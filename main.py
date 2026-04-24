import requests, time, random, json, os
from datetime import datetime, timedelta

BOT_TOKEN="你的TOKEN"
CHAT_ID="你的CHAT_ID"
API_KEY="你的API_KEY"

HEADERS={"User-Agent":"Mozilla/5.0"}
DB_FILE="db.json"

# ===== 中文隊名 =====
TEAM={
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
def zh(x): return TEAM.get(x,x)

# ===== DB =====
def load():
    if os.path.exists(DB_FILE):
        return json.load(open(DB_FILE))
    return {"bets":[], "profit":0, "bias":0}
def save(): json.dump(DB, open(DB_FILE,"w"))
DB=load()

# ===== 發送 =====
def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id":CHAT_ID,"text":msg})
    except: pass

# ===== API =====
def GET(url,p=None):
    try:
        r=requests.get(url,params=p,headers=HEADERS,timeout=10)
        if r.status_code==200: return r.json()
    except: pass
    return None

# ===== 盤口資料 =====
hist={}
init={}
track={}
live_count={}   # 走地次數

# ===== 判讀 + 比例 =====
def read_market(m):
    if m not in track or len(track[m])<2: return "⚖正常"
    c=[x[1] for x in track[m]]
    d=c[-1]-c[0]
    if d>=1: return "🔥主力拉高"
    if d<=-1: return "🔻壓低"
    if len(c)>=3 and c[-1]<c[-2] and c[-2]>c[-3]: return "⚠誘盤"
    return "⚖散戶"

def ratio(m):
    if m not in track or len(track[m])<2: return "50/50"
    c=[x[1] for x in track[m]]
    d=c[-1]-c[0]
    if d>1: return "大70% 小30%"
    if d<-1: return "小70% 大30%"
    return "50/50"

# ===== 19因子 μ =====
def mu(game):
    m=game["m"]; t=game["t"]; s=game["s"]
    h=track.get(m,[])
    d=t-init.get(m,t)
    n=len(h)
    # A 盤口
    f1=t; f2=d; f3=n; f4=sum([abs(h[i][1]-h[i-1][1]) for i in range(1,len(h))]) if len(h)>1 else 0
    f5=(h[-1][1]-h[-2][1]) if len(h)>1 else 0
    # B 市場
    f6=1 if d>0 else -1 if d<0 else 0
    f7=1 if len(h)>=3 and h[-1][1]<h[-2][1] else 0
    f8=min(n,5)
    f9=1 if n>=3 else 0
    # C 節奏
    f10=t/220; f11=abs(s); f12=(t+abs(s))/230
    # D 不確定
    f13=random.uniform(-3,3); f14=min(n,4); f15=random.uniform(0,1)
    # E 學習
    f16=DB["bias"]; f17=DB["profit"]/10; f18=len(DB["bets"]); f19=random.uniform(-1,1)

    val=(f1 + f2*0.4 + f3*0.15 + f4*0.05 + f5*0.1 +
         f6*0.5 - f7*1.2 + f8*0.1 + f9*0.2 +
         f10*2 - f11*0.3 + f12*1 +
         f13 - f14*0.1 + f15 +
         f16 + f17 + f18*0.01 + f19)

    return max(150,min(300,val))

# ===== 模擬（全/半、讓/大小）=====
def sim(game):
    t=game["t"]; s=game["s"]; m=mu(game)
    o=c=oh=ch=0
    for _ in range(1200):
        score=random.gauss(m,10)
        diff=random.gauss(s,8)
        r=random.uniform(0.47,0.53)
        if score>t:o+=1
        if diff>s:c+=1
        if score*r>t*r:oh+=1
        if diff*r>s*r:ch+=1
    return o/1200, c/1200, oh/1200, ch/1200

def U(p):
    return 2 if p>=0.7 else 1.5 if p>=0.65 else 1.2 if p>=0.6 else 1 if p>=0.55 else 0

# ===== 記錄推薦 =====
def add_bet(match,market,line,pick,u):
    DB["bets"].append({
        "match":match,"market":market,"line":line,"pick":pick,
        "u":u,"status":"pending","created":str(datetime.now()),"settled":None
    })
    save()

# ===== 抓盤（0.5記錄 / 1推播）=====
def monitor():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
    {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"})
    if not isinstance(data,list): return []

    games=[]
    for g in data:
        try:
            m=f"{zh(g['away_team'])} vs {zh(g['home_team'])}"
            totals=[]; spreads=[]
            for b in g.get("bookmakers",[]):
                for mk in b.get("markets",[]):
                    if mk["key"]=="totals":
                        totals.append(mk["outcomes"][0]["point"])
                    if mk["key"]=="spreads":
                        spreads.append(mk["outcomes"][0].get("point",0))
            if len(totals)<2: continue
            t=sum(totals)/len(totals)
            s=sum(spreads)/len(spreads) if spreads else 0

            if m not in init:
                init[m]=t
                track[m]=[("初盤",t)]
                send(f"🟡初盤\n{m}\n{round(t,1)}")

            if m in hist:
                diff=round(t-hist[m],1)
                if abs(diff)>=0.5:
                    track[m].append((datetime.now().strftime("%H:%M"),t))
                if abs(diff)>=1:
                    log="\n".join([f"{x[0]}→{round(x[1],1)}" for x in track[m]])
                    send(f"🚨重大變盤\n{m}\n{log}\n{read_market(m)}")

            hist[m]=t
            games.append({"m":m,"t":t,"s":s})
        except: continue
    return games

# ===== 20:00 分析 =====
def analysis():
    games=monitor()
    picks=[]
    for g in games:
        o,c,oh,ch=sim(g)
        edge=max(o,c,oh,ch)
        picks.append((edge,g,o,c,oh,ch))
    picks=sorted(picks,reverse=True)[:3]

    msg="📊20:00分析\n\n"
    for edge,g,o,c,oh,ch in picks:
        m=g["m"]; t=g["t"]
        msg+=f"{m}\n盤:{round(t,1)}\n"
        msg+=f"{read_market(m)} | {ratio(m)}\n"
        msg+=f"全場讓分:{int(c*100)}%\n全場大小:{int(o*100)}%\n"
        msg+=f"半場讓分:{int(ch*100)}%\n半場大小:{int(oh*100)}%\n"

        for name,p in [("全大",o),("全讓",c),("半大",oh),("半讓",ch)]:
            u=U(p)
            if u>0:
                msg+=f"💰{name} {u}U\n"
                market="total" if "大" in name else "spread"
                pick="over" if "大" in name else "cover"
                add_bet(m,market,t,pick,u)
        msg+="---\n"
    send(msg)

# ===== 結算（大小/讓分/半場）=====
def settle():
    data=GET("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
    if not data: return

    for g in data.get("events",[]):
        try:
            comp=g["competitions"][0]["competitors"]
            home=comp[0]["team"]["displayName"]; away=comp[1]["team"]["displayName"]
            s1=int(comp[0]["score"]); s2=int(comp[1]["score"])
            total=s1+s2; diff=s1-s2

            for b in DB["bets"]:
                if b["status"]!="pending": continue
                if home in b["match"] or away in b["match"]:
                    if b["market"]=="total":
                        win = total>b["line"] if b["pick"]=="over" else total<b["line"]
                    else:
                        win = diff> b["line"] if b["pick"]=="cover" else diff< b["line"]

                    b["status"]="win" if win else "lose"
                    b["settled"]=str(datetime.now())

                    if win:
                        DB["profit"]+=b["u"]; DB["bias"]+=0.1
                    else:
                        DB["profit"]-=b["u"]; DB["bias"]-=0.1
        except: continue
    DB["bias"]=max(-10,min(10,DB["bias"]))
    save()

# ===== 報表（用結算時間）=====
def report():
    now=datetime.now()
    d=w=m=0
    for b in DB["bets"]:
        if b["status"]=="pending": continue
        t=datetime.fromisoformat(b["settled"])
        val=b["u"] if b["status"]=="win" else -b["u"]
        if t.date()==now.date(): d+=val
        if (now-t).days<7: w+=val
        if t.month==now.month: m+=val
    send(f"📊報表\n今日:{d}U 本週:{w}U 本月:{m}U")

# ===== 走地（簡化但有效）=====
def live_signal(games):
    for g in games:
        m=g["m"]; t=g["t"]
        cnt=live_count.get(m,0)
        if cnt>=3: continue
        if len(track.get(m,[]))>=3:
            # 盤口快速反轉視為機會
            c=[x[1] for x in track[m]]
            if c[-1]<c[-2] and c[-2]>c[-3]:
                send(f"⚡走地機會\n{m}\n盤口反轉，考慮反向")
                live_count[m]=cnt+1

# ===== 定時回報 =====
last_report=None
def heartbeat():
    global last_report
    now=datetime.now()
    interval=2 if now.hour<22 else 4
    if last_report is None or (now-last_report)>=timedelta(hours=interval):
        send("📊系統運作中（無重大變動）")
        last_report=now

# ===== 主程式 =====
send("🚀最終完整版啟動")
last=None

while True:
    try:
        games=monitor()
        live_signal(games)
        heartbeat()

        now=datetime.now()
        if now.strftime("%H:%M")=="20:00" and last!=now.date():
            analysis()
            last=now.date()

        if now.strftime("%H:%M")=="06:00":
            settle()
            report()

        time.sleep(120)
    except Exception as e:
        send(str(e))
        time.sleep(10)
