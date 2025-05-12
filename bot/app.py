import os
import json
import requests
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from middlewares.flood_control import check_flood

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
        "disable_notification": True
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    response = requests.post(url, data=data)
    result = response.json()
    print("Message sent:", result)
    return result.get("result", {}).get("message_id")


def send_welcome_photo(chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    photo_path = "./danish_news_bot_image.png"

    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": chat_id}
        response = requests.post(url, data=data, files=files)
        print("Welcome photo sent:", response.json())


def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
    data = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    response = requests.post(url, data=data)
    print("Deleted message:", response.json())
    return response.json()


def consent_buttons():
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Так", "callback_data": "accept"},
                {"text": "❌ Ні", "callback_data": "decline"}
            ]
        ]
    }


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("📥 Incoming update:", json.dumps(data, indent=2, ensure_ascii=False))

    if "message" in data:
        user_id = data["message"]["from"]["id"]
    elif "callback_query" in data:
        user_id = data["callback_query"]["from"]["id"]
    else:
        return {"status": "unhandled"}

    flood_triggered, flood_message = check_flood(user_id)
    chat_id = data.get("message", {}).get("chat", {}).get("id") or \
        data.get("callback_query", {}).get(
            "message", {}).get("chat", {}).get("id")

    if flood_triggered and chat_id:
        send_message(chat_id, flood_message)
        return {"status": "flood_controlled"}

    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        user_choice = callback["data"]

        delete_message(chat_id, message_id)

        old_warning_id = last_warnings.get(user_id)
        if old_warning_id:
            delete_message(chat_id, old_warning_id)
            del last_warnings[user_id]

        if user_choice == "accept":
            send_message(
                chat_id, "✅ Дякуємо! Ви дали згоду на обробку персональних даних.")
        elif user_choice == "decline":
            new_warning = send_message(
                chat_id,
                "❌ Без згоди на обробку персональних даних бот не може працювати.\n\n"
                "Будь ласка, підтвердіть згоду нижче.",
                reply_markup=consent_buttons()
            )
            last_warnings[user_id] = new_warning

        return {"status": "callback_handled"}

    message = data.get("message", {})
    text = message.get("text", "").strip()
    chat_id = message.get("chat", {}).get("id")

    if text.lower() == "/start":
        send_welcome_photo(chat_id)

        welcome_text = (
            "🇩🇰 *Вітаємо на нашому новинному каналі!*\n\n"
            "Тут ви знайдете найсвіжіші новини про події в Данії. "
            "Ми тримаємо вас у курсі всіх важливих змін та новинок у країні.\n\n"
            "🔐 *Чи даєте ви згоду на обробку персональних даних?*\n"
            "[Ознайомитись з політикою →](https://bevarukraine.dk/uk/osobysti-dani/)"
        )
        msg_id = send_message(chat_id, welcome_text,
                              reply_markup=consent_buttons())
        last_warnings[user_id] = msg_id
        return {"status": "consent_requested"}

    old_warning_id = last_warnings.get(user_id)
    if old_warning_id:
        delete_message(chat_id, old_warning_id)

    warning_text = (
        "⚠️ Спочатку потрібно дати згоду на обробку персональних даних, "
        "щоб користуватись ботом.\n\n"
        "[Ознайомитись з політикою →](https://bevarukraine.dk/uk/osobysti-dani/)"
    )
    new_msg_id = send_message(chat_id, warning_text,
                              reply_markup=consent_buttons())
    last_warnings[user_id] = new_msg_id
    return {"status": "forced_consent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
