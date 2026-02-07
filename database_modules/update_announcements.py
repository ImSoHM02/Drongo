import aiosqlite
from datetime import datetime

from .database_schema import get_guild_config_db_path


def _now_iso():
    return datetime.utcnow().isoformat()


async def get_update_settings(guild_id: str):
    """Return update announcement settings for a guild, creating defaults if missing."""
    db_path = get_guild_config_db_path()
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT guild_id, channel_id, updated_at "
            "FROM update_announcement_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)

        # create default row (disabled)
        now = _now_iso()
        await conn.execute(
            "INSERT INTO update_announcement_settings (guild_id, channel_id, updated_at) "
            "VALUES (?, NULL, ?)",
            (guild_id, now),
        )
        await conn.commit()
        return {
            "guild_id": guild_id,
            "channel_id": None,
            "updated_at": now,
        }


async def update_settings(guild_id: str, channel_id: str | None):
    """Update announcement channel for a guild."""
    await get_update_settings(guild_id)  # ensures row exists
    db_path = get_guild_config_db_path()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "UPDATE update_announcement_settings SET channel_id = ?, updated_at = ? "
            "WHERE guild_id = ?",
            (channel_id, _now_iso(), guild_id),
        )
        await conn.commit()
    return await get_update_settings(guild_id)


async def get_all_configured_channels():
    """Return all guilds with configured announcement channels."""
    db_path = get_guild_config_db_path()
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT guild_id, channel_id FROM update_announcement_settings "
            "WHERE channel_id IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
