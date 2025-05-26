import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

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


def format_news_text(news_item):
    doc = news_item.get("document", {})
    meta = doc.get("metadata", {})

    title = doc.get("title", "")
    content = doc.get("content", "")
    author = meta.get("author") or meta.get("source", "berlingske.dk")
    pub_time = meta.get(
        "publication_time") or datetime.now().strftime("%d.%m.%Y")
    source = meta.get("source", "")

    header = f"📰 *{title}*\n\n"
    footer = f"\n\n🕒 {pub_time}\n✍️ {author}\n🔗 [Читати новину]({source})"

    max_content_len = 1024 - len(header) - len(footer)
    short_content = content[:max_content_len].rstrip() + "..."

    return header + short_content + footer
