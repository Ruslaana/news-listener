import os
import json
import requests
import time
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from middlewares.flood_control import (
    check_flood,
    track_blocked_user,
    get_expired_unblocks
)
from bot.subscribers import add_subscriber

load_dotenv()
app = FastAPI()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
last_warnings = {}


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
            [
                {"text": "✅ Так", "callback_data": "accept"},
                {"text": "❌ Ні", "callback_data": "decline"}
            ]
        ]
    }


def fetch_latest_news():
    sitemap_url = "https://www.berlingske.dk/sitemap.xml/tag/1"
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        news_items = []

        for url in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            loc = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if loc is not None:
                news_items.append({"id": loc.text, "title": loc.text})
        return news_items
    except Exception:
        return []


def send_first_news(chat_id):
    all_news = fetch_latest_news()
    if not all_news:
        send_message(chat_id, "⚠️ Наразі не вдалося отримати новини.")
        return

    latest = all_news[0]
    send_message(chat_id, f"📰 {latest['title']}")


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
                msg_id = send_message(
                    chat_id,
                    flood_message,
                    reply_markup=consent_buttons() if show_buttons else None
                )
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
