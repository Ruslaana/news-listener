import json
import boto3
import requests
from datetime import date
from moto import mock_s3
from unittest.mock import patch
from bot.scheduler import (
    load_sent_ids,
    save_sent_ids,
    is_news_already_sent,
    mark_news_as_sent,
    fetch_news,
    fetch_and_send_news,
    schedule_news_tasks,
    SENT_IDS_KEY
)

# ==== S3-Related Tests ====


@mock_s3
def test_load_sent_ids_from_existing_file(monkeypatch):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    import bot.scheduler
    monkeypatch.setattr(bot.scheduler, "s3", s3)
    monkeypatch.setattr(bot.scheduler, "AWS_BUCKET_NAME", "test-bucket")

    today = date.today().isoformat()
    test_data = {today: ["news123"]}
    s3.put_object(
        Bucket="test-bucket",
        Key=SENT_IDS_KEY,
        Body=json.dumps(test_data).encode("utf-8")
    )

    result = load_sent_ids()
    assert result[today] == ["news123"]


@mock_s3
def test_save_sent_ids(monkeypatch):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    import bot.scheduler
    monkeypatch.setattr(bot.scheduler, "s3", s3)
    monkeypatch.setattr(bot.scheduler, "AWS_BUCKET_NAME", "test-bucket")

    today = date.today().isoformat()
    data = {today: ["news999"]}
    save_sent_ids(data)

    response = s3.get_object(Bucket="test-bucket", Key=SENT_IDS_KEY)
    saved = json.loads(response["Body"].read().decode("utf-8"))
    assert saved[today] == ["news999"]


@patch("bot.scheduler.s3.get_object", side_effect=Exception("generic error"))
def test_load_sent_ids_generic_exception(mock_get, capsys):
    import bot.scheduler
    result = bot.scheduler.load_sent_ids()
    today = date.today().isoformat()
    assert today in result
    captured = capsys.readouterr()
    assert "❌ Помилка при завантаженні sent_news_ids" in captured.out


@patch("bot.scheduler.s3.put_object", side_effect=Exception("upload failed"))
def test_save_sent_ids_error(monkeypatch, capsys):
    import bot.scheduler
    monkeypatch.setattr(bot.scheduler, "AWS_BUCKET_NAME", "dummy-bucket")
    bot.scheduler.save_sent_ids({"dummy": ["data"]})
    captured = capsys.readouterr()
    assert "❌ Помилка при збереженні sent_news_ids" in captured.out

# ==== Logic Tests ====


def test_is_news_already_sent_true():
    today = date.today().isoformat()
    sent_data = {today: ["abc123"]}
    assert is_news_already_sent("abc123", sent_data) is True


def test_is_news_already_sent_false():
    today = date.today().isoformat()
    sent_data = {today: ["abc123"]}
    assert is_news_already_sent("xyz999", sent_data) is False


def test_mark_news_as_sent_adds_to_today():
    today = date.today().isoformat()
    sent_data = {}
    mark_news_as_sent("xyz123", sent_data)
    assert sent_data[today] == ["xyz123"]


def test_mark_news_as_sent_no_duplicates():
    today = date.today().isoformat()
    sent_data = {today: ["xyz123"]}
    mark_news_as_sent("xyz123", sent_data)
    assert sent_data[today] == ["xyz123"]

# ==== fetch_news ====


def test_fetch_news_success(monkeypatch):
    def mock_get(url):
        class MockResponse:
            status_code = 200

            def json(self):
                return {"document": {"id": "abc"}}
        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)
    import bot.scheduler
    monkeypatch.setattr(bot.scheduler, "API_URL", "http://fake.api")

    result = fetch_news("latest")
    assert result == {"document": {"id": "abc"}}


def test_fetch_news_failure_status(monkeypatch, capsys):
    def mock_get(url):
        class MockResponse:
            status_code = 500
        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)
    import bot.scheduler
    monkeypatch.setattr(bot.scheduler, "API_URL", "http://fake.api")

    result = fetch_news("latest")
    assert result is None
    captured = capsys.readouterr()
    assert "❌ API error" in captured.out


def test_fetch_news_exception(monkeypatch, capsys):
    def mock_get(url):
        raise requests.exceptions.RequestException("fail")

    monkeypatch.setattr("requests.get", mock_get)
    import bot.scheduler
    monkeypatch.setattr(bot.scheduler, "API_URL", "http://fake.api")

    result = fetch_news("latest")
    assert result is None
    captured = capsys.readouterr()
    assert "🔥 Error fetching news" in captured.out

# ==== fetch_and_send_news ====


@patch("bot.scheduler.load_subscribers", return_value=[])
def test_fetch_and_send_news_no_subscribers(mock_subs, capsys):
    fetch_and_send_news()
    captured = capsys.readouterr()
    assert "Немає підписників" in captured.out


@patch("bot.scheduler.fetch_news", return_value=None)
@patch("bot.scheduler.load_subscribers", return_value=[123])
@patch("bot.scheduler.load_sent_ids", return_value={})
def test_fetch_and_send_news_both_fetches_none(mock_sent, mock_subs, mock_fetch, capsys):
    fetch_and_send_news()
    captured = capsys.readouterr()
    assert "⚠️ Архів порожній або помилка" in captured.out


@patch("bot.scheduler.fetch_news", return_value={})
@patch("bot.scheduler.load_subscribers", return_value=[123])
@patch("bot.scheduler.load_sent_ids", return_value={})
def test_fetch_and_send_news_no_document(mock_sent, mock_subs, mock_fetch, capsys):
    fetch_and_send_news()
    captured = capsys.readouterr()
    assert "⚠️ Архів порожній або помилка" in captured.out


@patch("bot.scheduler.send_message", return_value=None)
@patch("bot.scheduler.fetch_news", return_value={"document": {}})
@patch("bot.scheduler.load_subscribers", return_value=[111])
@patch("bot.scheduler.load_sent_ids", return_value={})
def test_fetch_and_send_news_document_without_id(mock_sent, mock_subs, mock_fetch, mock_send):
    fetch_and_send_news()
    mock_send.assert_called_once()


@patch("bot.scheduler.send_message", side_effect=Exception("send fail"))
@patch("bot.scheduler.fetch_news", return_value={"document": {"id": "xyz"}})
@patch("bot.scheduler.load_subscribers", return_value=[111])
@patch("bot.scheduler.load_sent_ids", return_value={})
def test_fetch_and_send_news_send_message_error(mock_sent, mock_subs, mock_fetch, mock_send):
    fetch_and_send_news()
    mock_send.assert_called_once()

# ==== Scheduler Scheduling ====


@patch("bot.scheduler.send_message", return_value=None)
@patch("bot.scheduler.fetch_news", side_effect=[
    {"document": {"id": "xyz"}},
    {}
])
@patch("bot.scheduler.load_subscribers", return_value=[111])
@patch("bot.scheduler.load_sent_ids", return_value={date.today().isoformat(): ["xyz"]})
def test_fetch_and_send_news_fallback_without_document(mock_sent, mock_subs, mock_fetch, mock_send):
    fetch_and_send_news()
    assert mock_fetch.call_count == 2


def test_schedule_news_tasks():
    schedule_news_tasks()
