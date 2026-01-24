import logging
import os
import subprocess
import sys

import discord
from quart import Blueprint, jsonify, request

from .. import state
from ..broadcast import broadcast_stats
from ..name_resolution import validate_guild_id
from ..stats_service import get_enhanced_stats, real_time_stats
from database_modules.ai_mode_overrides import get_ai_mode

system_bp = Blueprint("dashboard_system", __name__)


@system_bp.route("/api/stats")
async def api_stats():
    """REST API endpoint for stats."""
    return jsonify(await get_enhanced_stats())


@system_bp.route("/api/system_info")
async def system_info():
    """Get system information."""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return jsonify({
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_total": memory.total // (1024 ** 3),
            "memory_used": memory.used // (1024 ** 3),
            "disk_usage": disk.percent,
            "disk_total": disk.total // (1024 ** 3),
            "disk_used": disk.used // (1024 ** 3)
        })
    except ImportError:
        return jsonify({
            "error": "psutil not available",
            "cpu_usage": 0,
            "memory_usage": 0
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@system_bp.route("/api/commands/list")
async def api_commands_list():
    """Get live list of available commands from the bot's command tree."""
    try:
        if not state.bot_instance or not state.bot_instance.is_ready():
            return jsonify({"error": "Bot is not ready"}), 503

        commands = []
        for cmd in state.bot_instance.tree.get_commands():
            # For groups, include top-level info; children handled in per-guild view
            commands.append({
                "name": cmd.name,
                "description": getattr(cmd, "description", "") or "No description",
            })
        return jsonify(commands)
    except Exception as e:
        logging.error(f"Error loading commands: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/commands/guild/<guild_id>", methods=["GET"])
async def api_guild_commands(guild_id):
    """Get commands and per-guild enablement states."""
    try:
        from database_modules.command_overrides import get_disabled_commands

        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return jsonify({"error": "Invalid guild_id"}), 400

        if not state.bot_instance or not state.bot_instance.is_ready():
            return jsonify({"error": "Bot is not ready"}), 503

        disabled = await get_disabled_commands(str(validated_guild_id))
        commands = []

        for command in state.bot_instance.tree.get_commands():
            subcommands = []
            if hasattr(command, "commands"):
                subcommands = [child.name for child in getattr(command, "commands", [])]

            commands.append({
                "name": command.name,
                "description": command.description,
                "type": getattr(getattr(command, "type", None), "name", "chat_input"),
                "subcommands": subcommands,
                "enabled": command.name.lower() not in disabled
            })

        return jsonify(commands)
    except Exception as e:
        logging.error(f"Error loading guild commands: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/commands/guild/<guild_id>", methods=["POST"])
async def api_update_guild_commands(guild_id):
    """Update per-guild command enablement and sync to Discord."""
    try:
        from database_modules.command_overrides import set_command_overrides

        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return jsonify({"error": "Invalid guild_id"}), 400

        data = await request.get_json()
        overrides = data.get("overrides") if data else None

        # Allow enabled/disabled lists as alternative input
        enabled_list = data.get("enabled_commands") if data else None
        disabled_list = data.get("disabled_commands") if data else None
        if (enabled_list or disabled_list) and overrides is None:
            overrides = {}
            if enabled_list:
                overrides.update({name: True for name in enabled_list})
            if disabled_list:
                overrides.update({name: False for name in disabled_list})

        if not overrides:
            return jsonify({"error": "No overrides provided"}), 400

        # Filter to known commands if bot is available
        bot_ready = state.bot_instance and state.bot_instance.is_ready()
        if bot_ready:
            available = {cmd.name.lower() for cmd in state.bot_instance.tree.get_commands()}
            overrides = {name: enabled for name, enabled in overrides.items() if name.lower() in available}

        if not overrides:
            return jsonify({"error": "No valid commands provided"}), 400

        await set_command_overrides(str(validated_guild_id), overrides)

        sync_status = "pending"
        if bot_ready:
            try:
                await state.bot_instance.sync_guild_commands(str(validated_guild_id))
                sync_status = "synced"
            except Exception as e:
                logging.error(f"Error syncing commands for guild {validated_guild_id}: {e}")
                sync_status = "sync_failed"

        return jsonify({
            "success": True,
            "sync_status": sync_status
        })
    except Exception as e:
        logging.error(f"Error updating guild commands: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/commands/register", methods=["POST"])
async def api_commands_register():
    """Register Discord commands."""
    try:
        return jsonify({"error": "Guild-specific registration is disabled; commands are synced by the bot"}), 400
    except Exception as e:
        logging.error(f"Error registering commands: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/commands/delete", methods=["POST"])
async def api_commands_delete():
    """Delete all Discord commands."""
    try:
        return jsonify({"error": "Command deletion via dashboard is disabled"}), 400
    except Exception as e:
        logging.error(f"Error deleting commands: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/ai/modes", methods=["GET"])
async def api_ai_modes():
    """List available AI modes."""
    try:
        if not state.bot_instance or not state.bot_instance.is_ready():
            return jsonify({"error": "Bot is not ready"}), 503

        configs = state.bot_instance.ai_handler.probability_manager.list_configs()
        modes = [
            {
                "name": cfg.name,
                "chance": cfg.total_chance,
                "insult_weight": cfg.insult_weight,
                "compliment_weight": cfg.compliment_weight,
            }
            for cfg in configs.values()
        ]
        return jsonify({"modes": modes})
    except Exception as e:
        logging.error(f"Error listing AI modes: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/ai/mode/<guild_id>", methods=["GET"])
async def api_get_ai_mode(guild_id):
    """Get current AI mode for a guild."""
    try:
        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return jsonify({"error": "Invalid guild_id"}), 400

        if not state.bot_instance or not state.bot_instance.is_ready():
            return jsonify({"error": "Bot is not ready"}), 503

        stored_mode = await get_ai_mode(str(validated_guild_id))
        active_mode = stored_mode or "default"

        return jsonify({
            "guild_id": str(validated_guild_id),
            "mode": active_mode
        })
    except Exception as e:
        logging.error(f"Error getting AI mode: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/ai/mode/<guild_id>", methods=["POST"])
async def api_set_ai_mode(guild_id):
    """Set AI mode for a guild and apply immediately."""
    try:
        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return jsonify({"error": "Invalid guild_id"}), 400

        data = await request.get_json()
        mode = (data or {}).get("mode")
        if not mode:
            return jsonify({"error": "mode is required"}), 400

        if not state.bot_instance or not state.bot_instance.is_ready():
            return jsonify({"error": "Bot is not ready"}), 503

        # Validate mode
        configs = state.bot_instance.ai_handler.probability_manager.list_configs()
        if mode not in configs:
            return jsonify({"error": "Invalid mode"}), 400

        await state.bot_instance.ai_handler.set_mode_for_guild(str(validated_guild_id), mode)

        return jsonify({"success": True, "mode": mode})
    except Exception as e:
        logging.error(f"Error setting AI mode: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/bot/restart", methods=["POST"])
async def api_bot_restart():
    """Restart the bot."""
    try:
        real_time_stats.add_event_log("Bot restart requested via dashboard", "system")
        await broadcast_stats()

        # Schedule the restart as an async task
        import asyncio
        asyncio.create_task(_perform_graceful_restart())

        return jsonify({"success": True, "message": "Bot restart initiated"})
    except Exception as e:
        logging.error(f"Error restarting bot: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/bot/shutdown", methods=["POST"])
async def api_bot_shutdown():
    """Shutdown the bot."""
    try:
        real_time_stats.add_event_log("Bot shutdown requested via dashboard", "system")
        await broadcast_stats()

        # Schedule the shutdown as an async task
        import asyncio
        asyncio.create_task(_perform_graceful_shutdown())

        return jsonify({"success": True, "message": "Bot shutdown initiated"})
    except Exception as e:
        logging.error(f"Error shutting down bot: {e}")
        return jsonify({"error": str(e)}), 500


async def _perform_graceful_restart():
    """Perform graceful shutdown and restart."""
    try:
        import asyncio
        # Wait for the response to send
        await asyncio.sleep(1)

        logging.info("Starting graceful restart...")

        await _cleanup_bot()

        # Wait for everything to settle
        await asyncio.sleep(1)

        # Restart the process
        logging.info("Executing restart...")

        # Use subprocess.Popen to start new process, then exit
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        logging.info("New process started, exiting...")
        sys.exit(0)

    except Exception as e:
        logging.error(f"Error during restart: {e}")
        # Still attempt to restart even if cleanup fails
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(1)


async def _perform_graceful_shutdown():
    """Perform graceful shutdown."""
    try:
        import asyncio
        # Wait for the response to send
        await asyncio.sleep(1)

        logging.info("Starting graceful shutdown...")

        await _cleanup_bot()

        # Wait for everything to settle
        await asyncio.sleep(1)

        # Exit gracefully
        logging.info("Exiting...")
        sys.exit(0)

    except Exception as e:
        logging.error(f"Error during shutdown: {e}")
        # Force exit if cleanup fails
        sys.exit(1)


async def _cleanup_bot():
    """Perform bot cleanup operations."""
    from database_modules.database import flush_message_batches
    from database_modules.database_pool import get_multi_guild_pool, close_all_pools
    import asyncio

    # Cancel the Hypercorn server task
    if state.bot_instance and hasattr(state.bot_instance, 'hypercorn_task'):
        state.bot_instance.hypercorn_task.cancel()
        try:
            await state.bot_instance.hypercorn_task
        except asyncio.CancelledError:
            pass
        logging.info("Dashboard server stopped")

    # Stop historical fetcher if it exists
    if state.bot_instance and hasattr(state.bot_instance, 'historical_fetcher') and state.bot_instance.historical_fetcher:
        await state.bot_instance.historical_fetcher.stop()
        logging.info("Historical fetcher stopped")

    # Flush any pending database writes
    await flush_message_batches()
    logging.info("Message batches flushed")

    # Close all database pools
    await close_all_pools()
    logging.info("Database pools closed")

    # Close multi-guild pools
    multi_pool = await get_multi_guild_pool()
    await multi_pool.close_all()
    logging.info("Multi-guild pools closed")

    # Close the bot connection
    if state.bot_instance:
        await state.bot_instance.close()
        logging.info("Bot connection closed")


@system_bp.route("/api/bot/config/<guild_id>", methods=["GET"])
async def api_get_bot_config(guild_id):
    """Get bot configuration for a specific guild."""
    try:
        from database_modules.database_utils import get_guild_settings

        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return jsonify({"error": "Invalid guild_id"}), 400

        settings = await get_guild_settings(str(validated_guild_id))

        if not settings:
            return jsonify({"error": "Guild not found"}), 404

        current_nickname = None
        if state.bot_instance and state.bot_instance.is_ready():
            try:
                guild = state.bot_instance.get_guild(validated_guild_id)
                if guild and guild.me:
                    current_nickname = guild.me.nick
            except Exception as e:
                logging.error(f"Error getting nickname: {e}")

        return jsonify({
            "guild_id": str(validated_guild_id),
            "guild_name": settings.get("guild_name", ""),
            "bot_name": settings.get("bot_name", "drongo"),
            "current_nickname": current_nickname
        })
    except Exception as e:
        logging.error(f"Error getting bot config: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/bot/config/<guild_id>", methods=["POST"])
async def api_update_bot_config(guild_id):
    """Update bot configuration for a specific guild."""
    try:
        from database_modules.database_utils import update_guild_bot_name

        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return jsonify({"error": "Invalid guild_id"}), 400

        data = await request.get_json()
        bot_name = data.get("bot_name", "").strip().lower()

        if not bot_name:
            return jsonify({"error": "bot_name is required"}), 400

        if len(bot_name) > 32:
            return jsonify({"error": "bot_name must be 32 characters or less"}), 400

        await update_guild_bot_name(str(validated_guild_id), bot_name)

        if state.bot_instance and hasattr(state.bot_instance, "ai_handler"):
            state.bot_instance.ai_handler.clear_bot_name_cache(str(validated_guild_id))

        return jsonify({
            "success": True,
            "message": "Bot configuration updated",
            "bot_name": bot_name
        })
    except Exception as e:
        logging.error(f"Error updating bot config: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/api/bot/nickname/<guild_id>", methods=["POST"])
async def api_update_bot_nickname(guild_id):
    """Update bot nickname for a specific guild."""
    try:
        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return jsonify({"error": "Invalid guild_id"}), 400

        data = await request.get_json()
        nickname = data.get("nickname", "").strip()

        if len(nickname) > 32:
            return jsonify({"error": "nickname must be 32 characters or less"}), 400

        if not state.bot_instance or not state.bot_instance.is_ready():
            return jsonify({"error": "Bot is not ready"}), 503

        guild = state.bot_instance.get_guild(validated_guild_id)
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        await guild.me.edit(nick=nickname if nickname else None)

        return jsonify({
            "success": True,
            "message": "Nickname updated",
            "nickname": nickname if nickname else None
        })
    except discord.Forbidden:
        return jsonify({"error": "Bot lacks permissions to change nickname"}), 403
    except Exception as e:
        logging.error(f"Error updating nickname: {e}")
        return jsonify({"error": str(e)}), 500
