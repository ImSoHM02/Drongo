import aiosqlite
from datetime import datetime
from typing import Dict, Optional

from .database_schema import get_guild_config_db_path


async def get_ai_mode(guild_id: str) -> Optional[str]:
    """Return the stored AI mode for a guild, or None if not set."""
    config_db_path = get_guild_config_db_path()
    async with aiosqlite.connect(config_db_path) as conn:
        async with conn.execute(
            "SELECT mode FROM ai_mode_overrides WHERE guild_id = ?",
            (str(guild_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_all_ai_modes() -> Dict[str, str]:
    """Return a mapping of guild_id -> mode for all stored overrides."""
    config_db_path = get_guild_config_db_path()
    async with aiosqlite.connect(config_db_path) as conn:
        async with conn.execute("SELECT guild_id, mode FROM ai_mode_overrides") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def set_ai_mode(guild_id: str, mode: str) -> None:
    """Persist the AI mode for a guild."""
    config_db_path = get_guild_config_db_path()
    now = datetime.now().isoformat()
    async with aiosqlite.connect(config_db_path) as conn:
        await conn.execute(
            """
            INSERT INTO ai_mode_overrides (guild_id, mode, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                mode = excluded.mode,
                updated_at = excluded.updated_at
            """,
            (str(guild_id), mode, now),
        )
        await conn.commit()
