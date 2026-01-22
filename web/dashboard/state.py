from typing import Dict, Set

# Bot instance for Discord API access
bot_instance = None

# Name resolution caches
name_cache: Dict[str, str] = {}
cache_expiry: Dict[str, float] = {}
CACHE_DURATION = 300  # 5 minutes

# Connected WebSocket clients
connected_clients: Set = set()


def set_bot_instance(bot):
    """Set the bot instance for Discord API access."""
    global bot_instance
    bot_instance = bot
    name_cache.clear()
    cache_expiry.clear()
