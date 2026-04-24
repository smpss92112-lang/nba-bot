import requests, time, json, os
from datetime import datetime, timedelta, timezone

BOT_TOKEN = "8684077613:AAGURQBszMtiOS4RdE3uDW9g504SIpZb8fs"
CHAT_ID = "957739057"
API_KEY = "3de238c08f870f50cf7e0afa980c6c8b"

HEADERS={"User-Agent":"Mozilla/5.0"}
DB_FILE="track.json"

# 台灣時區
TW = timezone(timedelta(hours=8))

print("🔥盤口監控（台灣時間版）啟動")

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
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg[:4000]},
            timeout=10
        )
    except:
        pass

# ===== API =====
def GET(url, p=None):
    try:
        r=requests.get(url, params=p, headers=HEADERS, timeout=10)
        if r.status_code==200:
            return r.json()
    except:
        pass
    return None

# ===== DB =====
def load():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE))
        except:
            return {}
    return {}

def save():
    json.dump(DB, open(DB_FILE,"w"))

DB=load()

# ===== 核心監控 =====
def monitor():
    data=GET(
        "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
        {"apiKey":API_KEY,"regions":"us","markets":"totals,spreads"}
    )

    if not isinstance(data,list):
        print("API無資料")
        return

    # 台灣時間的「明天」
    tomorrow = (datetime.now(TW) + timedelta(days=1)).date()

    for g in data:
        try:
            # ===== 時區轉換（關鍵）=====
            utc_time = datetime.fromisoformat(
                g["commence_time"].replace("Z","")
            ).replace(tzinfo=timezone.utc)

            local_time = utc_time.astimezone(TW)

            # 只抓台灣明天
            if local_time.date() != tomorrow:
                continue

            match = f"{zh(g['away_team'])} vs {zh(g['home_team'])}"

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

            total = round(sum(totals)/len(totals),1)
            spread = round(sum(spreads)/len(spreads),1) if spreads else 0

            now_time = datetime.now(TW).strftime("%H:%M")

            # ===== 初盤 =====
            if match not in DB:
                DB[match]={
                    "初盤":{"total":total,"spread":spread},
                    "紀錄":[f"{now_time} 初盤 大小:{total} 讓分:{spread}"]
                }
                send(
                    f"🟡初盤\n{match}\n大小:{total}\n讓分:{spread}"
                )
                continue

            last = DB[match]["紀錄"][-1]

            # 沒變就略過
            if f"大小:{total}" in last and f"讓分:{spread}" in last:
                continue

            # ===== 記錄變動 =====
            record=f"{now_time} 大小:{total} 讓分:{spread}"
            DB[match]["紀錄"].append(record)

            # ===== 判斷是否重大變動（>=1）=====
            prev = DB[match]["紀錄"][-2]

            try:
                prev_total=float(prev.split("大小:")[1].split()[0])
                if abs(total-prev_total) >= 1:
                    log="\n".join(DB[match]["紀錄"])
                    send(f"🚨盤口變動\n{match}\n{log}")
            except:
                pass

        except Exception as e:
            print("錯誤:", e)

    save()

# ===== 啟動 =====
send("🚀盤口監控啟動（台灣時間）")

while True:
    monitor()
    time.sleep(60)
