import json
import logging

from quart import Blueprint, websocket

from . import state
from .stats_service import get_enhanced_stats

ws_bp = Blueprint("dashboard_websocket", __name__)


@ws_bp.websocket("/ws")
async def websocket_endpoint():
    """WebSocket endpoint for real-time updates."""
    ws = websocket._get_current_object()
    state.connected_clients.add(ws)

    try:
        stats = await get_enhanced_stats()
        await ws.send(json.dumps({
            "type": "stats_update",
            "data": stats
        }))

        while True:
            try:
                message = await ws.receive()
                if isinstance(message, str):
                    try:
                        data = json.loads(message)

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
                logging.debug(f"WebSocket connection ended: {e}")
                break

    except Exception as e:
        logging.debug(f"WebSocket error: {e}")
    finally:
        state.connected_clients.discard(ws)
