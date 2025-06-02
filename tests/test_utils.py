import json
import pytest
from unittest.mock import patch, MagicMock
from bot.utils import send_message, delete_message, format_news_text


def test_format_news_text_with_all_fields():
    long_content = "Це контент новини." * 100
    news_item = {
        "document": {
            "title": "Новина",
            "content": long_content,
            "metadata": {
                "author": "Автор",
                "publication_time": "01.01.2025",
                "source": "https://example.com",
                "image_url": "https://example.com/image.jpg"
            }
        }
    }
    text = format_news_text(news_item)

    assert text.startswith("📰 *Новина*")
    assert "✍️ Автор" in text
    assert "🔗 [Читати новину](https://example.com)" in text

    header = "📰 *Новина*\n\n"
    footer = "\n\n🕒 01.01.2025\n✍️ Автор\n🔗 [Читати новину](https://example.com)"
    max_content_len = 1024 - len(header) - len(footer)
    assert text[len(header):-len(footer)].endswith("...")
    assert len(text) <= 1024


@patch("bot.utils.requests.post")
def test_send_message_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"result": {"message_id": 123}}
    result = send_message(111, "Привіт")
    assert result == 123


@patch("bot.utils.requests.post")
def test_send_message_failure(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response

    result = send_message(123456, "test")
    assert result is None


@patch("bot.utils.requests.post", side_effect=Exception("Connection error"))
def test_send_message_exception(mock_post):
    result = send_message(111, "Привіт")
    assert result is None


@patch("bot.utils.requests.post")
def test_delete_message(mock_post):
    delete_message(111, 222)
    mock_post.assert_called_once()


@patch("bot.utils.requests.post", side_effect=Exception("Delete error"))
def test_delete_message_exception(mock_post):
    delete_message(111, 222)
