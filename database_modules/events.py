import aiosqlite
from datetime import datetime

from .database_schema import get_events_db_path, get_guild_config_db_path, EVENTS_SCHEMA


def _now_iso():
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Table initialisation (per-guild events.db)
# ---------------------------------------------------------------------------
async def ensure_events_tables(guild_id: str):
    """Create events tables if they don't exist yet."""
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(EVENTS_SCHEMA)
        await conn.commit()


# ---------------------------------------------------------------------------
# Guild-level settings (stored in guild_config.db)
# ---------------------------------------------------------------------------
async def get_event_settings(guild_id: str):
    """Return event reminder settings for a guild, creating defaults if missing."""
    db_path = get_guild_config_db_path()
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT guild_id, channel_id, updated_at "
            "FROM event_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)

        now = _now_iso()
        await conn.execute(
            "INSERT INTO event_settings (guild_id, channel_id, updated_at) "
            "VALUES (?, NULL, ?)",
            (guild_id, now),
        )
        await conn.commit()
        return {
            "guild_id": guild_id,
            "channel_id": None,
            "updated_at": now,
        }


async def update_event_settings(guild_id: str, channel_id: str | None):
    """Update event reminder channel for a guild."""
    await get_event_settings(guild_id)  # ensures row exists
    db_path = get_guild_config_db_path()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "UPDATE event_settings SET channel_id = ?, updated_at = ? "
            "WHERE guild_id = ?",
            (channel_id, _now_iso(), guild_id),
        )
        await conn.commit()
    return await get_event_settings(guild_id)


# ---------------------------------------------------------------------------
# Event CRUD (per-guild events.db)
# ---------------------------------------------------------------------------
async def create_event(guild_id: str, creator_id: str, title: str,
                       description: str | None, event_timestamp: int) -> int:
    """Create a new event and return its ID."""
    await ensure_events_tables(guild_id)
    db_path = get_events_db_path(guild_id)
    now = _now_iso()
    event_time = datetime.utcfromtimestamp(event_timestamp).isoformat()
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "INSERT INTO events (guild_id, creator_id, title, description, "
            "event_time, event_timestamp, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (guild_id, creator_id, title, description, event_time, event_timestamp, now),
        )
        await conn.commit()
        return cursor.lastrowid


async def get_event(guild_id: str, event_id: int):
    """Fetch a single event by ID."""
    await ensure_events_tables(guild_id)
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM events WHERE id = ? AND guild_id = ?",
            (event_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def cancel_event(guild_id: str, event_id: int):
    """Mark an event as cancelled."""
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "UPDATE events SET cancelled = 1 WHERE id = ? AND guild_id = ?",
            (event_id, guild_id),
        )
        await conn.commit()


async def get_upcoming_events(guild_id: str, now_ts: int):
    """Return active future events for a guild."""
    await ensure_events_tables(guild_id)
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM events "
            "WHERE guild_id = ? AND cancelled = 0 AND event_timestamp > ? "
            "ORDER BY event_timestamp ASC",
            (guild_id, now_ts),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_events_needing_reminder(guild_id: str, now_ts: int, window_ts: int):
    """Return events within the reminder window that haven't been reminded yet."""
    await ensure_events_tables(guild_id)
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM events "
            "WHERE guild_id = ? AND cancelled = 0 AND reminder_sent = 0 "
            "AND event_timestamp > ? AND event_timestamp <= ?",
            (guild_id, now_ts, window_ts),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def mark_reminder_sent(guild_id: str, event_id: int):
    """Mark an event's reminder as sent."""
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "UPDATE events SET reminder_sent = 1 WHERE id = ? AND guild_id = ?",
            (event_id, guild_id),
        )
        await conn.commit()


# ---------------------------------------------------------------------------
# Attendees
# ---------------------------------------------------------------------------
async def add_attendee(guild_id: str, event_id: int, user_id: str):
    """Add a user to an event's attendee list."""
    db_path = get_events_db_path(guild_id)
    now = _now_iso()
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO event_attendees (event_id, user_id, joined_at) "
            "VALUES (?, ?, ?)",
            (event_id, user_id, now),
        )
        await conn.commit()


async def remove_attendee(guild_id: str, event_id: int, user_id: str):
    """Remove a user from an event's attendee list."""
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "DELETE FROM event_attendees WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        )
        await conn.commit()


async def get_attendees(guild_id: str, event_id: int) -> list[str]:
    """Return list of attendee user IDs for an event."""
    db_path = get_events_db_path(guild_id)
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute(
            "SELECT user_id FROM event_attendees WHERE event_id = ? ORDER BY joined_at ASC",
            (event_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]
