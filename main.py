import time
import json
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")


def get_latest_news():
    response = requests.get("NEWS_URL")
    latest_news = response.json()[0]
    return latest_news


def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})


def check_news():
    latest_news = get_latest_news()
    try:
        with open("last_news.json", "r") as f:
            last_saved = json.load(f)
    except FileNotFoundError:
        last_saved = {}

    if latest_news["id"] != last_saved.get("id"):
        send_to_telegram(latest_news["title"])
        with open("last_news.json", "w") as f:
            json.dump(latest_news, f)
    else:
        print("Немає нових новин")


scheduler = BlockingScheduler()
scheduler.add_job(check_news, 'interval', hours=1)
scheduler.start()
