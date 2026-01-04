#!/usr/bin/env python3
"""
Modern real-time dashboard server for Drongo bot.
Replaces the Rich terminal interface with a web-based dashboard.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Set
from quart import Quart, render_template, jsonify, websocket, request
from quart_cors import cors
from collections import deque
import discord

def validate_guild_id(guild_id):
    """Validate guild_id for dashboard operations."""
    if guild_id is None:
        return None
    
    if isinstance(guild_id, int):
        return guild_id
    
    if isinstance(guild_id, str):
        # Handle test guild IDs
        if guild_id.startswith('test_guild_'):
            logging.warning(f"Test guild ID detected in dashboard: {guild_id}. Rejecting request.")
            return None
        
        try:
            return int(guild_id)
        except ValueError:
            logging.error(f"Invalid guild_id in dashboard request: '{guild_id}'")
            return None
    
    return None

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, get_leveling_db_connection
from modules.leveling_system import get_leveling_system

# Bot instance for Discord API access
bot_instance = None
name_cache = {}  # Cache for resolved names
cache_expiry = {}  # Cache expiry times
CACHE_DURATION = 300  # 5 minutes

def set_bot_instance(bot):
    """Set the bot instance for Discord API access."""
    global bot_instance, name_cache, cache_expiry
    bot_instance = bot
    # Clear cached fallbacks so we can resolve fresh names now that the bot is ready
    name_cache.clear()
    cache_expiry.clear()

async def resolve_user_name(user_id: str) -> str:
    """Resolve user ID to display name with caching."""
    global name_cache, cache_expiry
    
    # Check cache first
    cache_key = f"user_{user_id}"
    current_time = time.time()
    
    if cache_key in name_cache and cache_key in cache_expiry:
        if current_time < cache_expiry[cache_key]:
            return name_cache[cache_key]
    
    # Try to resolve using Discord API
    if not bot_instance:
        logging.debug("Bot instance not available for user name resolution")
        return f"User ({user_id})"
    
    try:
        # Validate user_id first
        try:
            validated_user_id = int(user_id)
        except ValueError:
            logging.warning(f"Invalid user_id in dashboard request: '{user_id}'")
            return "Invalid User ID"
        
        # First try cache, then fetch from API if needed
        user = bot_instance.get_user(validated_user_id)
        if not user:
            # Try to fetch from Discord API if not in cache
            try:
                user = await bot_instance.fetch_user(validated_user_id)
            except discord.NotFound:
                logging.debug(f"User {user_id} not found on Discord")
            except discord.HTTPException as e:
                logging.debug(f"HTTP error fetching user {user_id}: {e}")
        
        if user:
            display_name = user.display_name
            name_cache[cache_key] = display_name
            cache_expiry[cache_key] = current_time + CACHE_DURATION
            logging.debug(f"Resolved user {user_id} to {display_name} via Discord API")
            return display_name
        else:
            logging.debug(f"User {user_id} not found in Discord")
    except Exception as e:
        logging.error(f"Error resolving user name via Discord API: {e}")
    
    # Final fallback - show full ID with short cache so we retry soon
    fallback_name = f"User ({user_id})"
    name_cache[cache_key] = fallback_name
    cache_expiry[cache_key] = current_time + 30  # retry relatively soon
    logging.debug(f"Using fallback name for user {user_id}: {fallback_name}")
    return fallback_name

async def resolve_guild_name(guild_id: str) -> str:
    """Resolve guild ID to guild name with caching."""
    global name_cache, cache_expiry
    
    # Check cache first
    cache_key = f"guild_{guild_id}"
    current_time = time.time()
    
    if cache_key in name_cache and cache_key in cache_expiry:
        if current_time < cache_expiry[cache_key]:
            return name_cache[cache_key]
    
    # Try to resolve using Discord API
    if not bot_instance:
        logging.debug("Bot instance not available for guild name resolution")
        return f"Guild ({guild_id})"
    
    try:
        # Validate guild_id first
        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return "Invalid Guild ID"
        
        # First try cache, then fetch from API if needed
        guild = bot_instance.get_guild(validated_guild_id)
        if not guild:
            # Try to fetch from Discord API if not in cache
            try:
                guild = await bot_instance.fetch_guild(validated_guild_id)
            except discord.NotFound:
                logging.debug(f"Guild {guild_id} not found on Discord")
            except discord.HTTPException as e:
                logging.debug(f"HTTP error fetching guild {guild_id}: {e}")
        
        if guild:
            display_name = guild.name
            name_cache[cache_key] = display_name
            cache_expiry[cache_key] = current_time + CACHE_DURATION
            logging.debug(f"Resolved guild {guild_id} to {display_name} via Discord API")
            return display_name
        else:
            logging.debug(f"Guild {guild_id} not found in Discord")
    except Exception as e:
        logging.error(f"Error resolving guild name via Discord API: {e}")
    
    # Final fallback - show full ID with short cache
    fallback_name = f"Guild ({guild_id})"
    name_cache[cache_key] = fallback_name
    cache_expiry[cache_key] = current_time + 30
    logging.debug(f"Using fallback name for guild {guild_id}: {fallback_name}")
    return fallback_name

async def bulk_resolve_names(user_ids: List[str] = None, guild_ids: List[str] = None) -> Dict[str, str]:
    """Bulk resolve multiple user and guild names."""
    resolved_names = {}
    
    if user_ids:
        for user_id in user_ids:
            resolved_names[f"user_{user_id}"] = await resolve_user_name(user_id)
    
    if guild_ids:
        for guild_id in guild_ids:
            resolved_names[f"guild_{guild_id}"] = await resolve_guild_name(guild_id)
    
    return resolved_names

app = Quart(__name__)
app = cors(app)

# Store connected WebSocket clients
connected_clients: Set = set()

# Store real-time stats data
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
        self.message_rate_history = deque(maxlen=60)  # Last 60 seconds
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
        
        # Add current counts to rate history
        self.message_rate_history.append({
            "time": current_time,
            "count": self.stats["messages_processed"]
        })
        
        self.command_rate_history.append({
            "time": current_time,
            "count": self.stats["commands_executed"]
        })
        
        # Remove old entries (older than 60 seconds)
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
            return (count_diff / time_diff) * 60  # Per minute
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
            return (count_diff / time_diff) * 60  # Per minute
        return 0.0

# Global stats instance
real_time_stats = RealTimeStats()

# Flag to trigger immediate broadcast
_needs_immediate_broadcast = False

async def get_enhanced_stats():
    """Get comprehensive stats for the dashboard."""
    try:
        # Get database stats
        conn = await get_db_connection()
        
        # Basic message stats
        async with conn.execute('SELECT COUNT(*) FROM messages') as cursor:
            total_messages = (await cursor.fetchone())[0]
        
        async with conn.execute('SELECT COUNT(DISTINCT user_id) FROM messages') as cursor:
            unique_users = (await cursor.fetchone())[0]
        
        # Recent activity (last hour)
        async with conn.execute('''
            SELECT COUNT(*) FROM messages
            WHERE datetime(timestamp) > datetime('now', '-1 hour')
        ''') as cursor:
            recent_activity = (await cursor.fetchone())[0]
        
        # Get database health info manually since optimized_db might not be available
        try:
            health_info = await get_database_health(conn)
        except Exception as e:
            logging.error(f"Error getting database health: {e}")
            health_info = {
                "database_size_mb": 0,
                "table_count": 0,
                "index_count": 0
            }
        
        await conn.close()
        
        # Update real-time stats
        real_time_stats.update_stat("messages_processed", total_messages)
        real_time_stats.update_stat("active_users", unique_users)
        real_time_stats.update_stat("database_size", health_info["database_size_mb"])
        real_time_stats.update_uptime()
        real_time_stats.update_rates()
        
        # Compile comprehensive stats
        stats = {
            **real_time_stats.stats,
            "recent_activity": recent_activity,
            "message_rate": round(real_time_stats.get_message_rate(), 1),
            "command_rate": round(real_time_stats.get_command_rate(), 1),
            "recent_messages": list(real_time_stats.recent_messages),
            "recent_events": list(real_time_stats.recent_events),
            "database_health": health_info,
            "last_updated": datetime.now().isoformat()
        }
        
        return stats
        
    except Exception as e:
        logging.error(f"Error getting enhanced stats: {e}")
        return {
            "error": str(e),
            "last_updated": datetime.now().isoformat()
        }

async def get_database_health(conn):
    """Get database health information."""
    try:
        # Get database file size
        import os
        db_file = "database/chat_history.db"  # Fixed database path
        try:
            db_size_bytes = os.path.getsize(db_file)
            db_size_mb = db_size_bytes / (1024 * 1024)
        except FileNotFoundError:
            db_size_mb = 0
        
        # Count tables
        async with conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'") as cursor:
            table_count = (await cursor.fetchone())[0]
        
        # Count indexes
        async with conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'") as cursor:
            index_count = (await cursor.fetchone())[0]
        
        return {
            "database_size_mb": round(db_size_mb, 2),
            "table_count": table_count,
            "index_count": index_count
        }
        
    except Exception as e:
        logging.error(f"Error getting database health: {e}")
        return {
            "database_size_mb": 0,
            "table_count": 0,
            "index_count": 0
        }

async def broadcast_stats():
    """Broadcast current stats to all connected WebSocket clients."""
    if not connected_clients:
        return
        
    stats = await get_enhanced_stats()
    
    message = json.dumps({
        "type": "stats_update",
        "data": stats
    })
    
    # Send to all connected clients
    disconnected_clients = set()
    for client in connected_clients.copy():  # Use copy to avoid modification during iteration
        try:
            await client.send(message)
        except Exception as e:
            logging.debug(f"Client disconnected during broadcast: {e}")
            disconnected_clients.add(client)
    
    # Remove disconnected clients
    connected_clients.difference_update(disconnected_clients)

@app.websocket('/ws')
async def websocket_endpoint():
    """WebSocket endpoint for real-time updates."""
    ws = websocket._get_current_object()
    connected_clients.add(ws)
    
    try:
        # Send initial stats
        stats = await get_enhanced_stats()
        await ws.send(json.dumps({
            "type": "stats_update",
            "data": stats
        }))
        
        # Keep connection alive and handle client messages
        while True:
            try:
                message = await ws.receive()
                if isinstance(message, str):
                    try:
                        data = json.loads(message)
                        
                        # Handle different message types
                        if data.get("type") == "ping":
                            await ws.send(json.dumps({"type": "pong"}))
                        elif data.get("type") == "request_stats":
                            stats = await get_enhanced_stats()
                            await ws.send(json.dumps({
                                "type": "stats_update",
                                "data": stats
                            }))
                            
                    except json.JSONDecodeError:
                        await ws.send(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON"
                        }))
                    except Exception as e:
                        logging.error(f"WebSocket message error: {e}")
                        
            except Exception as e:
                # Handle connection closed or other errors
                logging.debug(f"WebSocket connection ended: {e}")
                break
                
    except Exception as e:
        logging.debug(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(ws)

@app.route('/')
async def dashboard():
    """Main dashboard route."""
    return await render_template('dashboard/dashboard.html')

@app.route('/dashboard/leveling')
async def leveling_dashboard():
    """Leveling dashboard route."""
    return await render_template('dashboard/leveling/leveling.html')

@app.route('/api/stats')
async def api_stats():
    """REST API endpoint for stats."""
    return jsonify(await get_enhanced_stats())

@app.route('/api/system_info')
async def system_info():
    """Get system information."""
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return jsonify({
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_total": memory.total // (1024**3),  # GB
            "memory_used": memory.used // (1024**3),    # GB
            "disk_usage": disk.percent,
            "disk_total": disk.total // (1024**3),      # GB
            "disk_used": disk.used // (1024**3)         # GB
        })
    except ImportError:
        return jsonify({
            "error": "psutil not available",
            "cpu_usage": 0,
            "memory_usage": 0
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/commands/list')
async def api_commands_list():
    """Get list of available commands from register_commands.py."""
    try:
        from utilities.register_commands import get_commands
        commands = get_commands()
        
        return jsonify(commands)
    except Exception as e:
        logging.error(f"Error loading commands: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/commands/register', methods=['POST'])
async def api_commands_register():
    """Register Discord commands."""
    try:
        from utilities.register_commands import register_commands
        
        # Run the async function
        await register_commands()
        
        return jsonify({"success": True, "message": "Commands registered successfully"})
    except Exception as e:
        logging.error(f"Error registering commands: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/commands/delete', methods=['POST'])
async def api_commands_delete():
    """Delete all Discord commands."""
    try:
        from utilities.delete_commands import delete_all_commands
        
        # Run the async function
        await delete_all_commands()
        
        return jsonify({"success": True, "message": "Commands deleted successfully"})
    except Exception as e:
        logging.error(f"Error deleting commands: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/bot/restart', methods=['POST'])
async def api_bot_restart():
    """Restart the bot."""
    try:
        import os
        import sys
        import subprocess
        
        # Log the restart event
        real_time_stats.add_event_log("Bot restart requested via dashboard", "system")
        
        # Broadcast the restart event
        await broadcast_stats()
        
        # Use subprocess to restart the bot properly
        def restart_bot():
            import threading
            import time
            time.sleep(1)  # Give time for response to be sent
            
            # Get the current script path and arguments
            script_path = sys.argv[0]
            python_executable = sys.executable
            
            # Start new process and exit current one
            subprocess.Popen([python_executable] + sys.argv)
            os._exit(0)  # Exit current process cleanly
        
        # Start restart in background thread to allow response to be sent
        import threading
        restart_thread = threading.Thread(target=restart_bot)
        restart_thread.daemon = True
        restart_thread.start()
        
        return jsonify({"success": True, "message": "Bot restart initiated"})
    except Exception as e:
        logging.error(f"Error restarting bot: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/bot/shutdown', methods=['POST'])
async def api_bot_shutdown():
    """Shutdown the bot."""
    try:
        import os
        import sys
        
        # Log the shutdown event
        real_time_stats.add_event_log("Bot shutdown requested via dashboard", "system")
        
        # Broadcast the shutdown event
        await broadcast_stats()
        
        # Use os._exit to force shutdown
        def shutdown_bot():
            import threading
            import time
            time.sleep(1)  # Give time for response to be sent
            os._exit(0)  # Clean exit
        
        # Start shutdown in background thread to allow response to be sent
        import threading
        shutdown_thread = threading.Thread(target=shutdown_bot)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        return jsonify({"success": True, "message": "Bot shutdown initiated"})
    except Exception as e:
        logging.error(f"Error shutting down bot: {e}")
        return jsonify({"error": str(e)}), 500

# =========================================================================
# LEVELING SYSTEM API ROUTES
# =========================================================================

@app.route('/api/leveling/live-feed')
async def api_leveling_live_feed():
    """Get live XP award feed with resolved names."""
    try:
        guild_id = request.args.get('guild_id')
        limit = int(request.args.get('limit', 50))
        
        conn = await get_leveling_db_connection()
        
        # Build query with optional guild filter
        if guild_id:
            query = '''
                SELECT xt.user_id, xt.guild_id, xt.channel_id, xt.xp_awarded,
                       xt.message_length, xt.word_count, xt.char_count, xt.timestamp,
                       xt.daily_cap_applied
                FROM xp_transactions xt
                WHERE xt.guild_id = ?
                ORDER BY xt.timestamp DESC
                LIMIT ?
            '''
            params = (guild_id, limit)
        else:
            query = '''
                SELECT xt.user_id, xt.guild_id, xt.channel_id, xt.xp_awarded,
                       xt.message_length, xt.word_count, xt.char_count, xt.timestamp,
                       xt.daily_cap_applied
                FROM xp_transactions xt
                ORDER BY xt.timestamp DESC
                LIMIT ?
            '''
            params = (limit,)
        
        async with conn.execute(query, params) as cursor:
            transactions = await cursor.fetchall()
        
        await conn.close()
        
        # Extract unique user and guild IDs for bulk resolution
        user_ids = set()
        guild_ids = set()
        
        for tx in transactions:
            user_ids.add(tx[0])
            guild_ids.add(tx[1])
        
        # Bulk resolve names
        resolved_names = await bulk_resolve_names(list(user_ids), list(guild_ids))
        
        feed_data = []
        for tx in transactions:
            feed_data.append({
                'user_id': tx[0],
                'user_name': resolved_names.get(f"user_{tx[0]}", f"Unknown User ({tx[0][-4:]})"),
                'guild_id': tx[1],
                'guild_name': resolved_names.get(f"guild_{tx[1]}", f"Unknown Guild ({tx[1][-4:]})"),
                'channel_id': tx[2],
                'xp_awarded': tx[3],
                'message_length': tx[4],
                'word_count': tx[5],
                'char_count': tx[6],
                'timestamp': tx[7],
                'daily_cap_applied': bool(tx[8]) if tx[8] is not None else False
            })
        
        return jsonify(feed_data)
        
    except Exception as e:
        logging.error(f"Error getting live feed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/leaderboard')
async def api_leveling_leaderboard():
    """Get leaderboard data with resolved names."""
    try:
        guild_id = request.args.get('guild_id')
        limit = int(request.args.get('limit', 25))
        
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        # Mock bot instance for leveling system
        class MockBot:
            pass
            
        leveling = get_leveling_system(MockBot())
        leaderboard = await leveling.get_leaderboard(guild_id, limit)
        
        # Extract user IDs for name resolution
        user_ids = [entry['user_id'] for entry in leaderboard]
        resolved_names = await bulk_resolve_names(user_ids, [guild_id])
        
        # Add resolved names to leaderboard entries
        for entry in leaderboard:
            entry['user_name'] = resolved_names.get(f"user_{entry['user_id']}", f"Unknown User ({entry['user_id'][-4:]})")
            entry['guild_name'] = resolved_names.get(f"guild_{guild_id}", f"Unknown Guild ({guild_id[-4:]})")
        
        return jsonify(leaderboard)
        
    except Exception as e:
        logging.error(f"Error getting leaderboard: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/user-stats')
async def api_leveling_user_stats():
    """Get user statistics with resolved names."""
    try:
        user_id = request.args.get('user_id')
        guild_id = request.args.get('guild_id')
        
        if not user_id or not guild_id:
            return jsonify({"error": "user_id and guild_id parameters required"}), 400
            
        # Mock bot instance for leveling system
        class MockBot:
            pass
            
        leveling = get_leveling_system(MockBot())
        user_data = await leveling.get_user_level_data(user_id, guild_id)
        rank_data = await leveling.get_user_rank(user_id, guild_id)
        range_data = await leveling.get_user_range(user_id, guild_id)
        
        if user_data:
            # Resolve names
            resolved_names = await bulk_resolve_names([user_id], [guild_id])
            
            stats = {
                **user_data,
                'user_name': resolved_names.get(f"user_{user_id}", f"Unknown User ({user_id[-4:]})"),
                'guild_name': resolved_names.get(f"guild_{guild_id}", f"Unknown Guild ({guild_id[-4:]})"),
                'rank_info': rank_data or {},
                'range_info': range_data or None
            }
            return jsonify(stats)
        else:
            return jsonify({"error": "User not found"}), 404
            
    except Exception as e:
        logging.error(f"Error getting user stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/config', methods=['GET'])
async def api_leveling_config_get():
    """Get leveling configuration with proper database values."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Get configuration directly from database to ensure current values
        async with conn.execute('''
            SELECT enabled, base_xp, max_xp, word_multiplier, char_multiplier,
                   min_cooldown_seconds, max_cooldown_seconds, min_message_chars,
                   min_message_words, daily_xp_cap, blacklisted_channels,
                   whitelisted_channels, level_up_announcements, announcement_channel_id,
                   dm_level_notifications
            FROM leveling_config
            WHERE guild_id = ?
        ''', (guild_id,)) as cursor:
            result = await cursor.fetchone()
        
        await conn.close()
        
        if result:
            config = {
                'guild_id': guild_id,
                'enabled': bool(result[0]) if result[0] is not None else True,
                'base_xp': result[1] if result[1] is not None else 5,
                'max_xp': result[2] if result[2] is not None else 25,
                'word_multiplier': result[3] if result[3] is not None else 0.5,
                'char_multiplier': result[4] if result[4] is not None else 0.1,
                'min_cooldown_seconds': result[5] if result[5] is not None else 30,
                'max_cooldown_seconds': result[6] if result[6] is not None else 60,
                'min_message_chars': result[7] if result[7] is not None else 5,
                'min_message_words': result[8] if result[8] is not None else 2,
                'daily_xp_cap': result[9] if result[9] is not None else 1000,
                'blacklisted_channels': result[10] if result[10] is not None else '[]',
                'whitelisted_channels': result[11] if result[11] is not None else '[]',
                'level_up_announcements': bool(result[12]) if result[12] is not None else True,
                'announcement_channel_id': result[13],
                'dm_level_notifications': bool(result[14]) if result[14] is not None else False
            }
        else:
            # Return default configuration if none exists
            config = {
                'guild_id': guild_id,
                'enabled': True,
                'base_xp': 5,
                'max_xp': 25,
                'word_multiplier': 0.5,
                'char_multiplier': 0.1,
                'min_cooldown_seconds': 30,
                'max_cooldown_seconds': 60,
                'min_message_chars': 5,
                'min_message_words': 2,
                'daily_xp_cap': 1000,
                'blacklisted_channels': '[]',
                'whitelisted_channels': '[]',
                'level_up_announcements': True,
                'announcement_channel_id': None,
                'dm_level_notifications': False
            }
        
        return jsonify(config)
        
    except Exception as e:
        logging.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/config', methods=['POST'])
