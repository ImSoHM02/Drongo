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
from datetime import datetime, timedelta
from typing import Dict, List, Set
from quart import Quart, render_template, jsonify, websocket
from quart_cors import cors
from collections import deque

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection
from database_utils import optimized_db

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
        db_file = "chat_database.db"  # Adjust to your database file path
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
    return await render_template('dashboard.html')

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