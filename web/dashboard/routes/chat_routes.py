import logging
import os

import aiosqlite
from quart import Blueprint, jsonify, request

from .. import state
from ..name_resolution import resolve_user_name

chat_bp = Blueprint("dashboard_chat", __name__)


@chat_bp.route("/api/chat/guilds", methods=["GET"])
async def get_chat_guilds():
    """Get all guilds with chat logging info."""
    try:
        from database_modules.database_utils import get_all_guild_settings, get_guild_message_count, is_guild_scanning
        from database_modules.database_schema import get_guild_config_db_path

        guild_settings = await get_all_guild_settings()
        guilds_data = []

        for settings in guild_settings:
            guild_id = settings["guild_id"]
            message_count = await get_guild_message_count(guild_id)
            scanning = await is_guild_scanning(guild_id)

            config_db_path = get_guild_config_db_path()
            async with aiosqlite.connect(config_db_path) as conn:
                async with conn.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN fetch_completed = 1 THEN 1 ELSE 0 END) as completed
                    FROM historical_fetch_progress
                    WHERE guild_id = ?
                """, (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                    total_channels = row[0] if row and row[0] else 0
                    completed_channels = row[1] if row and row[1] else 0

                from database_modules.database_schema import get_guild_db_path

                guild_db_path = get_guild_db_path(guild_id)
                last_message_time = None

                if os.path.exists(guild_db_path):
                    async with aiosqlite.connect(guild_db_path) as guild_conn:
                        async with guild_conn.execute("""
                            SELECT timestamp FROM messages
                            ORDER BY timestamp DESC LIMIT 1
                        """) as cursor:
                            row = await cursor.fetchone()
                            if row:
                                last_message_time = row[0]

            fetch_percentage = 0
            if total_channels > 0:
                fetch_percentage = int((completed_channels / total_channels) * 100)

            guilds_data.append({
                "guild_id": guild_id,
                "guild_name": settings["guild_name"],
                "logging_enabled": bool(settings["logging_enabled"]),
                "total_messages": message_count,
                "channels_count": total_channels,
                "date_joined": settings["date_joined"],
                "last_message_time": last_message_time,
                "is_scanning": scanning,
                "fetch_progress": {
                    "completed": completed_channels == total_channels and total_channels > 0,
                    "percentage": fetch_percentage,
                    "channels_done": completed_channels,
                    "channels_total": total_channels
                }
            })

        return jsonify({"guilds": guilds_data})

    except Exception as e:
        logging.error(f"Error fetching chat guilds: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/guild/<guild_id>/settings", methods=["GET", "POST"])
async def guild_chat_settings(guild_id):
    """Get or update guild chat settings."""
    try:
        from database_modules.database_utils import get_guild_settings, update_guild_logging

        if request.method == "GET":
            settings = await get_guild_settings(guild_id)
            if not settings:
                return jsonify({"error": "Guild not found"}), 404
            return jsonify(settings)

        data = await request.get_json()
        enabled = data.get("logging_enabled", True)
        await update_guild_logging(guild_id, enabled)
        return jsonify({"success": True})

    except Exception as e:
        logging.error(f"Error managing guild settings: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/guild/<guild_id>/channels", methods=["GET"])
async def get_guild_channels(guild_id):
    """Get all channels for a guild with message counts."""
    try:
        from database_modules.database_schema import get_guild_db_path

        guild_db_path = get_guild_db_path(guild_id)

        if not os.path.exists(guild_db_path):
            return jsonify({"channels": []})

        channels_data = []

        async with aiosqlite.connect(guild_db_path) as conn:
            async with conn.execute("""
                SELECT channel_id, COUNT(*) as message_count
                FROM messages
                GROUP BY channel_id
                ORDER BY message_count DESC
            """) as cursor:
                rows = await cursor.fetchall()

                for row in rows:
                    channel_id, message_count = row

                    channel_name = f"Channel {channel_id}"
                    if state.bot_instance:
                        try:
                            channel = state.bot_instance.get_channel(int(channel_id))
                            if channel:
                                channel_name = channel.name
                        except Exception:
                            pass

                    channels_data.append({
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "message_count": message_count
                    })

        return jsonify({"channels": channels_data})

    except Exception as e:
        logging.error(f"Error fetching guild channels: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/guild/<guild_id>/messages", methods=["GET"])
async def get_guild_messages(guild_id):
    """Get messages for a guild/channel."""
    try:
        from database_modules.database_schema import get_guild_db_path

        channel_id = request.args.get("channel_id")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        guild_db_path = get_guild_db_path(guild_id)

        if not os.path.exists(guild_db_path):
            return jsonify({"messages": [], "total": 0, "has_more": False})

        async with aiosqlite.connect(guild_db_path) as conn:
            conn.row_factory = aiosqlite.Row

            if channel_id:
                query = """
                    SELECT * FROM messages
                    WHERE channel_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """
                params = (channel_id, limit, offset)

                count_query = "SELECT COUNT(*) FROM messages WHERE channel_id = ?"
                count_params = (channel_id,)
            else:
                query = """
                    SELECT * FROM messages
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """
                params = (limit, offset)

                count_query = "SELECT COUNT(*) FROM messages"
                count_params = ()

            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                messages = []

                for row in rows:
                    msg_dict = dict(row)
                    user_name = await resolve_user_name(msg_dict["user_id"])

                    channel_name = f"Channel {msg_dict['channel_id']}"
                    if state.bot_instance:
                        try:
                            channel = state.bot_instance.get_channel(int(msg_dict["channel_id"]))
                            if channel:
                                channel_name = channel.name
                        except Exception:
                            pass

                    messages.append({
                        "id": msg_dict["id"],
                        "user_id": msg_dict["user_id"],
                        "username": user_name,
                        "channel_id": msg_dict["channel_id"],
                        "channel_name": channel_name,
                        "message_content": msg_dict["message_content"],
                        "timestamp": msg_dict["timestamp"]
                    })

            async with conn.execute(count_query, count_params) as cursor:
                total = (await cursor.fetchone())[0]

        has_more = (offset + limit) < total

        return jsonify({
            "messages": messages,
            "total": total,
            "has_more": has_more
        })

    except Exception as e:
        logging.error(f"Error fetching guild messages: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/guild/<guild_id>/recent", methods=["GET"])
async def get_recent_messages(guild_id):
    """Get recent 50 messages for a guild."""
    try:
        from database_modules.database_schema import get_guild_db_path

        channel_id = request.args.get("channel_id")

        guild_db_path = get_guild_db_path(guild_id)

        if not os.path.exists(guild_db_path):
            return jsonify({"messages": []})

        async with aiosqlite.connect(guild_db_path) as conn:
            conn.row_factory = aiosqlite.Row

            if channel_id:
                query = """
                    SELECT * FROM messages
                    WHERE channel_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 50
                """
                params = (channel_id,)
            else:
                query = """
                    SELECT * FROM messages
                    ORDER BY timestamp DESC
                    LIMIT 50
                """
                params = ()

            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                messages = []

                for row in rows:
                    msg_dict = dict(row)
                    user_name = await resolve_user_name(msg_dict["user_id"])

                    channel_name = f"Channel {msg_dict['channel_id']}"
                    if state.bot_instance:
                        try:
                            channel = state.bot_instance.get_channel(int(msg_dict["channel_id"]))
                            if channel:
                                channel_name = channel.name
                        except Exception:
                            pass

                    messages.append({
                        "id": msg_dict["id"],
                        "user_id": msg_dict["user_id"],
                        "username": user_name,
                        "channel_id": msg_dict["channel_id"],
                        "channel_name": channel_name,
                        "message_content": msg_dict["message_content"],
                        "timestamp": msg_dict["timestamp"]
                    })

        return jsonify({"messages": messages})

    except Exception as e:
        logging.error(f"Error fetching recent messages: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/guild/<guild_id>/stats", methods=["GET"])
async def get_guild_chat_stats(guild_id):
    """Get statistics for a guild."""
    try:
        from database_modules.database_utils import get_guild_message_count, is_guild_scanning
        from database_modules.database_schema import get_guild_config_db_path, get_guild_db_path

        message_count = await get_guild_message_count(guild_id)
        scanning = await is_guild_scanning(guild_id)

        guild_db_path = get_guild_db_path(guild_id)
        oldest_message = None
        newest_message = None
        active_channels = 0

        if os.path.exists(guild_db_path):
            async with aiosqlite.connect(guild_db_path) as conn:
                async with conn.execute("""
                    SELECT timestamp FROM messages
                    ORDER BY timestamp ASC LIMIT 1
                """) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        oldest_message = row[0]

                async with conn.execute("""
                    SELECT timestamp FROM messages
                    ORDER BY timestamp DESC LIMIT 1
                """) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        newest_message = row[0]

                async with conn.execute("""
                    SELECT COUNT(DISTINCT channel_id) FROM messages
                """) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        active_channels = row[0]

        config_db_path = get_guild_config_db_path()
        async with aiosqlite.connect(config_db_path) as conn:
            async with conn.execute("""
                SELECT
                    SUM(total_fetched) as total_fetched,
                    COUNT(*) as channels_tracking,
                    SUM(CASE WHEN fetch_completed = 1 THEN 1 ELSE 0 END) as channels_completed
                FROM historical_fetch_progress
                WHERE guild_id = ?
            """, (guild_id,)) as cursor:
                row = await cursor.fetchone()
                total_fetched = row[0] if row and row[0] else 0
                channels_tracking = row[1] if row and row[1] else 0
                channels_completed = row[2] if row and row[2] else 0

        return jsonify({
            "total_messages": message_count,
            "active_channels": active_channels,
            "oldest_message": oldest_message,
            "newest_message": newest_message,
            "is_scanning": scanning,
            "fetch_stats": {
                "total_fetched": total_fetched,
                "channels_tracking": channels_tracking,
                "channels_completed": channels_completed
            }
        })

    except Exception as e:
        logging.error(f"Error fetching guild stats: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/fetch-progress", methods=["GET"])
async def get_fetch_progress():
    """Get historical fetch progress for all guilds."""
    try:
        from database_modules.database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        progress_data = []

        async with aiosqlite.connect(config_db_path) as conn:
            conn.row_factory = aiosqlite.Row

            async with conn.execute("""
                SELECT
                    guild_id,
                    COUNT(*) as total_channels,
                    SUM(CASE WHEN fetch_completed = 1 THEN 1 ELSE 0 END) as completed_channels,
                    SUM(total_fetched) as total_fetched,
                    MAX(last_fetch_timestamp) as last_fetch
                FROM historical_fetch_progress
                GROUP BY guild_id
            """) as cursor:
                rows = await cursor.fetchall()

                for row in rows:
                    row_dict = dict(row)
                    total = row_dict["total_channels"]
                    completed = row_dict["completed_channels"]
                    percentage = int((completed / total) * 100) if total > 0 else 0

                    progress_data.append({
                        "guild_id": row_dict["guild_id"],
                        "total_channels": total,
                        "completed_channels": completed,
                        "total_fetched": row_dict["total_fetched"] or 0,
                        "percentage": percentage,
                        "last_fetch": row_dict["last_fetch"],
                        "is_complete": completed == total and total > 0
                    })

        return jsonify({"progress": progress_data})

    except Exception as e:
        logging.error(f"Error fetching progress: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/guild/<guild_id>/fetch-all", methods=["POST"])
async def trigger_full_fetch(guild_id):
    """Trigger a full historical fetch for all channels in a guild."""
    try:
        from database_modules.database_utils import queue_channel_for_historical_fetch

        if not state.bot_instance:
            return jsonify({"error": "Bot instance not available"}), 503

        if not getattr(state.bot_instance, "historical_fetcher", None):
            return jsonify({"error": "Historical fetcher not initialized"}), 503
        if not state.bot_instance.historical_fetcher.running:
            await state.bot_instance.historical_fetcher.start()

        guild = state.bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        queued_channels = []
        for channel in guild.text_channels:
            try:
                if channel.permissions_for(guild.me).read_message_history:
                    await queue_channel_for_historical_fetch(
                        guild_id=str(guild.id),
                        channel_id=str(channel.id),
                        channel_name=channel.name,
                        priority=0,
                        force=True,
                        reset_progress=True
                    )
                    queued_channels.append({
                        "id": str(channel.id),
                        "name": channel.name
                    })
            except Exception as e:
                logging.error(f"Error queueing channel {channel.name}: {e}")

        return jsonify({
            "success": True,
            "message": f"Queued {len(queued_channels)} channels for historical fetch",
            "channels": queued_channels
        })

    except Exception as e:
        logging.error(f"Error triggering full fetch: {e}")
        return jsonify({"error": str(e)}), 500
