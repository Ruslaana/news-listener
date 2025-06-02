import time
import pytest
import middlewares.flood_control as flood_control


def setup_function():
    flood_control.user_strikes.clear()
    flood_control.blocked_users.clear()
    flood_control.permanent_ban.clear()
    flood_control.active_blocks.clear()


def test_check_flood_initial_warning():
    is_blocked, message, require_consent = flood_control.check_flood(123)
    assert is_blocked is True
    assert "⚠️" in message
    assert require_consent is True
    assert flood_control.user_strikes[123] == -1


def test_check_flood_temporary_block():
    flood_control.check_flood(123)  # -1
    is_blocked, message, require_consent = flood_control.check_flood(123)
    assert is_blocked is True
    assert "🚫" in message
    assert require_consent is False
    assert 123 in flood_control.blocked_users


def test_check_flood_block_expired(monkeypatch):
    now = time.time()
    flood_control.blocked_users[123] = {"unblock_at": now - 1}
    monkeypatch.setattr(flood_control, "save_blocked", lambda: None)

    is_blocked, _, _ = flood_control.check_flood(123)
    assert is_blocked is True
    assert 123 not in flood_control.blocked_users


def test_check_flood_permanent_ban():
    flood_control.permanent_ban.add(999)
    is_blocked, message, _ = flood_control.check_flood(999)
    assert is_blocked is True
    assert "назавжди" in message


def test_check_flood_permanent_after_strikes(monkeypatch):
    user_id = 1
    flood_control.check_flood(user_id)
    flood_control.check_flood(user_id)

    flood_control.blocked_users[user_id]["unblock_at"] = time.time() - 1
    flood_control.check_flood(user_id)

    flood_control.blocked_users[user_id]["unblock_at"] = time.time() - 1
    is_blocked, message, _ = flood_control.check_flood(
        user_id)

    assert is_blocked is True
    assert "назавжди" in message
    assert user_id in flood_control.permanent_ban


def test_get_expired_unblocks(monkeypatch):
    now = time.time()
    flood_control.blocked_users[123] = {"unblock_at": now - 5, "chat_id": 555}
    monkeypatch.setattr(flood_control, "save_blocked", lambda: None)
    expired = flood_control.get_expired_unblocks()
    assert expired == [(123, 555)]
    assert 123 not in flood_control.blocked_users


def test_format_time():
    assert flood_control.format_time(30) == "0 хвилин"
    assert flood_control.format_time(60) == "1 хвилину"
    assert flood_control.format_time(150) == "2 хвилини"
    assert flood_control.format_time(300) == "5 хвилин"


def test_reset_user_state():
    flood_control.user_strikes[123] = 3
    flood_control.blocked_users[123] = {"unblock_at": time.time() + 10}
    flood_control.active_blocks[123] = 456
    flood_control.permanent_ban.add(123)

    flood_control.reset_user_state(123)
    assert 123 not in flood_control.user_strikes
    assert 123 not in flood_control.blocked_users
    assert 123 not in flood_control.active_blocks
    assert 123 not in flood_control.permanent_ban
