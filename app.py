from flask import Flask, request
import requests
import json
import os
from dotenv import load_dotenv
from flask_ngrok import run_with_ngrok

load_dotenv()

app = Flask(__name__)
run_with_ngrok(app)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received message: ", json.dumps(data, indent=4))

    chat_id = data['message']['chat']['id']
    message_text = "Привіт, я отримав твоє повідомлення!"

    send_to_telegram(chat_id, message_text)
    return "OK"


def send_to_telegram(chat_id, message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, data=data)


if __name__ == '__main__':
    app.run(debug=True)
