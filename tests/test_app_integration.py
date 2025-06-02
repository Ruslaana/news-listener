import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app import app, last_warnings, user_strikes, process_unblocked_once

client = TestClient(app)


def test_get_subscribers(tmp_path, monkeypatch):
    subs_path = tmp_path / "subscribers.json"
    subs_path.write_text('[123, 456]')
    monkeypatch.setattr("app.SUBSCRIBERS_FILE", str(subs_path))

    response = client.get("/subscribers")
    assert response.status_code == 200
    assert response.json() == [123, 456]


def test_get_blocked(tmp_path, monkeypatch):
    blocked_path = tmp_path / "blocked.json"
    blocked_path.write_text('[789]')
    monkeypatch.setattr("app.BLOCKED_FILE", str(blocked_path))

    response = client.get("/blocked")
    assert response.status_code == 200
    assert response.json() == [789]


def test_get_blocked_empty(tmp_path, monkeypatch):
    blocked_path = tmp_path / "blocked.json"
    blocked_path.write_text('[]')
    monkeypatch.setattr("app.BLOCKED_FILE", str(blocked_path))

    response = client.get("/blocked")
    assert response.status_code == 200
    assert response.json() == []


def test_process_unblocked_once(monkeypatch):
    monkeypatch.setattr("app.get_expired_unblocks", lambda: [])
    process_unblocked_once()


def test_process_unblocked_endpoint(monkeypatch):
    monkeypatch.setattr("app.get_expired_unblocks", lambda: [])
    response = client.post("/process-unblocked")
    assert response.status_code == 200
    assert response.json() == {"status": "done"}


@patch("app.send_welcome_photo", return_value=111)
@patch("app.send_message", return_value=222)
def test_webhook_start(mock_send_msg, mock_send_photo):
    payload = {
        "message": {
            "message_id": 1,
            "from": {"id": 123},
            "chat": {"id": 123},
            "text": "/start"
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "consent_requested"
    assert mock_send_photo.called
    assert mock_send_msg.called


@patch("app.send_message")
@patch("app.delete_message")
@patch("app.send_first_news")
@patch("app.reset_user_state")
@patch("app.add_subscriber")
def test_webhook_callback_accept(mock_add, mock_reset, mock_send_first, mock_delete, mock_send):
    payload = {
        "callback_query": {
            "data": "accept",
            "message": {"message_id": 1, "chat": {"id": 123}},
            "from": {"id": 123}
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "callback_handled"
    assert mock_add.called
    assert mock_reset.called
    assert mock_send_first.called
    assert mock_send.called


@patch("app.send_message", return_value=333)
@patch("app.delete_message")
@patch("app.check_flood", return_value=(True, "\u23f3 Flood triggered", False))
@patch("app.track_blocked_user")
def test_webhook_callback_decline(mock_track, mock_check, mock_delete, mock_send):
    payload = {
        "callback_query": {
            "data": "decline",
            "message": {"message_id": 1, "chat": {"id": 123}},
            "from": {"id": 123}
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "flood_control_applied"
    assert mock_track.called
    assert mock_check.called
    assert mock_send.called


@patch("app.send_message", return_value=444)
@patch("app.delete_message")
@patch("app.check_flood", return_value=(True, "\u23f3 Flood again", True))
@patch("app.track_blocked_user")
def test_webhook_text_flood(mock_track, mock_check, mock_delete, mock_send):
    payload = {
        "message": {
            "message_id": 2,
            "from": {"id": 999},
            "chat": {"id": 999},
            "text": "hello"
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "flood_control_applied"
    assert mock_check.called
    assert mock_send.called


@patch("app.send_message", return_value=321)
@patch("app.delete_message")
def test_webhook_fallback_message(mock_delete, mock_send):
    payload = {
        "message": {
            "message_id": 55,
            "from": {"id": 9876},
            "chat": {"id": 9876},
            "text": "unknown"
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] in (
        "flood_control_applied", "consent_forced")
    assert mock_send.called


@patch("app.send_message", return_value=555)
@patch("app.delete_message")
def test_webhook_callback_decline_no_flood(mock_delete, mock_send):
    with patch("app.check_flood", return_value=(False, "", False)):
        payload = {
            "callback_query": {
                "data": "decline",
                "message": {"message_id": 1, "chat": {"id": 123}},
                "from": {"id": 123}
            }
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "callback_handled"
        assert mock_send.called


@patch("app.send_message")
@patch("app.requests.get", side_effect=Exception("Request failed"))
def test_send_first_news_exception(mock_get, mock_send):
    from app import send_first_news
    send_first_news(999)
    mock_send.assert_called_once_with(
        999, "\u26a0\ufe0f \u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044f \u0437\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0438\u0442\u0438 \u043d\u043e\u0432\u0438\u043d\u0443.")


@patch("app.requests.get")
@patch("app.send_message")
def test_send_first_news_no_news(mock_send, mock_get):
    from app import send_first_news
    mock_get.return_value.status_code = 500
    send_first_news(123)
    mock_send.assert_called_once()


@patch("app.requests.get")
@patch("app.send_message")
def test_send_first_news_no_document(mock_send, mock_get):
    from app import send_first_news
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {}
    send_first_news(123)
    mock_send.assert_called_once()


@patch("app.requests.get")
@patch("app.send_message")
def test_send_first_news_partial_data(mock_send, mock_get):
    from app import send_first_news
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "document": {},
        "title": None,
        "summary": None
    }
    send_first_news(123)
    mock_send.assert_called()


@patch("app.requests.post")
@patch("app.requests.get")
def test_send_first_news_with_image(mock_get, mock_post):
    from app import send_first_news
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "document": {
            "metadata": {"image_url": "http://example.com/image.png"}
        },
        "title": "Test",
        "summary": "Test summary",
        "published_at": "2024-06-01T12:00:00"
    }
    send_first_news(123)
    assert mock_post.called


@patch("app.get_expired_unblocks", return_value=[(123, 456)])
@patch("app.send_message", return_value=888)
@patch("app.delete_message")
def test_process_unblocked_strike_0(mock_delete, mock_send, mock_unblocks):
    last_warnings.clear()
    user_strikes.clear()
    process_unblocked_once()
    assert mock_send.called


@patch("app.requests.post")
@patch("builtins.open", create=True)
def test_send_welcome_photo(mock_open, mock_post):
    from app import send_welcome_photo
    mock_open.return_value.__enter__.return_value = b"fakeimage"
    mock_post.return_value.json.return_value = {"result": {"message_id": 777}}
    msg_id = send_welcome_photo(111)
    assert msg_id == 777
    mock_post.assert_called()


@patch("app.send_message", return_value=333)
def test_webhook_unknown_payload(mock_send):
    payload = {"update_id": 12345678}
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "consent_forced"
    mock_send.assert_called()
