"""Local persistent storage for field reports."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
HISTORY_PATH = APP_DIR / "data" / "field_history.sqlite3"


def read_history() -> list[dict]:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(HISTORY_PATH, timeout=10)) as connection, connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS field_visits "
            "(id INTEGER PRIMARY KEY, saved_at TEXT NOT NULL, "
            "field_name TEXT NOT NULL, report_json TEXT NOT NULL)"
        )
        count = connection.execute("SELECT COUNT(*) FROM field_visits").fetchone()[0]
        legacy_path = HISTORY_PATH.with_name("field_history.json")
        if count == 0 and legacy_path.exists():
            legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
            if not isinstance(legacy, list) or any(not isinstance(item, dict) for item in legacy):
                raise ValueError("Legacy field history has an unexpected format and was left untouched.")
            connection.executemany(
                "INSERT INTO field_visits (saved_at, field_name, report_json) VALUES (?, ?, ?)",
                [
                    (
                        item.get("field", {}).get("created_at", ""),
                        item.get("field", {}).get("name", "Unnamed field"),
                        json.dumps(item, ensure_ascii=False),
                    )
                    for item in legacy
                ],
            )
        rows = connection.execute("SELECT report_json FROM field_visits ORDER BY id").fetchall()
    return [json.loads(row[0]) for row in rows]


def append_history(report: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(HISTORY_PATH, timeout=10)) as connection, connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS field_visits "
            "(id INTEGER PRIMARY KEY, saved_at TEXT NOT NULL, "
            "field_name TEXT NOT NULL, report_json TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO field_visits (saved_at, field_name, report_json) VALUES (?, ?, ?)",
            (
                report.get("field", {}).get("created_at", ""),
                report.get("field", {}).get("name", "Unnamed field"),
                json.dumps(report, ensure_ascii=False),
            ),
        )
