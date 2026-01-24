import os
import aiosqlite
from datetime import datetime
from typing import Optional

from .database_schema import get_guild_db_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS wow_mains (
    guild_id TEXT NOT NULL,
    discord_user_id TEXT NOT NULL,
    region TEXT NOT NULL,
    realm_slug TEXT NOT NULL,
    character_slug TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (guild_id, discord_user_id)
);
CREATE INDEX IF NOT EXISTS idx_wow_mains_guild ON wow_mains (guild_id);
"""


def get_wow_main_db_path(guild_id: str) -> str:
    base_dir = get_guild_db_dir(guild_id)
    return os.path.join(base_dir, "wow_mains.db")


async def ensure_db(guild_id: str) -> str:
    path = get_wow_main_db_path(guild_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiosqlite.connect(path) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()
    return path


async def set_main(guild_id: str, discord_user_id: str, region: str, realm_slug: str, character_slug: str) -> None:
    path = await ensure_db(guild_id)
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(path) as conn:
        await conn.execute(
            """
            INSERT INTO wow_mains (guild_id, discord_user_id, region, realm_slug, character_slug, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, discord_user_id) DO UPDATE SET
                region = excluded.region,
                realm_slug = excluded.realm_slug,
                character_slug = excluded.character_slug,
                updated_at = excluded.updated_at
            """,
            (guild_id, discord_user_id, region, realm_slug, character_slug, now),
        )
        await conn.commit()


async def get_main(guild_id: str, discord_user_id: str) -> Optional[dict]:
    path = get_wow_main_db_path(guild_id)
    if not os.path.exists(path):
        return None
    async with aiosqlite.connect(path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT guild_id, discord_user_id, region, realm_slug, character_slug, updated_at
            FROM wow_mains
            WHERE guild_id = ? AND discord_user_id = ?
            """,
            (guild_id, discord_user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
