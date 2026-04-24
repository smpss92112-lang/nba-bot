send("測試")

import requests, time, random, json, os
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

HEADERS={"User-Agent":"Mozilla/5.0"}
DB_FILE="db.json"

# ===== 中文 =====
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
    return {"bets":[], "profit":0.0, "bias":0.0}
def save(): json.dump(DB, open(DB_FILE,"w"))
DB=load()

# ===== 工具 =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": str(msg)[:4000]
        }
        r = requests.post(url, data=payload, timeout=10)

        if r.status_code != 200:
            print("TG錯誤:", r.text)

    except Exception as e:
        print("發送失敗:", e)

# ===== 盤口資料 =====
hist={}       # 上次盤
init={}       # 初盤
track={}      # 軌跡
live_count={} # 走地次數

# ===== 判讀 / 比例 =====
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

# ===== 19因子 μ（加權可運作版）=====
def mu(g):
    m=g["m"]; t=g["t"]; s=g["s"]
    h=track.get(m,[])
    d=t-init.get(m,t)
    n=len(h)

    # 盤口(5)
    f1=t
    f2=d
    f3=n
    f4=sum(abs(h[i][1]-h[i-1][1]) for i in range(1,len(h))) if len(h)>1 else 0
    f5=(h[-1][1]-h[-2][1]) if len(h)>1 else 0

    # 市場(4)
    f6=1 if d>0 else -1 if d<0 else 0
    f7=1 if len(h)>=3 and h[-1][1]<h[-2][1] else 0
    f8=min(n,5)
    f9=1 if n>=3 else 0

    # 節奏(3)
    f10=t/220.0
    f11=abs(s)
    f12=(t+abs(s))/230.0

    # 不確定(3)
    f13=random.uniform(-2,2)
    f14=min(n,4)
    f15=random.uniform(0,1)

    # 學習(4)
    f16=DB["bias"]
    f17=DB["profit"]/10.0
    f18=len(DB["bets"])
    f19=random.uniform(-0.5,0.5)

    val = (
        f1
        + f2*0.45 + f3*0.18 + f4*0.05 + f5*0.12
        + f6*0.6 - f7*1.4 + f8*0.12 + f9*0.25
        + f10*2.2 - f11*0.35 + f12*1.1
        + f13 - f14*0.12 + f15*0.2
        + f16 + f17 + f18*0.01 + f19
    )
    return max(150, min(300, val))

# ===== 模擬（全/半 × 讓/大小）=====
def sim(g):
    t=g["t"]; s=g["s"]; mval=mu(g)
    o=c=oh=ch=0
    for _ in range(1500):
        score=random.gauss(mval,10)
        diff=random.gauss(s,8)
        r=random.uniform(0.47,0.53)
        if score>t: o+=1
        if diff>s: c+=1
        if score*r>t*r: oh+=1
        if diff*r>s*r: ch+=1
    return o/1500, c/1500, oh/1500, ch/1500

def U(p):
    if p>=0.7: return 2
    if p>=0.65: return 1.5
    if p>=0.6: return 1.2
    if p>=0.55: return 1
    return 0

# ===== 記錄 =====
def add_bet(match, market, line, side, u):
    DB["bets"].append({
        "match":match,
        "market":market,  # total_full / spread_full / total_half / spread_half
        "line":line,
        "side":side,      # over/under 或 home/away
        "u":u,
        "status":"pending",
        "created":str(datetime.now()),
        "settled":None
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
        except:
            continue
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
        m=g["m"]; t=g["t"]; s=g["s"]
        msg+=f"{m}\n盤:{round(t,1)}\n{read_market(m)} | {ratio(m)}\n"
        msg+=f"全讓:{int(c*100)}% 全大:{int(o*100)}%\n"
        msg+=f"半讓:{int(ch*100)}% 半大:{int(oh*100)}%\n"

        # 依機率選市場，並正確記錄 market / side
        for name,p in [("total_full",o),("spread_full",c),("total_half",oh),("spread_half",ch)]:
            u=U(p)
            if u<=0: continue

            if "total" in name:
                side = "over" if p>=0.5 else "under"
                line = t if "full" in name else t*0.5
            else:
                # 讓分方向：以 home(主) 為正負，這裡以 diff>line 視為主隊過盤
                side = "home" if p>=0.5 else "away"
                line = s if "full" in name else s*0.5

            add_bet(m, name, line, side, u)
            msg+=f"💰{name}:{side} {u}U\n"

        msg+="---\n"

    send(msg)

# ===== 結算（全/半 × 讓/大小，含方向）=====
def settle():
    data=GET("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
    if not data: return

    for g in data.get("events",[]):
        try:
            comp=g["competitions"][0]["competitors"]
            home=comp[0]["team"]["displayName"]
            away=comp[1]["team"]["displayName"]
            s1=int(comp[0]["score"]); s2=int(comp[1]["score"])

            # 若有半場（部分場次沒有）
            half_home = comp[0].get("linescores",[{}])[0].get("value", None)
            half_away = comp[1].get("linescores",[{}])[0].get("value", None)

            total_full = s1+s2
            diff_full  = s1-s2

            total_half = (half_home + half_away) if (half_home is not None and half_away is not None) else None
            diff_half  = (half_home - half_away) if (half_home is not None and half_away is not None) else None

            for b in DB["bets"]:
                if b["status"]!="pending": continue
                if home in b["match"] or away in b["match"]:
                    win=False

                    if b["market"]=="total_full":
                        if b["side"]=="over":  win = total_full > b["line"]
                        else:                  win = total_full < b["line"]

                    elif b["market"]=="spread_full":
                        # side: home/away
                        if b["side"]=="home": win = diff_full > b["line"]
                        else:                 win = diff_full < -b["line"]

                    elif b["market"]=="total_half" and total_half is not None:
                        if b["side"]=="over": win = total_half > b["line"]
                        else:                 win = total_half < b["line"]

                    elif b["market"]=="spread_half" and diff_half is not None:
                        if b["side"]=="home": win = diff_half > b["line"]
                        else:                 win = diff_half < -b["line"]

                    else:
                        continue

                    b["status"]="win" if win else "lose"
                    b["settled"]=str(datetime.now())

                    if win:
                        DB["profit"]+=b["u"]; DB["bias"]+=0.1
                    else:
                        DB["profit"]-=b["u"]; DB["bias"]-=0.1

        except:
            continue

    DB["bias"]=max(-10,min(10,DB["bias"]))
    save()

# ===== 報表（用結算時間）=====
def report():
    now=datetime.now()
    d=w=m=0.0
    for b in DB["bets"]:
        if b["status"]=="pending": continue
        t=datetime.fromisoformat(b["settled"])
        val=b["u"] if b["status"]=="win" else -b["u"]
        if t.date()==now.date(): d+=val
        if (now-t).days<7: w+=val
        if t.month==now.month: m+=val
    send(f"📊報表\n今日:{round(d,2)}U 本週:{round(w,2)}U 本月:{round(m,2)}U")

# ===== 走地（每場最多3次）=====
def live_signal(games):
    for g in games:
        m=g["m"]
        cnt=live_count.get(m,0)
        if cnt>=3: continue
        if len(track.get(m,[]))>=3:
            c=[x[1] for x in track[m]]
            if c[-1]<c[-2] and c[-2]>c[-3]:
                send(f"⚡走地\n{m}\n盤口反轉，考慮反向")
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
send("🚀最終版啟動")
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
