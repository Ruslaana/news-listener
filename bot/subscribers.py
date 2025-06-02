import json
import os

SUBSCRIBERS_FILE = "data/subscribers.json"


def load_subscribers(filepath=SUBSCRIBERS_FILE):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_subscribers(data, filepath=SUBSCRIBERS_FILE):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f)


def add_subscriber(subscriber_id, filepath=SUBSCRIBERS_FILE):
    subs = load_subscribers(filepath)
    if subscriber_id not in subs:
        subs.append(subscriber_id)
        save_subscribers(subs, filepath)
        print(f"Added subscriber: {subscriber_id}")
    else:
        print(f"Subscriber already exists: {subscriber_id}")
