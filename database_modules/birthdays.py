import aiosqlite
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from .database_schema import get_birthdays_db_path, get_guild_config_db_path


def _now_iso():
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Guild-level settings (stored in guild_config.db)
# ---------------------------------------------------------------------------
async def get_birthday_settings(guild_id: str):
    """Return birthday settings for a guild, creating defaults if missing."""
    db_path = get_guild_config_db_path()
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT guild_id, channel_id, message_template, updated_at "
            "FROM birthday_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)

        # create default row
        now = _now_iso()
        await conn.execute(
            "INSERT INTO birthday_settings (guild_id, channel_id, message_template, updated_at) "
            "VALUES (?, NULL, 'Happy birthday, {user}! 🎂', ?)",
            (guild_id, now),
        )
        await conn.commit()
        return {
            "guild_id": guild_id,
            "channel_id": None,
            "message_template": "Happy birthday, {user}! 🎂",
            "updated_at": now,
        }


async def update_birthday_settings(guild_id: str, channel_id: str | None, message_template: str | None):
    """Update birthday settings for a guild."""
    settings = await get_birthday_settings(guild_id)  # ensures row exists
    db_path = get_guild_config_db_path()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "UPDATE birthday_settings SET channel_id = ?, message_template = ?, updated_at = ? "
            "WHERE guild_id = ?",
            (channel_id, message_template or settings["message_template"], _now_iso(), guild_id),
        )
        await conn.commit()
    return await get_birthday_settings(guild_id)


# ---------------------------------------------------------------------------
# User birthdays (per-guild birthdays.db)
# ---------------------------------------------------------------------------
async def set_birthday(guild_id: str, user_id: str, month: int, day: int, timezone: str):
    """Insert or update a user's birthday."""
    db_path = get_birthdays_db_path(guild_id)
    now = _now_iso()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """
            INSERT INTO birthdays (user_id, guild_id, month, day, timezone, last_announced_year, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
                month=excluded.month,
                day=excluded.day,
                timezone=excluded.timezone,
                updated_at=excluded.updated_at
            """,
            (user_id, guild_id, month, day, timezone, now, now),
        )
        await conn.commit()


async def get_birthday(guild_id: str, user_id: str):
    """Fetch a user's birthday record."""
    db_path = get_birthdays_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM birthdays WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def remove_birthday(guild_id: str, user_id: str):
    """Remove a birthday entry."""
    db_path = get_birthdays_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "DELETE FROM birthdays WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await conn.commit()


async def birthdays_for_date(guild_id: str, month: int, day: int):
    """Return birthdays matching a month/day."""
    db_path = get_birthdays_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM birthdays WHERE guild_id = ? AND month = ? AND day = ?",
            (guild_id, month, day),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_all_birthdays(guild_id: str):
    """Return all birthday rows for a guild."""
    db_path = get_birthdays_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM birthdays WHERE guild_id = ?", (guild_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def mark_announced(guild_id: str, user_id: str, year: int):
    """Update last_announced_year to the provided year."""
    db_path = get_birthdays_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "UPDATE birthdays SET last_announced_year = ?, updated_at = ? WHERE guild_id = ? AND user_id = ?",
            (year, _now_iso(), guild_id, user_id),
        )
        await conn.commit()


# Utility
def validate_timezone(tz_name: str) -> bool:
    """Return True if tz_name is a valid IANA timezone."""
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False

