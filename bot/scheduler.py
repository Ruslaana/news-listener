import os
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from bot.subscribers import load_subscribers
from bot.utils import send_message

load_dotenv()
API_URL = os.getenv("NEWS_API_URL")

scheduler = BackgroundScheduler()


def fetch_and_send_news(tag="day"):
    try:
        response = requests.get(f"{API_URL}/latest?tag={tag}")
        if response.status_code != 200:
            print("❌ API error:", response.status_code)
            return

        news_item = response.json()
        chat_ids = load_subscribers()

        if not news_item or "title" not in news_item:
            for chat_id in chat_ids:
                send_message(
                    chat_id, "ℹ️ На цей момент немає новин для показу.")
            return

        for chat_id in chat_ids:
            send_message(chat_id, f"🗞 {news_item['title']}")

    except Exception as e:
        print("🔥 Error fetching news:", e)


def schedule_news_tasks():
    scheduler.add_job(lambda: fetch_and_send_news("day"), "cron", hour=9)
    scheduler.add_job(lambda: fetch_and_send_news("day"), "cron", hour=10)
    scheduler.add_job(lambda: fetch_and_send_news("day"), "cron", hour=11)
    scheduler.add_job(lambda: fetch_and_send_news("day"), "cron", hour=12)
    scheduler.add_job(lambda: fetch_and_send_news("evening"), "cron", hour=20)
    scheduler.start()
