import time
import json
import os

BLOCKS_FILE = "bot/blocks.json"

user_strikes = {}
blocked_users = {}
permanent_ban = set()
active_blocks = {}

ADMIN_EMAIL = "test@admin.dk"


def save_blocked():
    os.makedirs("bot", exist_ok=True)

    if not blocked_users and not permanent_ban and not active_blocks:
        if os.path.exists(BLOCKS_FILE):
            os.remove(BLOCKS_FILE)
        return

    data = {
        "blocked_users": blocked_users,
        "permanent_ban": list(permanent_ban),
        "active_blocks": active_blocks
    }

    with open(BLOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_blocked():
    os.makedirs("bot", exist_ok=True)
    if not os.path.exists(BLOCKS_FILE):
        return

    with open(BLOCKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        global blocked_users, permanent_ban, active_blocks
        blocked_users = data.get("blocked_users", {})
        permanent_ban = set(data.get("permanent_ban", []))
        active_blocks = data.get("active_blocks", {})


def load_blocked_users(path="blocked.json"):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {"active_blocks": {}, "permanent_ban": []}


def get_all_blocked_users():
    return {
        "blocked_users": blocked_users,
        "permanent_ban": list(permanent_ban),
        "active_blocks": active_blocks
    }


def format_time(seconds):
    minutes = seconds // 60
    if minutes == 1:
        return "1 хвилину"
    elif 2 <= minutes <= 4:
        return f"{minutes} хвилини"
    else:
        return f"{minutes} хвилин"


def check_flood(user_id, chat_id=None):
    now = time.time()

    if user_id in permanent_ban:
        return True, f"😷 Ви заблоковані назавжди. Зверніться до {ADMIN_EMAIL}", False

    if user_id in blocked_users:
        entry = blocked_users[user_id]
        if now < entry["unblock_at"]:
            remaining = int(entry["unblock_at"] - now)
            return True, f"⏳ Ви під блокуванням. Залишилось {format_time(remaining)}.", False
        else:
            del blocked_users[user_id]
            save_blocked()

    strikes = user_strikes.get(user_id, 0)

    if strikes == 0:
        user_strikes[user_id] = -1  # попередження
        return True, (
            "⚠️ Спершу потрібно дати згоду на обробку персональних даних.\n\n"
            "🔐 [Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)\n\n"
            "❗ Якщо ви натиснете ще раз \"Ні\" — буде блокування на 1 хвилину."
        ), True

    elif strikes == -1:
        user_strikes[user_id] = 1
        blocked_users[user_id] = {"unblock_at": now + 60, "chat_id": chat_id}
        track_blocked_user(user_id, chat_id)
        save_blocked()
        return True, (
            "🚫 Ви тимчасово заблоковані на 1 хвилину за ігнорування згоди.\n\n"
            "Після завершення блоку бот автоматично нагадає про згоду."
        ), False

    elif strikes == 1:
        user_strikes[user_id] = 2
        blocked_users[user_id] = {"unblock_at": now + 180, "chat_id": chat_id}
        track_blocked_user(user_id, chat_id)
        save_blocked()
        return True, (
            "🚫 Ви знову порушили умови. Блок подовжено до 3 хвилин.\n\n"
            "Після завершення блоку бот знову запропонує дати згоду."
        ), False

    elif strikes >= 2:
        user_strikes[user_id] = 3
        permanent_ban.add(user_id)
        blocked_users.pop(user_id, None)
        save_blocked()
        return True, (
            f"😷 Ви заблоковані назавжди. Зверніться до адміністратора: {ADMIN_EMAIL}"
        ), False

    return True, (
        "⚠️ Потрібно дати згоду на обробку персональних даних.\n\n"
        "🔐 [Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)"
    ), True


def track_blocked_user(user_id, chat_id):
    if chat_id:
        active_blocks[user_id] = chat_id
        save_blocked()


def get_expired_unblocks():
    now = time.time()
    expired = []
    for user_id, entry in list(blocked_users.items()):
        if now >= entry["unblock_at"]:
            chat_id = entry.get("chat_id") or active_blocks.pop(user_id, None)
            if chat_id:
                expired.append((user_id, chat_id))
            del blocked_users[user_id]
    if expired:
        save_blocked()
    return expired


def reset_user_state(user_id):
    user_strikes.pop(user_id, None)
    blocked_users.pop(user_id, None)
    active_blocks.pop(user_id, None)
    if user_id in permanent_ban:
        permanent_ban.remove(user_id)
    save_blocked()


load_blocked()
