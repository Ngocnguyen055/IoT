"""Create independent Flask applications with explicit configuration."""

from flask import Flask

from project_config import ROOT
from .config import build_config
from .repositories.sqlite import SQLiteRepository
from .routes import register_routes
from .services.monitoring import MonitoringService


def create_app(config=None):
    app = Flask(
        __name__,
        template_folder=str(ROOT / "frontend" / "templates"),
        static_folder=str(ROOT / "frontend" / "static"),
        static_url_path="/static",
    )
    app.config.from_mapping(build_config(config))

    repository = SQLiteRepository(app.config["DB_PATH"])
    repository.initialize()
    app.extensions["sos_repository"] = repository
    app.extensions["sos_service"] = MonitoringService(repository)
    register_routes(app)
    return app
