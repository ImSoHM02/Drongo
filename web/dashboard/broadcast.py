import asyncio
import json
import logging

from . import state
from .stats_service import get_enhanced_stats

_needs_immediate_broadcast = False


async def broadcast_stats():
    """Broadcast current stats to all connected WebSocket clients."""
    if not state.connected_clients:
        return

    stats = await get_enhanced_stats()

    message = json.dumps({
        "type": "stats_update",
        "data": stats
    })

    disconnected_clients = set()
    for client in state.connected_clients.copy():
        try:
            await client.send(message)
        except Exception as e:
            logging.debug(f"Client disconnected during broadcast: {e}")
            disconnected_clients.add(client)

    state.connected_clients.difference_update(disconnected_clients)


def request_immediate_broadcast():
    """Flag that stats should be broadcast ASAP."""
    global _needs_immediate_broadcast
    _needs_immediate_broadcast = True


async def stats_broadcast_loop():
    """Background task to broadcast stats every 2 seconds."""
    global _needs_immediate_broadcast
    while True:
        try:
            if _needs_immediate_broadcast:
                _needs_immediate_broadcast = False
                await broadcast_stats()
                await asyncio.sleep(0.1)
            else:
                await broadcast_stats()
                await asyncio.sleep(2)
        except Exception as e:
            logging.error(f"Error in stats broadcast loop: {e}")
            await asyncio.sleep(5)
