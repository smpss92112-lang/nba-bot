import requests, time, random, json, os
from datetime import datetime, timedelta

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

HEADERS={"User-Agent":"Mozilla/5.0"}
DB_FILE="db.json"

print("🔥版本確認：GET修復+中文版本")

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

# ===== Telegram =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": str(msg)[:4000]}, timeout=10)
    except:
        pass

# ===== GET（統一）=====
def GET(url, p=None):
    try:
        r = requests.get(url, params=p, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("GET錯:", e)
    return None

# ===== DB =====
def load():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE))
        except:
            return {"bets":[], "profit":0, "bias":0}
    return {"bets":[], "profit":0, "bias":0}

def save():
    json.dump(DB, open(DB_FILE,"w"))

DB=load()

# ===== 資料 =====
history={}
initial={}
track={}

# ===== 監控 =====
def monitor():
    data=GET("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
             {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"})

    if not isinstance(data,list):
        return []

    games=[]

    for g in data:
        try:
            m=f"{zh(g['away_team'])} vs {zh(g['home_team'])}"

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

            if m not in initial:
                initial[m]=t
                track[m]=[("初盤",t)]
                send(f"🟡初盤\n{m}\n大小:{round(t,1)}\n讓分:{round(s,1)}")

            if m in history:
                diff=round(t-history[m],1)

                if abs(diff)>=0.5:
                    track[m].append((datetime.now().strftime("%H:%M"),t))

                if abs(diff)>=1:
                    log="\n".join([f"{x[0]}→{x[1]}" for x in track[m]])
                    send(f"🚨重大變盤\n{m}\n{log}")

            history[m]=t
            games.append((m,t))

        except Exception as e:
            print("monitor錯:", e)

    return games

# ===== 啟動 =====
send("🚀系統啟動成功")

while True:
    try:
        monitor()
        time.sleep(10)
    except Exception as e:
        print("主錯:", e)
        time.sleep(5)
