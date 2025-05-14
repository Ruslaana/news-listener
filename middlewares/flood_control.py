import time

user_violations = {}
user_strikes = {}
blocked_users = {}
permanent_ban = set()
active_blocks = {}

ADMIN_EMAIL = "test@admin.dk"


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
        return True, f"🚷 Ви заблоковані назавжди. Зверніться до {ADMIN_EMAIL}", False

    if user_id in blocked_users:
        entry = blocked_users[user_id]
        if now >= entry["unblock_at"]:
            del blocked_users[user_id]
            user_violations.pop(user_id, None)
            user_strikes.pop(user_id, None)
        else:
            user_violations[user_id] = user_violations.get(user_id, 0) + 1
            count = user_violations[user_id]

            if count == 3:
                user_strikes[user_id] = 2
                blocked_users[user_id] = {
                    "unblock_at": now + 180, "chat_id": chat_id}
                track_blocked_user(user_id, chat_id)
                return True, (
                    "🚫 Ви написали під час блокування. Блок подовжено до 3 хвилин.\n\n"
                    "(Після завершення блоку бот автоматично нагадає про згоду.)"
                ), False

            elif count >= 4:
                user_strikes[user_id] = 3
                permanent_ban.add(user_id)
                del blocked_users[user_id]
                return True, f"🚷 Ви заблоковані назавжди. Зверніться до {ADMIN_EMAIL}", False

            else:
                remaining = int(entry["unblock_at"] - now)
                return True, (
                    f"⏳ Ви знаходитесь під блокуванням. Залишилось {format_time(remaining)}."
                ), False

    new_count = user_violations.get(user_id, 0) + 1
    user_violations[user_id] = new_count

    if new_count == 1:
        return True, (
            "⚠️ Спершу потрібно дати згоду на обробку персональних даних.\n\n"
            "🔐 [Ознайомитись з політикою](https://bevarukraine.dk/uk/osobysti-dani/)\n\n"
            "Без згоди користуватись ботом неможливо. Якщо ви напишете ще раз, "
            "то бот заблокує вас на 1 хвилину.\n\n"
        ), True

    elif new_count == 2:
        user_strikes[user_id] = 1
        blocked_users[user_id] = {"unblock_at": now + 60, "chat_id": chat_id}
        track_blocked_user(user_id, chat_id)
        return True, (
            f"🚫 Ви тимчасово заблоковані на {format_time(60)} за ігнорування згоди.\n\n"
            "(Після завершення блоку бот автоматично нагадає про згоду.)"
        ), False

    return True, "⚠️ Невідома дія. Підтвердіть згоду або зачекайте.", True


def track_blocked_user(user_id, chat_id):
    if chat_id:
        active_blocks[user_id] = chat_id


def get_expired_unblocks():
    now = time.time()
    expired = []
    for user_id, entry in list(blocked_users.items()):
        if now >= entry["unblock_at"]:
            chat_id = entry.get("chat_id") or active_blocks.pop(user_id, None)
            if chat_id:
                expired.append((user_id, chat_id))
            del blocked_users[user_id]
            user_violations.pop(user_id, None)
            user_strikes.pop(user_id, None)
    return expired
