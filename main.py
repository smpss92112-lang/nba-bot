import requests
import time
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=data)
    print("發送結果:", response.text)

def main():
    print("🚀 系統啟動")

    # 測試訊息（這段是關鍵）
    send_telegram("🔥 BOT已成功啟動！")

    while True:
        print("執行中...")
        time.sleep(60)

if __name__ == "__main__":
    main()
