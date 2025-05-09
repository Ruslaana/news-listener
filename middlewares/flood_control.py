import time

message_log = {}
blocked_users = {}
warned_users = set()


def check_flood(user_id: int) -> tuple[bool, str | None]:
    now = time.time()

    if user_id in blocked_users:
        unblock_at = blocked_users[user_id]
        if now < unblock_at:
            wait = int(unblock_at - now)
            return True, f"⛔ Ви заблоковані за спам. Спробуйте через {wait} сек."
        else:
            del blocked_users[user_id]

    timestamps = message_log.get(user_id, [])
    timestamps = [t for t in timestamps if now - t <= 5]
    timestamps.append(now)
    message_log[user_id] = timestamps

    if len(timestamps) >= 5:
        blocked_users[user_id] = now + 60
        warned_users.discard(user_id)
        return True, "🚫 Ви були тимчасово заблоковані за надмірну кількість повідомлень. Повторіть через 1 хвилину."

    if len(timestamps) >= 3 and user_id not in warned_users:
        warned_users.add(user_id)
        return True, "⚠️ Будь ласка, не надсилайте повідомлення надто часто. Ще кілька — і вас буде заблоковано."

    return False, None
