import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


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

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json().get("result", {}).get("message_id")
        else:
            print(
                f"❌ Error sending message to {chat_id}: {response.status_code} {response.text}")
    except Exception as e:
        print(f"🔥 Exception sending message: {e}")
    return None


def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
    data = {
        "chat_id": chat_id,
        "message_id": message_id
    }

    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"🔥 Exception deleting message: {e}")
