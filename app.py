from flask import Flask, request
import requests
import json
import os
from dotenv import load_dotenv
from flask_ngrok import run_with_ngrok
from fastapi import FastAPI
from fastapi import Request

load_dotenv()

app = FastAPI()


@app.post('/webhook')
async def webhook(request: Request):
    data = await request.json()
    response_text = data['message']['text']
    print("Received data:", data)
    send_to_telegram(data['message']['chat']['id'], response_text)
    return {"status": "success"}


def send_to_telegram(chat_id, message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, data=data)
    print("Response from Telegram:", response.json())
    return response.json()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
