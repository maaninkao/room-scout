"""SQLite storage layer for tracking seen and notified listings."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from room_scout.models import Listing


class Storage:
    def __init__(self, db_path: str):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                slug TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                notified_at TEXT,
                payload_json TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def mark_seen(self, listing: Listing) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        payload = listing.model_dump_json()
        existing = self._conn.execute(
            "SELECT first_seen_at FROM seen_listings WHERE slug = ?", (listing.slug,)
        ).fetchone()
        if existing is None:
            self._conn.execute(
                "INSERT INTO seen_listings (slug, first_seen_at, last_seen_at, payload_json) VALUES (?, ?, ?, ?)",
                (listing.slug, now, now, payload),
            )
            self._conn.commit()
            return True
        self._conn.execute(
            "UPDATE seen_listings SET last_seen_at = ?, payload_json = ? WHERE slug = ?",
            (now, payload, listing.slug),
        )
        self._conn.commit()
        return False

    def mark_notified(self, slug: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE seen_listings SET notified_at = ? WHERE slug = ?", (now, slug)
        )
        self._conn.commit()

    def was_notified(self, slug: str) -> bool:
        row = self._conn.execute(
            "SELECT notified_at FROM seen_listings WHERE slug = ?", (slug,)
        ).fetchone()
        return row is not None and row[0] is not None

    def close(self) -> None:
        self._conn.close()
