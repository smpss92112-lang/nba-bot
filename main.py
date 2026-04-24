import requests, time, random, json, os
from datetime import datetime, timedelta

# ===== 基本設定 =====
BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

HEADERS={"User-Agent":"Mozilla/5.0"}
DB_FILE="db.json"

print("🔥版本確認：完整覆蓋版啟動")

# ===== Telegram =====
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
        print("發送錯誤:", e)

# ===== GET（修正你炸掉的核心）=====
def GET(url, p=None):
    try:
        r = requests.get(url, params=p, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print("GET錯誤:", r.text)
    except Exception as e:
        print("GET Exception:", e)
    return None

# ===== DB =====
def load():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE))
        except:
            return {"bets":[], "profit":0.0, "bias":0.0}
    return {"bets":[], "profit":0.0, "bias":0.0}

def save():
    json.dump(DB, open(DB_FILE,"w"))

DB=load()

# ===== 資料 =====
history={}
initial={}
track={}

# ===== 抓盤 =====
def monitor():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
             {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"})

    if not isinstance(data,list):
        print("⚠ API無資料")
        return []

    games=[]

    for g in data:
        try:
            m=f"{g['away_team']} vs {g['home_team']}"

            totals=[]
            spreads=[]

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

            # 初盤
            if m not in initial:
                initial[m]=t
                track[m]=[("初盤",t)]
                send(f"🟡初盤\n{m}\n大小:{round(t,1)}\n讓分:{round(s,1)}")

            # 變盤
            if m in history:
                diff=round(t-history[m],1)

                if abs(diff)>=0.5:
                    track[m].append((datetime.now().strftime("%H:%M"),t))

                if abs(diff)>=1:
                    log="\n".join([f"{x[0]}→{x[1]}" for x in track[m]])
                    send(f"🚨重大變盤\n{m}\n{log}")

            history[m]=t
            games.append((m,t,s))

        except Exception as e:
            print("monitor錯:", e)

    return games

# ===== 模型 =====
def model(t,m):
    diff=t-initial.get(m,t)
    return t + diff*0.3 + len(track.get(m,[]))*0.1 + DB["bias"]

# ===== 模擬 =====
def simulate(t):
    over=0
    for _ in range(800):
        if random.gauss(t,10)>t:
            over+=1
    return over/800

# ===== U =====
def U(p):
    if p>=0.7:return 2
    if p>=0.65:return 1.5
    if p>=0.55:return 1
    return 0

# ===== 記錄 =====
def add_bet(m,t,u):
    DB["bets"].append({
        "match":m,
        "line":t,
        "u":u,
        "status":"pending",
        "created":str(datetime.now()),
        "settled":None
    })
    save()

# ===== 分析 =====
def analysis():
    games=monitor()

    picks=[]
    for m,t,s in games:
        p=simulate(t)
        picks.append((p,m,t))

    picks=sorted(picks,reverse=True)[:3]

    msg="📊20:00分析\n\n"

    for p,m,t in picks:
        u=U(p)

        msg+=f"{m}\n盤:{round(t,1)}\n機率:{int(p*100)}%\n💰{u}U\n\n"

        if u>0:
            add_bet(m,t,u)

    send(msg)

# ===== 結算 =====
def settle():
    data=GET("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")

    if not data:
        return

    for g in data.get("events",[]):
        try:
            comp=g["competitions"][0]["competitors"]
            home=comp[0]["team"]["displayName"]
            away=comp[1]["team"]["displayName"]

            s1=int(comp[0]["score"])
            s2=int(comp[1]["score"])
            total=s1+s2

            for b in DB["bets"]:
                if b["status"]!="pending":
                    continue

                if home in b["match"] or away in b["match"]:
                    win = total > b["line"]

                    b["status"]="win" if win else "lose"
                    b["settled"]=str(datetime.now())

                    if win:
                        DB["profit"]+=b["u"]
                        DB["bias"]+=0.1
                    else:
                        DB["profit"]-=b["u"]
                        DB["bias"]-=0.1

        except Exception as e:
            print("結算錯:", e)

    save()

# ===== 報表 =====
def report():
    now=datetime.now()
    d=w=m=0

    for b in DB["bets"]:
        if b["status"]=="pending":
            continue

        t=datetime.fromisoformat(b["settled"])
        val=b["u"] if b["status"]=="win" else -b["u"]

        if t.date()==now.date(): d+=val
        if (now-t).days<7: w+=val
        if t.month==now.month: m+=val

    send(f"📊報表\n今日:{d}U\n本週:{w}U\n本月:{m}U")

# ===== 心跳 =====
last_report=None
def heartbeat():
    global last_report
    now=datetime.now()
    interval=2 if now.hour<22 else 4

    if last_report is None or (now-last_report)>=timedelta(hours=interval):
        send("📊系統運作中")
        last_report=now

# ===== 啟動 =====
send("🚀系統啟動成功")

last_analysis=None

while True:
    try:
        monitor()
        heartbeat()

        now=datetime.now()

        if now.strftime("%H:%M")=="20:00" and last_analysis!=now.date():
            analysis()
            last_analysis=now.date()

        if now.strftime("%H:%M")=="06:00":
            settle()
            report()

        time.sleep(120)

    except Exception as e:
        print("主錯誤:", e)
        time.sleep(10)
