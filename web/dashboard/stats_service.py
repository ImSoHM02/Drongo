import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Dict, List

import aiosqlite

from . import state
from .name_resolution import resolve_guild_name
from .paths import DATABASE_DIR


class RealTimeStats:
    def __init__(self):
        self.stats = {
            "messages_processed": 0,
            "commands_executed": 0,
            "active_users": 0,
            "uptime": "0:00:00",
            "status": "Disconnected",
            "memory_usage": 0,
            "cpu_usage": 0,
            "bot_guilds": 0,
            "database_size": 0
        }
        self.recent_messages = deque(maxlen=10)
        self.recent_events = deque(maxlen=10)
        self.start_time = None
        self.message_rate_history = deque(maxlen=60)
        self.command_rate_history = deque(maxlen=60)
        self.last_command_count = 0

    def update_stat(self, key: str, value):
        """Update a statistic value."""
        self.stats[key] = value

    def add_message_log(self, author: str, guild: str, channel: str):
        """Add a message to recent messages log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        message_log = {
            "timestamp": timestamp,
            "author": author,
            "guild": guild,
            "channel": channel,
            "type": "message"
        }
        self.recent_messages.appendleft(message_log)

    def add_event_log(self, event: str, event_type: str = "info"):
        """Add an event to recent events log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        event_log = {
            "timestamp": timestamp,
            "event": event,
            "type": event_type
        }
        self.recent_events.appendleft(event_log)

    def set_status(self, status: str):
        """Set bot status and update start time."""
        self.stats["status"] = status
        self.add_event_log(f"Bot {status}", "status")

        if status == "Connected" and self.start_time is None:
            self.start_time = time.time()
        elif status in ["Disconnected", "Offline"]:
            self.start_time = None

    def update_uptime(self):
        """Update uptime calculation."""
        if self.start_time:
            uptime_seconds = int(time.time() - self.start_time)
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.stats["uptime"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.stats["uptime_seconds"] = uptime_seconds
        else:
            self.stats["uptime"] = "00:00:00"
            self.stats["uptime_seconds"] = 0

    def update_rates(self):
        """Update message and command rates."""
        current_time = time.time()

        self.message_rate_history.append({
            "time": current_time,
            "count": self.stats["messages_processed"]
        })

        self.command_rate_history.append({
            "time": current_time,
            "count": self.stats["commands_executed"]
        })

        cutoff_time = current_time - 60
        self.message_rate_history = deque(
            [entry for entry in self.message_rate_history if entry["time"] >= cutoff_time],
            maxlen=60
        )
        self.command_rate_history = deque(
            [entry for entry in self.command_rate_history if entry["time"] >= cutoff_time],
            maxlen=60
        )

    def get_message_rate(self) -> float:
        """Calculate messages per minute."""
        if len(self.message_rate_history) < 2:
            return 0.0

        recent = self.message_rate_history[-1]
        old = self.message_rate_history[0]

        time_diff = recent["time"] - old["time"]
        count_diff = recent["count"] - old["count"]

        if time_diff > 0:
            return (count_diff / time_diff) * 60
        return 0.0

    def get_command_rate(self) -> float:
        """Calculate commands per minute."""
        if len(self.command_rate_history) < 2:
            return 0.0

        recent = self.command_rate_history[-1]
        old = self.command_rate_history[0]

        time_diff = recent["time"] - old["time"]
        count_diff = recent["count"] - old["count"]

        if time_diff > 0:
            return (count_diff / time_diff) * 60
        return 0.0


real_time_stats = RealTimeStats()


def _list_guild_db_paths() -> List[str]:
    """List all guild chat history database paths."""
    paths: List[str] = []
    if not os.path.isdir(DATABASE_DIR):
        return paths

    for entry in os.listdir(DATABASE_DIR):
        candidate = os.path.join(DATABASE_DIR, entry, "chat_history.db")
        if entry.isdigit() and os.path.isfile(candidate):
            paths.append(candidate)
    return paths


async def get_database_health():
    """Get aggregated database health information across guild databases."""
    try:
        db_paths = _list_guild_db_paths()
        total_size_bytes = 0

        for db_file in db_paths:
            try:
                total_size_bytes += os.path.getsize(db_file)
            except FileNotFoundError:
                continue

        system_databases = []

        system_db_files = {
            "leveling_system.db": "Leveling System",
            "command_stats.db": "Command Stats",
            "system.db": "System",
            "guild_config.db": "Guild Config",
            "chat_history.db": "Legacy Chat History"
        }

        for db_file, db_name in system_db_files.items():
            db_path = os.path.join(DATABASE_DIR, db_file)
            if os.path.exists(db_path):
                size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
                system_databases.append({
                    "name": db_name,
                    "file": db_file,
                    "size_mb": size_mb
                })

        return {
            "database_size_mb": round(total_size_bytes / (1024 * 1024), 2) if total_size_bytes else 0,
            "table_count": len(db_paths) * 3,
            "index_count": 0,
            "database_files": len(db_paths),
            "system_databases": system_databases
        }

    except Exception as e:
        logging.error(f"Error getting database health: {e}")
        return {
            "database_size_mb": 0,
            "table_count": 0,
            "index_count": 0,
            "database_files": 0,
            "system_databases": []
        }


async def get_enhanced_stats():
    """Get comprehensive stats for the dashboard."""
    try:
        from database_modules.database_utils import get_all_guild_settings, is_guild_scanning

        guild_db_paths = _list_guild_db_paths()
        total_messages = 0
        unique_users = 0
        recent_activity = 0
        guild_breakdown = []

        guild_settings = await get_all_guild_settings()
        guild_names = {s["guild_id"]: s["guild_name"] for s in guild_settings}

        for db_file in guild_db_paths:
            try:
                guild_id = os.path.basename(os.path.dirname(db_file))

                async with aiosqlite.connect(db_file) as conn:
                    async with conn.execute("SELECT COUNT(*) FROM messages") as cursor:
                        guild_messages = (await cursor.fetchone())[0]
                        total_messages += guild_messages

                    async with conn.execute("SELECT COUNT(DISTINCT user_id) FROM messages") as cursor:
                        guild_users = (await cursor.fetchone())[0]
                        unique_users += guild_users

                    async with conn.execute("""
                        SELECT COUNT(*) FROM messages
                        WHERE datetime(timestamp) > datetime('now', '-1 hour')
                    """) as cursor:
                        guild_recent = (await cursor.fetchone())[0]
                        recent_activity += guild_recent

                    async with conn.execute("SELECT COUNT(DISTINCT channel_id) FROM messages") as cursor:
                        guild_channels = (await cursor.fetchone())[0]

                    async with conn.execute("SELECT timestamp FROM messages ORDER BY timestamp DESC LIMIT 1") as cursor:
                        last_message_row = await cursor.fetchone()
                        last_message = last_message_row[0] if last_message_row else None

                db_size_mb = round(os.path.getsize(db_file) / (1024 * 1024), 2)
                is_scanning = await is_guild_scanning(guild_id)

                guild_name = guild_names.get(guild_id)
                if not guild_name:
                    guild_name = await resolve_guild_name(guild_id)

                guild_breakdown.append({
                    "guild_id": guild_id,
                    "guild_name": guild_name,
                    "total_messages": guild_messages,
                    "unique_users": guild_users,
                    "active_channels": guild_channels,
                    "recent_activity": guild_recent,
                    "database_size_mb": db_size_mb,
                    "last_message": last_message,
                    "is_scanning": is_scanning
                })

            except Exception as db_err:
                logging.error(f"Error aggregating stats from {db_file}: {db_err}")

        guild_breakdown.sort(key=lambda x: x["total_messages"], reverse=True)
        health_info = await get_database_health()
        bot_guilds_count = len(guild_breakdown)

        real_time_stats.update_stat("messages_processed", total_messages)
        real_time_stats.update_stat("active_users", unique_users)
        real_time_stats.update_stat("database_size", health_info["database_size_mb"])
        real_time_stats.update_stat("bot_guilds", bot_guilds_count)
        real_time_stats.update_uptime()
        real_time_stats.update_rates()

        stats = {
            **real_time_stats.stats,
            "recent_activity": recent_activity,
            "message_rate": round(real_time_stats.get_message_rate(), 1),
            "command_rate": round(real_time_stats.get_command_rate(), 1),
            "recent_messages": list(real_time_stats.recent_messages),
            "recent_events": list(real_time_stats.recent_events),
            "database_health": health_info,
            "guild_breakdown": guild_breakdown,
            "last_updated": datetime.now().isoformat()
        }

        return stats

    except Exception as e:
        logging.error(f"Error getting enhanced stats: {e}")
        return {
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }
