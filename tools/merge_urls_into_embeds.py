#!/usr/bin/env python3
"""
Merge legacy per-guild urls.db into embeds.db (urls table now lives alongside embeds).

Usage:
  python3 tools/merge_urls_into_embeds.py

Safe to re-run; skips if urls.db missing or urls table already populated.
"""

import os
import sqlite3
import glob
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "database"


def ensure_urls_table(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            url TEXT NOT NULL,
            domain TEXT NOT NULL,
            url_position INTEGER,
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_urls_message ON urls (message_id);
        CREATE INDEX IF NOT EXISTS idx_urls_user ON urls (user_id, guild_id);
        CREATE INDEX IF NOT EXISTS idx_urls_domain ON urls (domain);
        """
    )


def migrate_guild(guild_dir: Path):
    urls_path = guild_dir / "urls.db"
    embeds_path = guild_dir / "embeds.db"

    if not urls_path.exists():
        return
    if not embeds_path.exists():
        print(f"[SKIP] embeds.db missing for guild {guild_dir.name}")
        return

    urls_conn = sqlite3.connect(urls_path)
    emb_conn = sqlite3.connect(embeds_path)
    urls_conn.row_factory = sqlite3.Row
    try:
        ensure_urls_table(emb_conn)

        rows = urls_conn.execute("SELECT * FROM urls").fetchall()
        if not rows:
            print(f"[OK] No URLs to migrate for guild {guild_dir.name}")
            return

        emb_conn.executemany(
            """
            INSERT OR IGNORE INTO urls (
                id, message_id, user_id, guild_id, channel_id,
                url, domain, url_position, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"],
                    row["message_id"],
                    row["user_id"],
                    row["guild_id"],
                    row["channel_id"],
                    row["url"],
                    row["domain"],
                    row["url_position"],
                    row["timestamp"],
                )
                for row in rows
            ],
        )
        emb_conn.commit()
        print(f"[OK] Migrated {len(rows)} URLs into embeds.db for guild {guild_dir.name}")
    finally:
        urls_conn.close()
        emb_conn.close()


def main():
    guild_dirs = [Path(p) for p in glob.glob(str(BASE / "[0-9]*")) if os.path.isdir(p)]
    if not guild_dirs:
        print("No guild databases found.")
        return
    for g in guild_dirs:
        migrate_guild(g)


if __name__ == "__main__":
    main()
