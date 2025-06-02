import os
import json
import requests
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from threading import Thread
from time import sleep
from contextlib import asynccontextmanager

from middlewares.flood_control import (
    check_flood,
    track_blocked_user,
    get_expired_unblocks,
    get_all_blocked_users,
    reset_user_state,
    user_strikes
)
from bot.subscribers import add_subscriber
from bot.utils import send_message, delete_message, format_news_text
from bot.scheduler import schedule_news_tasks

load_dotenv()

# Для інтеграційних тестів (test_app_integration.py)
SUBSCRIBERS_FILE = "subscribers.json"
BLOCKED_FILE = "blocked.json"
UNBLOCKED_FILE = "unblocked.json"
save_subscriber = add_subscriber


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_API_URL = os.getenv("NEWS_API_URL")
last_warnings = {}


def consent_buttons():
    return {
        "inline_keyboard": [
            [{"text": "✅ Так", "callback_data": "accept"},
             {"text": "❌ Ні", "callback_data": "decline"}]
        ]
    }


def send_welcome_photo(chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    with open("./danish_news_bot_image.png", "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": chat_id, "disable_notification": True}
        response = requests.post(url, data=data, files=files)
        return response.json().get("result", {}).get("message_id")


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

        text = format_news_text(news)
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
            send_message(chat_id, text)

    except Exception:
        send_message(chat_id, "⚠️ Не вдалося завантажити новину.")


def process_unblocked_once():
    expired = get_expired_unblocks()
    for user_id, chat_id in expired:
        if last_warnings.get(user_id):
            for mid in last_warnings[user_id]:
                delete_message(chat_id, mid)
            del last_warnings[user_id]

        done_msg_id = send_message(chat_id, "✅ Блок завершено.")
        time.sleep(1)
        delete_message(chat_id, done_msg_id)

        strike = user_strikes.get(user_id, 0)

        if strike == 1:
            info_text = (
                "🔐 Для користування ботом потрібно підтвердити обробку персональних даних.\n"
                "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)\n\n"
                "❗ Якщо ви натиснете ще раз \"Ні\", вас буде заблоковано на 3 хвилини."
            )
        elif strike == 2:
            info_text = (
                "🔐 Для користування ботом потрібно підтвердити обробку персональних даних.\n"
                "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)\n\n"
                "❗ Якщо ви натиснете ще раз \"Ні\", вас буде заблоковано назавжди."
            )
        else:
            info_text = (
                "🔐 Для користування ботом потрібно підтвердити обробку персональних даних.\n"
                "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)"
            )

        msg_id = send_message(chat_id, info_text,
                              reply_markup=consent_buttons())
        last_warnings[user_id] = [msg_id]


def notify_unblocked_users():
    while True:
        process_unblocked_once()
        sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Thread(target=notify_unblocked_users, daemon=True).start()
    schedule_news_tasks()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/subscribers")
def get_subscribers():
    from bot.subscribers import load_subscribers
    return load_subscribers(SUBSCRIBERS_FILE)


@app.get("/blocked")
def get_blocked_users():
    from middlewares.flood_control import load_blocked_users
    return load_blocked_users(BLOCKED_FILE)


@app.post("/process-unblocked")
def trigger_unblock():
    process_unblocked_once()
    return {"status": "done"}


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    user_id = (data.get("message", {}) or data.get(
        "callback_query", {})).get("from", {}).get("id")
    chat_id = (data.get("message", {}) or data.get(
        "callback_query", {}).get("message", {})).get("chat", {}).get("id")

    # TEXT MESSAGE
    if "message" in data:
        text = data["message"].get("text", "").strip().lower()
        if text != "/start":
            flood_triggered, flood_message, show_buttons = check_flood(
                user_id, chat_id)
            if flood_triggered:
                delete_message(chat_id, data["message"]["message_id"])
                time.sleep(1)
                for mid in last_warnings.get(user_id, []):
                    delete_message(chat_id, mid)
                track_blocked_user(user_id, chat_id)
                msg_id = send_message(
                    chat_id,
                    flood_message,
                    reply_markup=consent_buttons() if show_buttons else None
                )
                last_warnings[user_id] = [msg_id]
                return {"status": "flood_control_applied"}

    # CALLBACK
    if "callback_query" in data:
        callback = data["callback_query"]
        message_id = callback["message"]["message_id"]
        user_choice = callback["data"]

        delete_message(chat_id, message_id)
        for mid in last_warnings.get(user_id, []):
            delete_message(chat_id, mid)
        last_warnings[user_id] = []

        if user_choice == "accept":
            reset_user_state(user_id)
            add_subscriber(chat_id)
            confirm_id = send_message(
                chat_id, "✅ Дякуємо! Ви дали згоду на обробку персональних даних.")
            send_first_news(chat_id)
            delete_message(chat_id, confirm_id)
            return {"status": "callback_handled"}

        # decline case → check flood
        flood_triggered, flood_message, show_buttons = check_flood(
            user_id, chat_id)
        if flood_triggered:
            track_blocked_user(user_id, chat_id)
            msg_id = send_message(
                chat_id,
                flood_message,
                reply_markup=consent_buttons() if show_buttons else None
            )
            last_warnings[user_id] = [msg_id]
            return {"status": "flood_control_applied"}

        msg_id = send_message(
            chat_id,
            "❌ Без згоди на обробку персональних даних бот не може працювати.\n\n"
            "🔐 [Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)",
            reply_markup=consent_buttons()
        )
        last_warnings[user_id] = [msg_id]
        return {"status": "callback_handled"}

    # START
    if data.get("message", {}).get("text", "").strip().lower() == "/start":
        photo_id = send_welcome_photo(chat_id)
        welcome_text = (
            "🇩🇰 *Вітаємо на нашому новинному каналі!*\n\n"
            "Тут ви знайдете найсвіжіші новини про події в Данії. Ми тримаємо вас у курсі всіх важливих змін та новинок у країні.\n\n"
            "🔐 *Чи даєте ви згоду на обробку персональних даних?*\n"
            "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)"
        )
        msg_id = send_message(chat_id, welcome_text,
                              reply_markup=consent_buttons())
        last_warnings[user_id] = [photo_id, msg_id]
        return {"status": "consent_requested"}

    # fallback
    msg = data.get("message")
    if msg and "message_id" in msg:
        delete_message(chat_id, msg["message_id"])
        time.sleep(1)

    for mid in last_warnings.get(user_id, []):
        delete_message(chat_id, mid)

    msg_id = send_message(
        chat_id,
        "⚠️ Спершу потрібно дати згоду на обробку персональних даних.\n\n"
        "[Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)",
        reply_markup=consent_buttons()
    )
    last_warnings[user_id] = [msg_id]
    return {"status": "consent_forced"}
