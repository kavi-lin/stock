"""Reinstalled Futu clients must feed the existing notification consumers."""
import datetime
import sqlite3
from pathlib import Path

import pytest

from scripts import parse_futu_notifications as futu


@pytest.fixture
def layouts(tmp_path, monkeypatch):
    legacy = tmp_path / "cn.futu.Niuniu/Data/Documents/com_tencent_imsdk_data"
    native = tmp_path / "cn.futu.niuniu.nx/Data/Library/Application Support/Logs/TIMLogs"
    prefix = str(Path.home() / "Library/Containers")
    assert all(pattern.startswith(prefix) for pattern in futu.MSG_DB_PATTERNS)
    monkeypatch.setattr(futu, "MSG_DB_PATTERNS", tuple(
        pattern.replace(prefix, str(tmp_path), 1) for pattern in futu.MSG_DB_PATTERNS
    ))
    return legacy, native


def write_push(root, epoch, text):
    path = root / "test_account/msg_0.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE message (time INTEGER, sender TEXT, element_descriptions TEXT)")
        conn.execute("INSERT INTO message VALUES (?, ?, ?)", (epoch, "10025", text))
    return path


@pytest.mark.parametrize("layout", [0, 1])
def test_each_client_layout_reaches_notification_entry(layouts, layout):
    write_push(layouts[layout], 100, "NVDA announces earnings growth")
    assert futu.is_available()
    items = futu.load_notifications()
    assert len(items) == 1
    assert items[0]["time"] == 100
    assert items[0]["tickers"] == ["NVDA"]


def test_reinstall_is_discovered_without_module_reload(layouts):
    assert not futu.is_available()
    assert futu.load_notifications() == []
    write_push(layouts[1], 200, "NVDA announces earnings growth")
    assert futu.is_available()
    assert futu.load_notifications()[0]["time"] == 200


def test_new_messages_sort_ahead_of_old_install(layouts):
    write_push(layouts[0], 100, "NVDA announces old earnings")
    write_push(layouts[1], 200, "NVDA announces new earnings")
    assert [item["time"] for item in futu.load_notifications()] == [200, 100]
    assert futu.load_notifications(limit=1)[0]["time"] == 200


def test_unreadable_old_db_does_not_hide_native_pushes(layouts):
    old = layouts[0] / "broken/msg_0.db"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"not a sqlite database")
    write_push(layouts[1], 200, "NVDA announces earnings growth")
    assert len(futu.load_notifications()) == 1


def test_connections_are_read_only_and_closed(layouts, monkeypatch):
    write_push(layouts[1], 200, "NVDA announces earnings growth")
    connect = sqlite3.connect
    opened = []

    def checked_connect(*args, **kwargs):
        conn = connect(*args, **kwargs)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM message")
        opened.append(conn)
        return conn

    monkeypatch.setattr(futu.sqlite3, "connect", checked_connect)
    assert len(futu.load_notifications()) == 1
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")


def test_native_push_reaches_break_news_with_existing_filters(layouts):
    now = int(datetime.datetime.now().timestamp())
    path = write_push(layouts[1], now, "NVDA announces strong earnings growth")
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO message VALUES (?, ?, ?)", (now + 1, "10025", "港股今日大漲 NVIDIA"))
    items, stats = futu.load_for_break_news()
    assert len(items) == 1
    assert items[0]["source"] == "Futu Push"
    assert items[0]["tickers"] == ["NVDA"]
    assert stats["filtered_hk_cn"] == 1
