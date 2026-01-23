import aiosqlite
from datetime import datetime
from typing import Dict, Set

from .database_schema import get_guild_config_db_path


def _normalize_name(command_name: str) -> str:
    """Normalize command names for storage."""
    return command_name.strip().lower()


async def get_command_overrides(guild_id: str) -> Dict[str, bool]:
    """
    Return stored command overrides for a guild.

    Returns a mapping of command_name -> enabled flag. Missing commands imply default enabled.
    """
    config_db_path = get_guild_config_db_path()

    async with aiosqlite.connect(config_db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT command_name, enabled FROM command_overrides WHERE guild_id = ?",
            (str(guild_id),),
        ) as cursor:
            rows = await cursor.fetchall()

    return {row["command_name"]: bool(row["enabled"]) for row in rows}


async def get_disabled_commands(guild_id: str) -> Set[str]:
    """Return the set of disabled command names for a guild."""
    overrides = await get_command_overrides(guild_id)
    return {name for name, enabled in overrides.items() if not enabled}


async def set_command_overrides(guild_id: str, overrides: Dict[str, bool]) -> None:
    """
    Replace command overrides for a guild.

    Args:
        guild_id: Discord guild ID
        overrides: Mapping of command_name -> enabled flag
    """
    if overrides is None:
        return

    normalized = {_normalize_name(name): bool(enabled) for name, enabled in overrides.items()}
    config_db_path = get_guild_config_db_path()
    now = datetime.now().isoformat()

    async with aiosqlite.connect(config_db_path) as conn:
        await conn.execute("BEGIN")
        await conn.execute("DELETE FROM command_overrides WHERE guild_id = ?", (str(guild_id),))

        for name, enabled in normalized.items():
            await conn.execute(
                """
                INSERT INTO command_overrides (guild_id, command_name, enabled, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, command_name) DO UPDATE SET
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (str(guild_id), name, 1 if enabled else 0, now),
            )

        await conn.commit()