async def api_leveling_config_update():
    """Update leveling configuration."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        
        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Update configuration
        await conn.execute('''
            UPDATE leveling_config SET
                enabled = ?,
                base_xp = ?,
                max_xp = ?,
                word_multiplier = ?,
                char_multiplier = ?,
                min_cooldown_seconds = ?,
                max_cooldown_seconds = ?,
                min_message_chars = ?,
                min_message_words = ?,
                daily_xp_cap = ?,
                blacklisted_channels = ?,
                whitelisted_channels = ?,
                level_up_announcements = ?,
                announcement_channel_id = ?,
                dm_level_notifications = ?
            WHERE guild_id = ?
        ''', (
            data.get('enabled', True),
            data.get('base_xp', 5),
            data.get('max_xp', 25),
            data.get('word_multiplier', 0.5),
            data.get('char_multiplier', 0.1),
            data.get('min_cooldown_seconds', 30),
            data.get('max_cooldown_seconds', 60),
            data.get('min_message_chars', 5),
            data.get('min_message_words', 2),
            data.get('daily_xp_cap', 1000),
            data.get('blacklisted_channels', '[]'),
            data.get('whitelisted_channels', '[]'),
            data.get('level_up_announcements', True),
            data.get('announcement_channel_id'),
            data.get('dm_level_notifications', False),
            guild_id
        ))
        
        await conn.commit()
        await conn.close()

        # Clear cached configuration so changes apply immediately
        try:
            leveling_instance = None
            if bot_instance:
                leveling_instance = get_leveling_system(bot_instance)
            else:
                import modules.leveling_system as leveling_module  # Local import to avoid circulars at module load
                leveling_instance = getattr(leveling_module, "leveling_system", None)
            if leveling_instance and hasattr(leveling_instance, 'clear_guild_config_cache'):
                leveling_instance.clear_guild_config_cache(str(guild_id))
        except Exception as cache_error:
            logging.error(f"Error clearing leveling config cache for guild {guild_id}: {cache_error}")
        
        return jsonify({"success": True, "message": "Configuration updated successfully"})
        
    except Exception as e:
        logging.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/manual-adjust', methods=['POST'])
async def api_leveling_manual_adjust():
    """Manual XP/level adjustment."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id')
        guild_id = data.get('guild_id')
        adjustment_type = data.get('type')  # 'add_xp', 'remove_xp', 'set_level'
        amount = data.get('amount')
        reason = data.get('reason', 'Manual adjustment')
        
        if not all([user_id, guild_id, adjustment_type, amount is not None]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        conn = await get_leveling_db_connection()
        
        if adjustment_type == 'add_xp':
            await conn.execute('''
                UPDATE user_levels
                SET current_xp = current_xp + ?,
                    total_xp = total_xp + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            ''', (amount, amount, user_id, guild_id))
            
        elif adjustment_type == 'remove_xp':
            await conn.execute('''
                UPDATE user_levels
                SET current_xp = MAX(0, current_xp - ?),
                    total_xp = MAX(0, total_xp - ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            ''', (amount, amount, user_id, guild_id))
            
        elif adjustment_type == 'set_level':
            # Calculate required XP for target level
            class MockBot:
                pass
            leveling = get_leveling_system(MockBot())
            required_xp = leveling.get_xp_required_for_level(amount)
            
            await conn.execute('''
                UPDATE user_levels
                SET current_level = ?,
                    current_xp = 0,
                    total_xp = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            ''', (amount, required_xp, user_id, guild_id))
        
        # Log the adjustment
        await conn.execute('''
            INSERT INTO xp_transactions
            (user_id, guild_id, channel_id, xp_awarded, message_length, word_count, char_count)
            VALUES (?, ?, 'MANUAL', ?, 0, 0, 0)
        ''', (user_id, guild_id, amount if adjustment_type != 'set_level' else 0))
        
        await conn.commit()
        await conn.close()
        
        return jsonify({"success": True, "message": f"Successfully applied {adjustment_type}"})
        
    except Exception as e:
        logging.error(f"Error in manual adjustment: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/ranks', methods=['GET'])
async def api_leveling_ranks_get():
    """Get guild rank titles with enhanced data."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Get ranks with additional statistics
        async with conn.execute('''
            SELECT rt.id, rt.min_level, rt.max_level, rt.title, rt.description,
                   rt.color_hex, rt.emoji, rt.role_id, rt.created_at,
                   COUNT(ul.user_id) as user_count
            FROM rank_titles rt
            LEFT JOIN user_levels ul ON ul.guild_id = rt.guild_id
                AND ul.current_level >= rt.min_level
                AND (rt.max_level IS NULL OR ul.current_level <= rt.max_level)
            WHERE rt.guild_id = ?
            GROUP BY rt.id
            ORDER BY rt.min_level ASC
        ''', (guild_id,)) as cursor:
            ranks = await cursor.fetchall()
        
        await conn.close()
        
        rank_list = []
        for rank in ranks:
            rank_list.append({
                'id': rank[0],
                'level_min': rank[1],
                'level_max': rank[2],
                'name': rank[3],
                'description': rank[4],
                'color': rank[5],
                'emoji': rank[6],
                'discord_role_id': rank[7],
                'created_at': rank[8],
                'user_count': rank[9] or 0
            })
        
        return jsonify(rank_list)
        
    except Exception as e:
        logging.error(f"Error getting ranks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/ranks', methods=['POST'])
async def api_leveling_ranks_create():
    """Create a new rank title with validation."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        min_level = data.get('level_min')
        max_level = data.get('level_max')
        title = data.get('name')
        
        if not all([guild_id, min_level is not None, title]):
            return jsonify({"error": "guild_id, min_level, and title are required"}), 400
            
        # Validate level range
        if min_level < 0:
            return jsonify({"error": "min_level must be non-negative"}), 400
            
        if max_level is not None and max_level < min_level:
            return jsonify({"error": "max_level must be greater than or equal to min_level"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Check for overlapping ranges
        overlap_query = '''
            SELECT id, title FROM rank_titles
            WHERE guild_id = ? AND (
                (min_level <= ? AND (max_level IS NULL OR max_level >= ?)) OR
                (? IS NOT NULL AND min_level <= ? AND (max_level IS NULL OR max_level >= ?))
            )
        '''
        async with conn.execute(overlap_query, (
            guild_id, min_level, min_level,
            max_level, max_level, max_level
        )) as cursor:
            overlapping = await cursor.fetchone()
            
        if overlapping:
            await conn.close()
            return jsonify({
                "error": f"Level range conflicts with existing rank '{overlapping[1]}'"
            }), 400
        
        # Create the rank
        await conn.execute('''
            INSERT INTO rank_titles
            (guild_id, min_level, max_level, title, description, color_hex, emoji, role_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            guild_id, min_level, max_level, title,
            data.get('description'), data.get('color_hex', '#7289DA'),
            data.get('emoji'), data.get('role_id')
        ))
        
        await conn.commit()
        
        # Get the created rank ID
        async with conn.execute('SELECT last_insert_rowid()') as cursor:
            rank_id = (await cursor.fetchone())[0]
            
        await conn.close()
        
        return jsonify({
            "success": True,
            "rank_id": rank_id,
            "message": f"Rank '{title}' created successfully"
        })
        
    except Exception as e:
        logging.error(f"Error creating rank: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/ranks/<int:rank_id>', methods=['PUT'])
async def api_leveling_ranks_update(rank_id):
    """Update a rank title with validation."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        
        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Verify rank exists and belongs to guild
        async with conn.execute(
            'SELECT id, title FROM rank_titles WHERE id = ? AND guild_id = ?',
            (rank_id, guild_id)
        ) as cursor:
            existing_rank = await cursor.fetchone()
            
        if not existing_rank:
            await conn.close()
            return jsonify({"error": "Rank not found or access denied"}), 404
        
        # Validate level range if being updated
        min_level = data.get('min_level')
        max_level = data.get('max_level')
        
        if min_level is not None and min_level < 0:
            await conn.close()
            return jsonify({"error": "min_level must be non-negative"}), 400
            
        if max_level is not None and min_level is not None and max_level < min_level:
            await conn.close()
            return jsonify({"error": "max_level must be greater than or equal to min_level"}), 400
        
        # Build update query
        valid_fields = ['min_level', 'max_level', 'title', 'description', 'color_hex', 'emoji', 'role_id']
        update_fields = []
        update_values = []
        
        for field in valid_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        if not update_fields:
            await conn.close()
            return jsonify({"error": "No valid fields to update"}), 400
        
        update_values.extend([rank_id, guild_id])
        
        await conn.execute(f'''
            UPDATE rank_titles
            SET {', '.join(update_fields)}
            WHERE id = ? AND guild_id = ?
        ''', update_values)
        
        await conn.commit()
        await conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Rank updated successfully"
        })
        
    except Exception as e:
        logging.error(f"Error updating rank: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/ranks/<int:rank_id>', methods=['DELETE'])
async def api_leveling_ranks_delete(rank_id):
    """Delete a rank title."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Verify rank exists and belongs to guild
        async with conn.execute(
            'SELECT title FROM rank_titles WHERE id = ? AND guild_id = ?',
            (rank_id, guild_id)
        ) as cursor:
            existing_rank = await cursor.fetchone()
            
        if not existing_rank:
            await conn.close()
            return jsonify({"error": "Rank not found or access denied"}), 404
        
        await conn.execute(
            'DELETE FROM rank_titles WHERE id = ? AND guild_id = ?',
            (rank_id, guild_id)
        )
        
        await conn.commit()
        await conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Rank '{existing_rank[0]}' deleted successfully"
        })
        
    except Exception as e:
        logging.error(f"Error deleting rank: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/rewards', methods=['GET'])
async def api_leveling_rewards_get():
    """Get guild level rewards."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        # Mock bot instance for leveling system
        class MockBot:
            pass
            
        leveling = get_leveling_system(MockBot())
        rewards = await leveling.get_guild_rewards(guild_id)
        
        return jsonify(rewards)
        
    except Exception as e:
        logging.error(f"Error getting rewards: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/rewards', methods=['POST'])
async def api_leveling_rewards_create():
    """Create a new level reward."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        
        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400
            
        # Mock bot instance for leveling system
        class MockBot:
            pass
            
        leveling = get_leveling_system(MockBot())
        result = await leveling.create_level_reward(
            guild_id=guild_id,
            level=data.get('level'),
            reward_type=data.get('reward_type'),
            reward_data=data.get('reward_data', {}),
            is_milestone=data.get('is_milestone', False),
            milestone_interval=data.get('milestone_interval')
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error creating reward: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/rewards/<int:reward_id>', methods=['PUT'])
async def api_leveling_rewards_update(reward_id):
    """Update a level reward."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        
        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400
            
        # Mock bot instance for leveling system
        class MockBot:
            pass
            
        leveling = get_leveling_system(MockBot())
        result = await leveling.update_level_reward(guild_id, reward_id, **data)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error updating reward: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/rewards/<int:reward_id>', methods=['DELETE'])
async def api_leveling_rewards_delete(reward_id):
    """Delete a level reward."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        # Mock bot instance for leveling system
        class MockBot:
            pass
            
        leveling = get_leveling_system(MockBot())
        result = await leveling.delete_level_reward(guild_id, reward_id)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error deleting reward: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/guilds')
async def api_leveling_guilds():
    """Get available guilds for leveling dashboard with resolved names."""
    try:
        conn = await get_leveling_db_connection()
        
        # Get guilds that have leveling data
        async with conn.execute('''
            SELECT DISTINCT guild_id, COUNT(*) as user_count
            FROM user_levels
            GROUP BY guild_id
            ORDER BY user_count DESC
        ''') as cursor:
            guild_data = await cursor.fetchall()
        
        await conn.close()
        
        # Extract guild IDs for bulk resolution
        guild_ids = [guild[0] for guild in guild_data]
        resolved_names = await bulk_resolve_names(None, guild_ids)
        
        guilds = []
        for guild in guild_data:
            guild_id = guild[0]
            guild_name = resolved_names.get(f"guild_{guild_id}", f"Unknown Guild ({guild_id[-4:]})")
            
            guilds.append({
                'id': guild_id,
                'name': guild_name,
                'user_count': guild[1]
            })
        
        return jsonify(guilds)
        
    except Exception as e:
        logging.error(f"Error getting guilds: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/stats')
async def api_leveling_stats():
    """Get leveling system statistics."""
    try:
        guild_id = request.args.get('guild_id')
        
        conn = await get_leveling_db_connection()
        
        if guild_id:
            # Guild-specific stats
            async with conn.execute('''
                SELECT
                    COUNT(*) as total_users,
                    AVG(current_level) as avg_level,
                    SUM(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN daily_xp_earned ELSE 0 END) as xp_today,
                    COUNT(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN 1 END) as active_today
                FROM user_levels
                WHERE guild_id = ?
            ''', (guild_id,)) as cursor:
                result = await cursor.fetchone()
        else:
            # Global stats
            async with conn.execute('''
                SELECT
                    COUNT(*) as total_users,
                    AVG(current_level) as avg_level,
                    SUM(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN daily_xp_earned ELSE 0 END) as xp_today,
                    COUNT(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN 1 END) as active_today
                FROM user_levels
            ''') as cursor:
                result = await cursor.fetchone()
        
        await conn.close()
        
        if result:
            return jsonify({
                'total_users': result[0] or 0,
                'avg_level': round(result[1] or 0, 1),
                'xp_today': result[2] or 0,
                'active_users_today': result[3] or 0
            })
        else:
            return jsonify({
                'total_users': 0,
                'avg_level': 0,
                'xp_today': 0,
                'active_users_today': 0
            })
        
    except Exception as e:
        logging.error(f"Error getting leveling stats: {e}")
        return jsonify({"error": str(e)}), 500

# =========================================================================
# MESSAGE TEMPLATES API ROUTES
# =========================================================================

@app.route('/api/leveling/message-templates', methods=['GET'])
async def api_message_templates_get():
    """Get guild message templates."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Get templates for the guild
        async with conn.execute('''
            SELECT id, template_type, template_name, message_content, embed_enabled,
                   embed_config, milestone_interval, min_level, max_level, enabled,
                   send_to_channel, send_as_dm, mention_user, priority, created_at, updated_at
            FROM level_up_message_templates
            WHERE guild_id = ?
            ORDER BY template_type, priority DESC, template_name
        ''', (guild_id,)) as cursor:
            templates = await cursor.fetchall()
        
        await conn.close()
        
        template_list = []
        for template in templates:
            template_list.append({
                'id': template[0],
                'template_type': template[1],
                'template_name': template[2],
                'message_content': template[3],
                'embed_enabled': bool(template[4]),
                'embed_config': json.loads(template[5]) if template[5] else {},
                'milestone_interval': template[6],
                'min_level': template[7],
                'max_level': template[8],
                'enabled': bool(template[9]),
                'send_to_channel': bool(template[10]),
                'send_as_dm': bool(template[11]),
                'mention_user': bool(template[12]),
                'priority': template[13],
                'created_at': template[14],
                'updated_at': template[15]
            })
        
        return jsonify(template_list)
        
    except Exception as e:
        logging.error(f"Error getting message templates: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/message-templates', methods=['POST'])
async def api_message_templates_create():
    """Create a new message template."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        template_type = data.get('template_type')
        template_name = data.get('template_name')
        message_content = data.get('message_content')
        
        if not all([guild_id, template_type, template_name, message_content]):
            return jsonify({"error": "guild_id, template_type, template_name, and message_content are required"}), 400
        
        # Validate template type
        valid_types = ['default_levelup', 'rank_promotion', 'milestone_level', 'first_level', 'major_milestone']
        if template_type not in valid_types:
            return jsonify({"error": f"Invalid template_type. Must be one of: {', '.join(valid_types)}"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Check for duplicate template name within guild and type
        async with conn.execute(
            'SELECT id FROM level_up_message_templates WHERE guild_id = ? AND template_type = ? AND template_name = ?',
            (guild_id, template_type, template_name)
        ) as cursor:
            existing = await cursor.fetchone()
            
        if existing:
            await conn.close()
            return jsonify({"error": f"Template '{template_name}' already exists for {template_type}"}), 400
        
        # Create the template
        await conn.execute('''
            INSERT INTO level_up_message_templates
            (guild_id, template_type, template_name, message_content, embed_enabled, embed_config,
             milestone_interval, min_level, max_level, enabled, send_to_channel, send_as_dm,
             mention_user, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            guild_id, template_type, template_name, message_content,
            data.get('embed_enabled', False),
            json.dumps(data.get('embed_config', {})),
            data.get('milestone_interval'),
            data.get('min_level'),
            data.get('max_level'),
            data.get('enabled', True),
            data.get('send_to_channel', True),
            data.get('send_as_dm', False),
            data.get('mention_user', True),
            data.get('priority', 0)
        ))
        
        await conn.commit()
        
        # Get the created template ID
        async with conn.execute('SELECT last_insert_rowid()') as cursor:
            template_id = (await cursor.fetchone())[0]
            
        await conn.close()
        
        return jsonify({
            "success": True,
            "template_id": template_id,
            "message": f"Template '{template_name}' created successfully"
        })
        
    except Exception as e:
        logging.error(f"Error creating message template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/message-templates/<int:template_id>', methods=['PUT'])
async def api_message_templates_update(template_id):
    """Update a message template."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        
        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Verify template exists and belongs to guild
        async with conn.execute(
            'SELECT id, template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?',
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()
            
        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404
        
        # Build update query
        valid_fields = [
            'template_type', 'template_name', 'message_content', 'embed_enabled', 'embed_config',
            'milestone_interval', 'min_level', 'max_level', 'enabled', 'send_to_channel',
            'send_as_dm', 'mention_user', 'priority'
        ]
        update_fields = []
        update_values = []
        
        for field in valid_fields:
            if field in data:
                if field == 'embed_config':
                    update_fields.append(f"{field} = ?")
                    update_values.append(json.dumps(data[field]) if data[field] else '{}')
                else:
                    update_fields.append(f"{field} = ?")
                    update_values.append(data[field])
        
        if not update_fields:
            await conn.close()
            return jsonify({"error": "No valid fields to update"}), 400
        
        update_values.extend([template_id, guild_id])
        
        await conn.execute(f'''
            UPDATE level_up_message_templates
            SET {', '.join(update_fields)}
            WHERE id = ? AND guild_id = ?
        ''', update_values)
        
        await conn.commit()
        await conn.close()
        
        return jsonify({
            "success": True,
            "message": "Template updated successfully"
        })
        
    except Exception as e:
        logging.error(f"Error updating message template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/message-templates/<int:template_id>', methods=['DELETE'])
async def api_message_templates_delete(template_id):
    """Delete a message template."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Verify template exists and belongs to guild
        async with conn.execute(
            'SELECT template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?',
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()
            
        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404
        
        await conn.execute(
            'DELETE FROM level_up_message_templates WHERE id = ? AND guild_id = ?',
            (template_id, guild_id)
        )
        
        await conn.commit()
        await conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Template '{existing_template[0]}' deleted successfully"
        })
        
    except Exception as e:
        logging.error(f"Error deleting message template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/template-variables', methods=['GET'])
async def api_template_variables_get():
    """Get available template variables."""
    try:
        conn = await get_leveling_db_connection()
        
        # Get all available template variables
        async with conn.execute('''
            SELECT variable_name, description, example_value, variable_type, is_system_variable
            FROM template_variables
            ORDER BY is_system_variable DESC, variable_name
        ''') as cursor:
            variables = await cursor.fetchall()
        
        await conn.close()
        
        variable_list = []
        for var in variables:
            variable_list.append({
                'variable_name': var[0],
                'description': var[1],
                'example_value': var[2],
                'variable_type': var[3],
                'is_system_variable': bool(var[4])
            })
        
        return jsonify(variable_list)
        
    except Exception as e:
        logging.error(f"Error getting template variables: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/message-templates/preview', methods=['POST'])
async def api_message_template_preview():
    """Preview a message template with sample data."""
    try:
        data = await request.get_json()
        message_content = data.get('message_content', '')
        guild_id = data.get('guild_id')
        
        if not message_content:
            return jsonify({"error": "message_content required"}), 400
        
        # Sample data for preview
        sample_data = {
            '{user}': '<@123456789012345678>',
            '{username}': 'SampleUser',
            '{user_id}': '123456789012345678',
            '{level}': '15',
            '{old_level}': '14',
            '{xp}': '2,500',
            '{current_xp}': '120',
            '{xp_needed}': '380',
            '{rank}': 'Veteran',
            '{old_rank}': 'Member',
            '{guild}': 'Sample Discord Server',
            '{guild_id}': '987654321098765432',
            '{channel}': '<#876543210987654321>',
            '{date}': datetime.now().strftime('%Y-%m-%d'),
            '{time}': datetime.now().strftime('%H:%M:%S'),
            '{total_members}': '150',
            '{server_rank}': '23',
            '{messages_sent}': '1,234',
            '{daily_xp}': '250',
            '{progress_bar}': '████████░░ 80%',
            '{congratulations}': 'Well done!'
        }
        
        # Replace template variables with sample data
        preview_content = message_content
        for variable, value in sample_data.items():
            preview_content = preview_content.replace(variable, str(value))
        
        return jsonify({
            "success": True,
            "preview_content": preview_content,
            "variables_used": [var for var in sample_data.keys() if var in message_content]
        })
        
    except Exception as e:
        logging.error(f"Error previewing message template: {e}")
        return jsonify({"error": str(e)}), 500

# =========================================================================
# TEMPLATES API ROUTES (for JavaScript compatibility)
# =========================================================================

@app.route('/api/leveling/templates', methods=['GET'])
async def api_leveling_templates_get():
    """Get message templates (alias for message-templates)."""
    try:
        guild_id = request.args.get('guild_id')
        template_type = request.args.get('type', 'default_levelup')
        
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Get templates for the guild and type
        async with conn.execute('''
            SELECT id, template_type, template_name, message_content, embed_enabled,
                   embed_config, milestone_interval, min_level, max_level, enabled,
                   send_to_channel, send_as_dm, mention_user, priority, created_at, updated_at
            FROM level_up_message_templates
            WHERE guild_id = ? AND template_type = ?
            ORDER BY priority DESC, template_name
        ''', (guild_id, template_type)) as cursor:
            templates = await cursor.fetchall()
        
        await conn.close()
        
        template_list = []
        for template in templates:
            template_list.append({
                'id': template[0],
                'type': template[1],
                'name': template[2],
                'content': template[3],
                'embed_enabled': bool(template[4]),
                'embed_config': json.loads(template[5]) if template[5] else {},
                'milestone_interval': template[6],
                'min_level': template[7],
                'max_level': template[8],
                'enabled': bool(template[9]),
                'send_to_channel': bool(template[10]),
                'send_as_dm': bool(template[11]),
                'mention_user': bool(template[12]),
                'priority': template[13],
                'created_at': template[14],
                'updated_at': template[15],
                'conditions': json.dumps({
                    'min_level': template[7],
                    'max_level': template[8]
                }) if template[7] or template[8] else ''
            })
        
        return jsonify(template_list)
        
    except Exception as e:
        logging.error(f"Error getting templates: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/templates', methods=['POST'])
async def api_leveling_templates_create():
    """Create message template (alias for message-templates)."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        template_type = data.get('type')
        template_name = data.get('name')
        message_content = data.get('content')
        
        if not all([guild_id, template_type, template_name, message_content]):
            return jsonify({"error": "guild_id, type, name, and content are required"}), 400
        
        # Validate template type
        valid_types = ['default_levelup', 'rank_promotion', 'milestone_level', 'first_level', 'major_milestone']
        if template_type not in valid_types:
            return jsonify({"error": f"Invalid template type. Must be one of: {', '.join(valid_types)}"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Check for duplicate template name within guild and type
        async with conn.execute(
            'SELECT id FROM level_up_message_templates WHERE guild_id = ? AND template_type = ? AND template_name = ?',
            (guild_id, template_type, template_name)
        ) as cursor:
            existing = await cursor.fetchone()
            
        if existing:
            await conn.close()
            return jsonify({"error": f"Template '{template_name}' already exists for {template_type}"}), 400
        
        # Parse conditions if provided
        conditions = data.get('conditions', '')
        min_level = None
        max_level = None
        
        if conditions:
            try:
                cond_data = json.loads(conditions)
                min_level = cond_data.get('min_level')
                max_level = cond_data.get('max_level')
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Create the template
        await conn.execute('''
            INSERT INTO level_up_message_templates
            (guild_id, template_type, template_name, message_content, embed_enabled, embed_config,
             milestone_interval, min_level, max_level, enabled, send_to_channel, send_as_dm,
             mention_user, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            guild_id, template_type, template_name, message_content,
            data.get('embed_enabled', False),
            json.dumps(data.get('embed_config', {})),
            data.get('milestone_interval'),
            min_level,
            max_level,
            data.get('enabled', True),
            data.get('send_to_channel', True),
            data.get('send_as_dm', False),
            data.get('mention_user', True),
            data.get('priority', 0)
        ))
        
        await conn.commit()
        
        # Get the created template ID
        async with conn.execute('SELECT last_insert_rowid()') as cursor:
            template_id = (await cursor.fetchone())[0]
            
        await conn.close()
        
        return jsonify({
            "success": True,
            "template_id": template_id,
            "message": f"Template '{template_name}' created successfully"
        })
        
    except Exception as e:
        logging.error(f"Error creating template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/templates/<int:template_id>', methods=['GET'])
async def api_leveling_templates_get_single(template_id):
    """Get single template by ID."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        async with conn.execute('''
            SELECT id, template_type, template_name, message_content, embed_enabled,
                   embed_config, milestone_interval, min_level, max_level, enabled,
                   send_to_channel, send_as_dm, mention_user, priority, created_at, updated_at
            FROM level_up_message_templates
            WHERE id = ? AND guild_id = ?
        ''', (template_id, guild_id)) as cursor:
            template = await cursor.fetchone()
        
        await conn.close()
        
        if template:
            return jsonify({
                'id': template[0],
                'type': template[1],
                'name': template[2],
                'content': template[3],
                'embed_enabled': bool(template[4]),
                'embed_config': json.loads(template[5]) if template[5] else {},
                'milestone_interval': template[6],
                'min_level': template[7],
                'max_level': template[8],
                'enabled': bool(template[9]),
                'send_to_channel': bool(template[10]),
                'send_as_dm': bool(template[11]),
                'mention_user': bool(template[12]),
                'priority': template[13],
                'created_at': template[14],
                'updated_at': template[15],
                'conditions': json.dumps({
                    'min_level': template[7],
                    'max_level': template[8]
                }) if template[7] or template[8] else ''
            })
        else:
            return jsonify({"error": "Template not found"}), 404
            
    except Exception as e:
        logging.error(f"Error getting template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/templates/<int:template_id>', methods=['PUT'])
async def api_leveling_templates_update(template_id):
    """Update template (alias for message-templates)."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        
        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Verify template exists and belongs to guild
        async with conn.execute(
            'SELECT id, template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?',
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()
            
        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404
        
        # Parse conditions if provided
        conditions = data.get('conditions', '')
        min_level = None
        max_level = None
        
        if conditions:
            try:
                cond_data = json.loads(conditions)
                min_level = cond_data.get('min_level')
                max_level = cond_data.get('max_level')
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Build update query - map frontend field names to database field names
        field_mapping = {
            'type': 'template_type',
            'name': 'template_name',
            'content': 'message_content',
            'embed_enabled': 'embed_enabled',
            'embed_config': 'embed_config',
            'milestone_interval': 'milestone_interval',
            'enabled': 'enabled',
            'send_to_channel': 'send_to_channel',
            'send_as_dm': 'send_as_dm',
            'mention_user': 'mention_user',
            'priority': 'priority'
        }
        
        update_fields = []
        update_values = []
        
        for frontend_field, db_field in field_mapping.items():
            if frontend_field in data:
                if frontend_field == 'embed_config':
                    update_fields.append(f"{db_field} = ?")
                    update_values.append(json.dumps(data[frontend_field]) if data[frontend_field] else '{}')
                else:
                    update_fields.append(f"{db_field} = ?")
                    update_values.append(data[frontend_field])
        
        # Add conditions fields if they were parsed
        if 'conditions' in data:
            if min_level is not None:
                update_fields.append("min_level = ?")
                update_values.append(min_level)
            if max_level is not None:
                update_fields.append("max_level = ?")
                update_values.append(max_level)
        
        if not update_fields:
            await conn.close()
            return jsonify({"error": "No valid fields to update"}), 400
        
        update_values.extend([template_id, guild_id])
        
        await conn.execute(f'''
            UPDATE level_up_message_templates
            SET {', '.join(update_fields)}
            WHERE id = ? AND guild_id = ?
        ''', update_values)
        
        await conn.commit()
        await conn.close()
        
        return jsonify({
            "success": True,
            "message": "Template updated successfully"
        })
        
    except Exception as e:
        logging.error(f"Error updating template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/templates/<int:template_id>', methods=['DELETE'])
async def api_leveling_templates_delete(template_id):
    """Delete template (alias for message-templates)."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        # Verify template exists and belongs to guild
        async with conn.execute(
            'SELECT template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?',
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()
            
        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404
        
        await conn.execute(
            'DELETE FROM level_up_message_templates WHERE id = ? AND guild_id = ?',
            (template_id, guild_id)
        )
        
        await conn.commit()
        await conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Template '{existing_template[0]}' deleted successfully"
        })
        
    except Exception as e:
        logging.error(f"Error deleting template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/templates/<int:template_id>/preview', methods=['GET'])
async def api_leveling_templates_preview(template_id):
    """Preview template with sample data."""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400
            
        conn = await get_leveling_db_connection()
        
        async with conn.execute(
            'SELECT message_content FROM level_up_message_templates WHERE id = ? AND guild_id = ?',
            (template_id, guild_id)
        ) as cursor:
            template = await cursor.fetchone()
        
        await conn.close()
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        # Sample data for preview
        sample_data = {
            '{user}': '<@123456789012345678>',
            '{username}': 'SampleUser',
            '{user_id}': '123456789012345678',
            '{level}': '15',
            '{previous_level}': '14',
            '{xp}': '2,500',
            '{current_xp}': '120',
            '{xp_needed}': '380',
            '{rank}': 'Veteran',
            '{previous_rank}': 'Member',
            '{guild}': 'Sample Discord Server',
            '{guild_id}': '987654321098765432',
            '{channel}': '<#876543210987654321>',
            '{date}': datetime.now().strftime('%Y-%m-%d'),
            '{time}': datetime.now().strftime('%H:%M:%S'),
            '{total_members}': '150',
            '{leaderboard_position}': '23',
            '{messages_sent}': '1,234',
            '{daily_xp}': '250',
            '{progress_bar}': '████████░░ 80%',
            '{congratulations}': 'Well done!',
            '{range}': 'Journeyman',
            '{tier}': 'Journeyman'
        }
        
        # Replace template variables with sample data
        preview_content = template[0]
        for variable, value in sample_data.items():
            preview_content = preview_content.replace(variable, str(value))
        
        return jsonify({
            "success": True,
            "preview": preview_content
        })
        
    except Exception as e:
        logging.error(f"Error previewing template: {e}")
        return jsonify({"error": str(e)}), 500

# Level Ranges API endpoints
@app.route('/api/leveling/ranges/guild/<guild_id>', methods=['GET'])
async def api_get_guild_ranges(guild_id):
    """Get all level ranges for a guild."""
    try:
        conn = await get_leveling_db_connection()
        
        async with conn.execute('''
            SELECT id, min_level, max_level, range_name, description, created_at
            FROM level_range_names
            WHERE guild_id = ?
            ORDER BY min_level
        ''', (guild_id,)) as cursor:
            ranges = await cursor.fetchall()
        
        await conn.close()
        
        range_list = []
        for range_data in ranges:
            range_list.append({
                'id': range_data[0],
                'min_level': range_data[1],
                'max_level': range_data[2],
                'range_name': range_data[3],
                'description': range_data[4],
                'created_at': range_data[5]
            })
        
        return jsonify({'ranges': range_list})
        
    except Exception as e:
        logging.error(f"Error getting guild ranges: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/ranges', methods=['POST'])
async def api_create_level_range():
    """Create a new level range."""
    try:
        data = await request.get_json()
        guild_id = data.get('guild_id')
        min_level = data.get('min_level')
        max_level = data.get('max_level')
        range_name = data.get('range_name')
        description = data.get('description', '')
        
        if not all([guild_id, min_level is not None, max_level is not None, range_name]):
            return jsonify({"error": "Missing required fields"}), 400
        
        try:
            min_level = int(min_level)
            max_level = int(max_level)
            
            if min_level < 1 or max_level < min_level:
                return jsonify({"error": "Invalid level range"}), 400
                
        except ValueError:
            return jsonify({"error": "Invalid level values"}), 400
        
        conn = await get_leveling_db_connection()
        
        # Check for overlapping ranges
        async with conn.execute('''
            SELECT COUNT(*) FROM level_range_names
            WHERE guild_id = ? AND (
                (? >= min_level AND ? <= max_level) OR
                (? >= min_level AND ? <= max_level) OR
                (min_level >= ? AND min_level <= ?) OR
                (max_level >= ? AND max_level <= ?)
            )
        ''', (guild_id, min_level, min_level, max_level, max_level,
              min_level, max_level, min_level, max_level)) as cursor:
            overlap_count = (await cursor.fetchone())[0]
        
        if overlap_count > 0:
            await conn.close()
            return jsonify({"error": "Range overlaps with existing ranges"}), 400
        
        # Insert new range
        await conn.execute('''
            INSERT INTO level_range_names
            (guild_id, min_level, max_level, range_name, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, min_level, max_level, range_name, description))
        
        await conn.commit()
        await conn.close()
        
        return jsonify({"message": "Range added successfully"})
        
    except Exception as e:
        logging.error(f"Error creating level range: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/ranges/<int:range_id>', methods=['PUT'])
async def api_update_level_range(range_id):
    """Update an existing level range."""
    try:
        data = await request.get_json()
        min_level = data.get('min_level')
        max_level = data.get('max_level')
        range_name = data.get('range_name')
        description = data.get('description', '')
        
        if not all([min_level is not None, max_level is not None, range_name]):
            return jsonify({"error": "Missing required fields"}), 400
        
        try:
            min_level = int(min_level)
            max_level = int(max_level)
            
            if min_level < 1 or max_level < min_level:
                return jsonify({"error": "Invalid level range"}), 400
                
        except ValueError:
            return jsonify({"error": "Invalid level values"}), 400
        
        conn = await get_leveling_db_connection()
        
        # Get guild_id for this range
        async with conn.execute(
            'SELECT guild_id FROM level_range_names WHERE id = ?',
            (range_id,)
        ) as cursor:
            result = await cursor.fetchone()
        
        if not result:
            await conn.close()
            return jsonify({"error": "Range not found"}), 404
        
        guild_id = result[0]
        
        # Check for overlapping ranges (excluding current range)
        async with conn.execute('''
            SELECT COUNT(*) FROM level_range_names
            WHERE guild_id = ? AND id != ? AND (
                (? >= min_level AND ? <= max_level) OR
                (? >= min_level AND ? <= max_level) OR
                (min_level >= ? AND min_level <= ?) OR
                (max_level >= ? AND max_level <= ?)
            )
        ''', (guild_id, range_id, min_level, min_level, max_level, max_level,
              min_level, max_level, min_level, max_level)) as cursor:
            overlap_count = (await cursor.fetchone())[0]
        
        if overlap_count > 0:
            await conn.close()
            return jsonify({"error": "Range overlaps with existing ranges"}), 400
        
        # Update range
        await conn.execute('''
            UPDATE level_range_names
            SET min_level = ?, max_level = ?, range_name = ?, description = ?
            WHERE id = ?
        ''', (min_level, max_level, range_name, description, range_id))
        
        await conn.commit()
        await conn.close()
        
        return jsonify({"message": "Range updated successfully"})
        
    except Exception as e:
        logging.error(f"Error updating level range: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leveling/ranges/<int:range_id>', methods=['DELETE'])
async def api_delete_level_range(range_id):
    """Delete a level range."""
    try:
        conn = await get_leveling_db_connection()
        
        # Verify range exists
        async with conn.execute(
            'SELECT id FROM level_range_names WHERE id = ?',
            (range_id,)
        ) as cursor:
            result = await cursor.fetchone()
        
        if not result:
            await conn.close()
            return jsonify({"error": "Range not found"}), 404
        
        await conn.execute('DELETE FROM level_range_names WHERE id = ?', (range_id,))
        
        await conn.commit()
        await conn.close()
        
        return jsonify({"message": "Range deleted successfully"})
        
    except Exception as e:
        logging.error(f"Error deleting level range: {e}")
        return jsonify({"error": str(e)}), 500

async def stats_broadcast_loop():
    """Background task to broadcast stats every 2 seconds."""
    global _needs_immediate_broadcast
    while True:
        try:
            # Check if immediate broadcast is needed
            if _needs_immediate_broadcast:
                _needs_immediate_broadcast = False
                await broadcast_stats()
                await asyncio.sleep(0.1)  # Short delay after immediate broadcast
            else:
                await broadcast_stats()
                await asyncio.sleep(2)  # Update every 2 seconds
        except Exception as e:
            logging.error(f"Error in stats broadcast loop: {e}")
            await asyncio.sleep(5)  # Wait longer on error

# Chat History API Endpoints

@app.route('/api/chat/guilds', methods=['GET'])
async def get_chat_guilds():
    """Get all guilds with chat logging info."""
    try:
        from database_utils import get_all_guild_settings, get_guild_message_count, is_guild_scanning
        from database_schema import get_guild_config_db_path
        import aiosqlite

        guild_settings = await get_all_guild_settings()
        guilds_data = []

        for settings in guild_settings:
            guild_id = settings['guild_id']

            # Get message count
            message_count = await get_guild_message_count(guild_id)

            # Get scanning status
            scanning = await is_guild_scanning(guild_id)

            # Get fetch progress
            config_db_path = get_guild_config_db_path()
            async with aiosqlite.connect(config_db_path) as conn:
                # Count total channels and completed channels
                async with conn.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN fetch_completed = 1 THEN 1 ELSE 0 END) as completed
                    FROM historical_fetch_progress
                    WHERE guild_id = ?
                """, (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                    total_channels = row[0] if row and row[0] else 0
                    completed_channels = row[1] if row and row[1] else 0

                # Get last message time
                from database_schema import get_guild_db_path
                import os
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

            # Calculate fetch progress percentage
            fetch_percentage = 0
            if total_channels > 0:
                fetch_percentage = int((completed_channels / total_channels) * 100)

            guilds_data.append({
                'guild_id': guild_id,
                'guild_name': settings['guild_name'],
                'logging_enabled': bool(settings['logging_enabled']),
                'total_messages': message_count,
                'channels_count': total_channels,
                'date_joined': settings['date_joined'],
                'last_message_time': last_message_time,
                'is_scanning': scanning,
                'fetch_progress': {
                    'completed': completed_channels == total_channels and total_channels > 0,
                    'percentage': fetch_percentage,
                    'channels_done': completed_channels,
                    'channels_total': total_channels
                }
            })

        return jsonify({'guilds': guilds_data})

    except Exception as e:
        logging.error(f"Error fetching chat guilds: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/guild/<guild_id>/settings', methods=['GET', 'POST'])
async def guild_chat_settings(guild_id):
    """Get or update guild chat settings."""
    try:
        from database_utils import get_guild_settings, update_guild_logging

        if request.method == 'GET':
            settings = await get_guild_settings(guild_id)
            if not settings:
                return jsonify({'error': 'Guild not found'}), 404
            return jsonify(settings)

        else:  # POST
            data = await request.get_json()
            enabled = data.get('logging_enabled', True)
            await update_guild_logging(guild_id, enabled)
            return jsonify({'success': True})

    except Exception as e:
        logging.error(f"Error managing guild settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/guild/<guild_id>/channels', methods=['GET'])
async def get_guild_channels(guild_id):
    """Get all channels for a guild with message counts."""
    try:
        from database_schema import get_guild_db_path
        import os
        import aiosqlite

        guild_db_path = get_guild_db_path(guild_id)

        if not os.path.exists(guild_db_path):
            return jsonify({'channels': []})

        channels_data = []

        async with aiosqlite.connect(guild_db_path) as conn:
            # Get unique channels with message counts
            async with conn.execute("""
                SELECT channel_id, COUNT(*) as message_count
                FROM messages
                GROUP BY channel_id
                ORDER BY message_count DESC
            """) as cursor:
                rows = await cursor.fetchall()

                for row in rows:
                    channel_id, message_count = row

                    # Try to get channel name from bot
                    channel_name = f"Channel {channel_id}"
                    if bot_instance:
                        try:
                            channel = bot_instance.get_channel(int(channel_id))
                            if channel:
                                channel_name = channel.name
                        except:
                            pass

                    channels_data.append({
                        'channel_id': channel_id,
                        'channel_name': channel_name,
                        'message_count': message_count
                    })

        return jsonify({'channels': channels_data})

    except Exception as e:
        logging.error(f"Error fetching guild channels: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/guild/<guild_id>/messages', methods=['GET'])
async def get_guild_messages(guild_id):
    """Get messages for a guild/channel."""
    try:
        from database_schema import get_guild_db_path
        import os
        import aiosqlite

        channel_id = request.args.get('channel_id')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        guild_db_path = get_guild_db_path(guild_id)

        if not os.path.exists(guild_db_path):
            return jsonify({'messages': [], 'total': 0, 'has_more': False})

        async with aiosqlite.connect(guild_db_path) as conn:
            conn.row_factory = aiosqlite.Row

            # Build query
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

            # Get messages
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                messages = []

                for row in rows:
                    msg_dict = dict(row)

                    # Resolve user name
                    user_name = await resolve_user_name(msg_dict['user_id'])

                    # Get channel name
                    channel_name = f"Channel {msg_dict['channel_id']}"
                    if bot_instance:
                        try:
                            channel = bot_instance.get_channel(int(msg_dict['channel_id']))
                            if channel:
                                channel_name = channel.name
                        except:
                            pass

                    messages.append({
                        'id': msg_dict['id'],
                        'user_id': msg_dict['user_id'],
                        'username': user_name,
                        'channel_id': msg_dict['channel_id'],
                        'channel_name': channel_name,
                        'message_content': msg_dict['message_content'],
                        'timestamp': msg_dict['timestamp']
                    })

            # Get total count
            async with conn.execute(count_query, count_params) as cursor:
                total = (await cursor.fetchone())[0]

        has_more = (offset + limit) < total

        return jsonify({
            'messages': messages,
            'total': total,
            'has_more': has_more
        })

    except Exception as e:
        logging.error(f"Error fetching guild messages: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/guild/<guild_id>/recent', methods=['GET'])
async def get_recent_messages(guild_id):
    """Get recent 50 messages for a guild."""
    try:
        from database_schema import get_guild_db_path
        import os
        import aiosqlite

        channel_id = request.args.get('channel_id')

        guild_db_path = get_guild_db_path(guild_id)

        if not os.path.exists(guild_db_path):
            return jsonify({'messages': []})

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
                    user_name = await resolve_user_name(msg_dict['user_id'])

                    # Get channel name
                    channel_name = f"Channel {msg_dict['channel_id']}"
                    if bot_instance:
                        try:
                            channel = bot_instance.get_channel(int(msg_dict['channel_id']))
                            if channel:
                                channel_name = channel.name
                        except:
                            pass

                    messages.append({
                        'id': msg_dict['id'],
                        'user_id': msg_dict['user_id'],
                        'username': user_name,
                        'channel_id': msg_dict['channel_id'],
                        'channel_name': channel_name,
                        'message_content': msg_dict['message_content'],
                        'timestamp': msg_dict['timestamp']
                    })

        return jsonify({'messages': messages})

    except Exception as e:
        logging.error(f"Error fetching recent messages: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/guild/<guild_id>/stats', methods=['GET'])
async def get_guild_chat_stats(guild_id):
    """Get statistics for a guild."""
    try:
        from database_utils import get_guild_message_count, is_guild_scanning
        from database_schema import get_guild_config_db_path, get_guild_db_path
        import os
        import aiosqlite

        message_count = await get_guild_message_count(guild_id)
        scanning = await is_guild_scanning(guild_id)

        # Get date range
        guild_db_path = get_guild_db_path(guild_id)
        oldest_message = None
        newest_message = None
        active_channels = 0

        if os.path.exists(guild_db_path):
            async with aiosqlite.connect(guild_db_path) as conn:
                # Get oldest message
                async with conn.execute("""
                    SELECT timestamp FROM messages
                    ORDER BY timestamp ASC LIMIT 1
                """) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        oldest_message = row[0]

                # Get newest message
                async with conn.execute("""
                    SELECT timestamp FROM messages
                    ORDER BY timestamp DESC LIMIT 1
                """) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        newest_message = row[0]

                # Count active channels
                async with conn.execute("""
                    SELECT COUNT(DISTINCT channel_id) FROM messages
                """) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        active_channels = row[0]

        # Get fetch progress
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
            'total_messages': message_count,
            'active_channels': active_channels,
            'oldest_message': oldest_message,
            'newest_message': newest_message,
            'is_scanning': scanning,
            'fetch_stats': {
                'total_fetched': total_fetched,
                'channels_tracking': channels_tracking,
                'channels_completed': channels_completed
            }
        })

    except Exception as e:
        logging.error(f"Error fetching guild stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/fetch-progress', methods=['GET'])
async def get_fetch_progress():
    """Get historical fetch progress for all guilds."""
    try:
        from database_schema import get_guild_config_db_path
        import aiosqlite

        config_db_path = get_guild_config_db_path()

        progress_data = []

        async with aiosqlite.connect(config_db_path) as conn:
            conn.row_factory = aiosqlite.Row

            # Get progress by guild
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
                    total = row_dict['total_channels']
                    completed = row_dict['completed_channels']
                    percentage = int((completed / total) * 100) if total > 0 else 0

                    progress_data.append({
                        'guild_id': row_dict['guild_id'],
                        'total_channels': total,
                        'completed_channels': completed,
                        'total_fetched': row_dict['total_fetched'] or 0,
                        'percentage': percentage,
                        'last_fetch': row_dict['last_fetch'],
                        'is_complete': completed == total and total > 0
                    })

        return jsonify({'progress': progress_data})

    except Exception as e:
        logging.error(f"Error fetching progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.before_serving
async def startup():
    """Start background tasks."""
    app.add_background_task(stats_broadcast_loop)

# API for bot integration
class DashboardAPI:
    """API class for bot integration."""
    
    @staticmethod
    def update_stat(key: str, value):
        """Update a statistic from the bot."""
        real_time_stats.update_stat(key, value)
    
    @staticmethod
    def log_message(author: str, guild: str, channel: str):
        """Log a message from the bot."""
        real_time_stats.add_message_log(str(author), str(guild), str(channel))
        global _needs_immediate_broadcast
        _needs_immediate_broadcast = True
    
    @staticmethod
    def log_event(event: str, event_type: str = "info"):
        """Log an event from the bot."""
        real_time_stats.add_event_log(str(event), event_type)
    
    @staticmethod
    def set_status(status: str):
        """Set bot status."""
        real_time_stats.set_status(status)
    
    @staticmethod
    def increment_command_count():
        """Increment command counter."""
        real_time_stats.stats["commands_executed"] += 1
        real_time_stats.add_event_log("Command executed", "command")

# Export for bot integration
dashboard_api = DashboardAPI()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5001, debug=False)
