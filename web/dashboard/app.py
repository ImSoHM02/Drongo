import logging
import os
import sys

from quart import Quart
from quart_cors import cors

# Ensure project root is on the path when running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from .broadcast import stats_broadcast_loop
from .routes.chat_routes import chat_bp
from .routes.github_routes import github_bp
from .routes.leveling_routes import leveling_bp
from .routes.spa_routes import spa_bp
from .routes.system_routes import system_bp
from .websocket_routes import ws_bp


def create_app() -> Quart:
    """Create and configure the Quart application."""
    app = Quart(__name__)
    app = cors(app)

    app.register_blueprint(ws_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(leveling_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(spa_bp)

    _register_background_tasks(app)
    return app


def _register_background_tasks(app: Quart):
    @app.before_serving
    async def startup():
        app.add_background_task(stats_broadcast_loop)


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5001, debug=False)
