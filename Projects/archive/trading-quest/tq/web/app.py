"""Flask application factory for Trading Quest web dashboard."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_app(config: dict | None = None):
    """Create and configure the Flask app."""
    try:
        from flask import Flask
    except ImportError:
        logger.error("Flask not installed. Run: pip install flask")
        raise

    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )

    app.config["SECRET_KEY"] = "tq-dev-key-change-in-production"
    if config:
        app.config.update(config)

    # Register routes
    from tq.web.routes import register_routes
    register_routes(app)

    return app


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = True):
    """Run the development server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)
