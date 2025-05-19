import os
import json
import requests
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from threading import Thread
from time import sleep
from datetime import datetime
from contextlib import asynccontextmanager

from middlewares.flood_control import (
    check_flood,
    track_blocked_user,
    get_expired_unblocks
)
from bot.subscribers import add_subscriber

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_API_URL = os.getenv("NEWS_API_URL")

last_warnings = {}


def format_telegram_text(news):
    doc = news.get("document", {})
    meta = doc.get("metadata", {})

    title = doc.get("title", "")
    content = doc.get("content", "")
    publication_time = meta.get(
        "publication_time") or datetime.now().strftime("%d.%m.%Y")
    author = meta.get("author") or meta.get("source", "berlingske.dk")
    source = meta.get("source", "")

    header = f"📰 *{title}*\n\n"
    footer = f"\n\n🕒 {publication_time}\n✍️ {author}\n🔗 [Читати новину]({source})"

    max_content_len = 1024 - len(header) - len(footer)

    short_content = content[:max_content_len].rstrip() + "..."

    return header + short_content + footer


def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_notification": True,
        "disable_web_page_preview": True
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    response = requests.post(url, data=data)
    return response.json().get("result", {}).get("message_id")


def send_welcome_photo(chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    with open("./danish_news_bot_image.png", "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": chat_id, "disable_notification": True}
        requests.post(url, data=data, files=files)


def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
    data = {"chat_id": chat_id, "message_id": message_id}
    requests.post(url, data=data)


def consent_buttons():
    return {
        "inline_keyboard": [
            [{"text": "✅ Так", "callback_data": "accept"},
             {"text": "❌ Ні", "callback_data": "decline"}]
        ]
    }


def send_first_news(chat_id):
    try:
        response = requests.get(f"{NEWS_API_URL}/latest")

        if response.status_code != 200:
            send_message(chat_id, "⚠️ Не вдалося отримати новину.")
            return

        news = response.json()
        if "document" not in news:
            send_message(chat_id, "ℹ️ Новини ще не опубліковані.")
            return

        text = format_telegram_text(news)
        image_url = news.get("document", {}).get(
            "metadata", {}).get("image_url")

        if image_url and image_url.startswith("http"):
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                json={
                    "chat_id": chat_id,
                    "photo": image_url,
                    "caption": text,
                    "parse_mode": "Markdown"
                }
            )
        else:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                }
            )

    except Exception:
        send_message(chat_id, "⚠️ Не вдалося завантажити новину.")


def notify_unblocked_users():
    while True:
        expired = get_expired_unblocks()
        if expired:
            for user_id, chat_id in expired:
                if last_warnings.get(user_id):
                    delete_message(chat_id, last_warnings[user_id])
                    del last_warnings[user_id]

                done_msg_id = send_message(chat_id, "✅ Блок завершено.")
                time.sleep(2)

                if done_msg_id:
                    delete_message(chat_id, done_msg_id)

                msg_id = send_message(
                    chat_id,
                    "🔐 Для користування ботом потрібно підтвердити обробку персональних даних.\n"
                    "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)",
                    reply_markup=consent_buttons()
                )
                last_warnings[user_id] = msg_id
        sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Thread(target=notify_unblocked_users, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/subscribers")
def get_subscribers():
    from bot.subscribers import load_subscribers
    return load_subscribers()


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    user_id = (data.get("message", {}).get("from", {}).get("id") or
               data.get("callback_query", {}).get("from", {}).get("id"))
    chat_id = (data.get("message", {}).get("chat", {}).get("id") or
               data.get("callback_query", {}).get("message", {}).get("chat", {}).get("id"))

    if "message" in data:
        text = data["message"].get("text", "").strip().lower()
        if text != "/start":
            flood_triggered, flood_message, show_buttons = check_flood(
                user_id, chat_id)
            if flood_triggered:
                delete_message(chat_id, data["message"]["message_id"])
                time.sleep(1)
                if last_warnings.get(user_id):
                    delete_message(chat_id, last_warnings[user_id])
                track_blocked_user(user_id, chat_id)
                msg_id = send_message(chat_id, flood_message,
                                      reply_markup=consent_buttons() if show_buttons else None)
                last_warnings[user_id] = msg_id
                return {"status": "flood_control_applied"}

    if "callback_query" in data:
        callback = data["callback_query"]
        message_id = callback["message"]["message_id"]
        user_choice = callback["data"]

        delete_message(chat_id, message_id)
        if last_warnings.get(user_id):
            delete_message(chat_id, last_warnings[user_id])
            del last_warnings[user_id]

        if user_choice == "accept":
            add_subscriber(chat_id)
            send_message(
                chat_id, "✅ Дякуємо! Ви дали згоду на обробку персональних даних.")
            send_first_news(chat_id)
        elif user_choice == "decline":
            msg_id = send_message(
                chat_id,
                "❌ Без згоди на обробку персональних даних бот не може працювати.\n\n"
                "🔐 [Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)",
                reply_markup=consent_buttons()
            )
            last_warnings[user_id] = msg_id
        return {"status": "callback_handled"}

    if data.get("message", {}).get("text", "").strip().lower() == "/start":
        send_welcome_photo(chat_id)
        welcome_text = (
            "🇩🇰 *Вітаємо на нашому новинному каналі!*\n\n"
            "Тут ви знайдете найсвіжіші новини про події в Данії. "
            "Ми тримаємо вас у курсі всіх важливих змін та новинок у країні.\n\n"
            "🔐 *Чи даєте ви згоду на обробку персональних даних?*\n"
            "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)"
        )
        msg_id = send_message(chat_id, welcome_text,
                              reply_markup=consent_buttons())
        last_warnings[user_id] = msg_id
        return {"status": "consent_requested"}

    if "message" in data:
        delete_message(chat_id, data["message"]["message_id"])
        time.sleep(1)

    if last_warnings.get(user_id):
        delete_message(chat_id, last_warnings[user_id])

    msg_id = send_message(
        chat_id,
        "⚠️ Спершу потрібно дати згоду на обробку персональних даних.\n\n"
        "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)",
        reply_markup=consent_buttons()
    )
    last_warnings[user_id] = msg_id
    return {"status": "consent_forced"}
