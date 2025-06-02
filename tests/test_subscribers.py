import pytest
from bot.subscribers import load_subscribers, save_subscribers, add_subscriber


def test_load_subscribers_when_file_does_not_exist(tmp_path):
    fake_file = tmp_path / "subscribers.json"
    subs = load_subscribers(str(fake_file))
    assert subs == []


def test_save_and_load_subscribers(tmp_path):
    fake_file = tmp_path / "subscribers.json"
    expected = [111, 222]
    save_subscribers(expected, str(fake_file))
    loaded = load_subscribers(str(fake_file))
    assert loaded == expected


def test_add_subscriber_adds_new(tmp_path, capsys):
    fake_file = tmp_path / "subscribers.json"
    save_subscribers([], str(fake_file))
    add_subscriber(12345, str(fake_file))
    subs = load_subscribers(str(fake_file))
    assert 12345 in subs
    assert "Added subscriber: 12345" in capsys.readouterr().out


def test_add_subscriber_skips_existing(tmp_path, capsys):
    fake_file = tmp_path / "subscribers.json"
    save_subscribers([999], str(fake_file))
    add_subscriber(999, str(fake_file))
    subs = load_subscribers(str(fake_file))
    assert subs == [999]
    assert "Subscriber already exists: 999" in capsys.readouterr().out
