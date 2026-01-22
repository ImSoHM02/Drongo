from quart import Blueprint, jsonify, send_from_directory
from werkzeug.exceptions import NotFound

from ..paths import REACT_BUILD_DIR

spa_bp = Blueprint("dashboard_spa", __name__)


@spa_bp.route("/")
async def serve_react_app():
    """Serve React app."""
    return await send_from_directory(REACT_BUILD_DIR, "index.html")


@spa_bp.route("/<path:path>")
async def serve_react_static(path):
    """Serve React static files and handle client-side routing."""
    if path.startswith("api/") or path.startswith("ws"):
        return jsonify({"error": "Not found"}), 404

    try:
        return await send_from_directory(REACT_BUILD_DIR, path)
    except NotFound:
        return await send_from_directory(REACT_BUILD_DIR, "index.html")
