import pytest
from unittest.mock import patch, ANY
from datetime import date
from bot.scheduler import fetch_and_send_news


@patch("bot.scheduler.send_message", return_value=None)
@patch("bot.scheduler.load_sent_ids", return_value={})
@patch("bot.scheduler.load_subscribers", return_value=[111])
@patch("bot.scheduler.fetch_news", side_effect=[None, None])
def test_fetch_and_send_news_latest_none(mock_fetch, mock_subs, mock_sent, mock_send):
    fetch_and_send_news()
    assert mock_fetch.call_args_list == [(("latest",),), (("random",),)]


@patch("bot.scheduler.send_message", return_value=None)
@patch("bot.scheduler.load_sent_ids", return_value={date.today().isoformat(): ["abc"]})
@patch("bot.scheduler.load_subscribers", return_value=[111])
@patch("bot.scheduler.fetch_news", side_effect=[
    {"document": {"id": "abc"}},  # latest
    None                          # random
])
def test_fetch_and_send_news_random_none_after_duplicate(mock_fetch, mock_subs, mock_sent, mock_send):
    fetch_and_send_news()
    assert mock_fetch.call_count == 2


@patch("bot.scheduler.send_message", return_value=None)
@patch("bot.scheduler.load_sent_ids", return_value={date.today().isoformat(): ["abc"]})
@patch("bot.scheduler.load_subscribers", return_value=[111])
@patch("bot.scheduler.fetch_news", side_effect=[
    {"document": {"id": "abc"}},  # latest
    {"document": {"id": "abc"}}   # random, але дубль
])
def test_fetch_and_send_news_random_duplicate(mock_fetch, mock_subs, mock_sent, mock_send):
    fetch_and_send_news()
    assert mock_fetch.call_count == 2


@patch("bot.scheduler.send_message", return_value=None)
@patch("bot.scheduler.load_sent_ids", return_value={})
@patch("bot.scheduler.load_subscribers", return_value=[111, 222])
@patch("bot.scheduler.fetch_news", return_value={"document": {"id": "xyz"}})
def test_fetch_and_send_news_success(mock_fetch, mock_subs, mock_sent, mock_send):
    fetch_and_send_news()
    mock_send.assert_any_call(111, ANY)
    mock_send.assert_any_call(222, ANY)
    assert mock_fetch.call_count == 1
