import os
import json
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from datetime import date

from bot.subscribers import load_subscribers
from bot.utils import send_message, format_news_text

import boto3

load_dotenv()

API_URL = os.getenv("NEWS_API_URL")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

scheduler = BackgroundScheduler()
SENT_IDS_KEY = "meta/sent_news_ids.json"


def load_sent_ids():
    try:
        obj = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=SENT_IDS_KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        today_str = date.today().isoformat()
        if today_str not in data:
            data[today_str] = []
        return data
    except s3.exceptions.NoSuchKey:
        return {date.today().isoformat(): []}
    except Exception as e:
        print(f"❌ Помилка при завантаженні sent_news_ids: {e}")
        return {date.today().isoformat(): []}


def save_sent_ids(data):
    try:
        s3.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=SENT_IDS_KEY,
            Body=json.dumps(data, ensure_ascii=False),
            ContentType="application/json"
        )
    except Exception as e:
        print(f"❌ Помилка при збереженні sent_news_ids: {e}")


def fetch_news(endpoint):
    try:
        response = requests.get(f"{API_URL}/{endpoint}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API error ({endpoint}):", response.status_code)
            return None
    except Exception as e:
        print(f"🔥 Error fetching news ({endpoint}):", e)
        return None


def is_news_already_sent(news_id, sent_data):
    today_str = date.today().isoformat()
    return news_id in sent_data.get(today_str, [])


def mark_news_as_sent(news_id, sent_data):
    today_str = date.today().isoformat()
    if today_str not in sent_data:
        sent_data[today_str] = []
    if news_id not in sent_data[today_str]:
        sent_data[today_str].append(news_id)


def fetch_and_send_news():
    sent_data = load_sent_ids()
    chat_ids = load_subscribers()
    if not chat_ids:
        print("ℹ️ Немає підписників для розсилки.")
        return

    # Спроба надіслати latest
    news = fetch_news("latest")
    if news and "document" in news:
        news_id = news["document"].get("id")
        if is_news_already_sent(news_id, sent_data):
            # Якщо вже надсилали — беремо random
            news = fetch_news("random")
            if not news or "document" not in news:
                print("⚠️ Архів порожній або помилка.")
                return
            news_id = news["document"].get("id")
    else:
        # latest не спрацював — одразу random
        news = fetch_news("random")
        if not news or "document" not in news:
            print("⚠️ Архів порожній або помилка.")
            return
        news_id = news["document"].get("id")

    if is_news_already_sent(news_id, sent_data):
        print("🔁 Новина вже надсилалася сьогодні.")
        return

    text = format_news_text(news)
    for chat_id in chat_ids:
        send_message(chat_id, text)

    mark_news_as_sent(news_id, sent_data)
    save_sent_ids(sent_data)
    print(f"📨 Надіслано новину: {news_id}")


def schedule_news_tasks():
    scheduler.add_job(fetch_and_send_news, "cron", hour=9)
    scheduler.add_job(fetch_and_send_news, "cron", hour=10)
    scheduler.add_job(fetch_and_send_news, "cron", hour=11)
    scheduler.add_job(fetch_and_send_news, "cron", hour=12)
    scheduler.add_job(fetch_and_send_news, "cron", hour=20)
    scheduler.start()


# def schedule_news_tasks():
#     scheduler.add_job(lambda: fetch_and_send_news(), "interval", minutes=5)
#     scheduler.start()
