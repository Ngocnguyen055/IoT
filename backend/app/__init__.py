"""Create independent Flask applications with explicit configuration."""

from flask import Flask

from project_config import ROOT
from .config import build_config
from .repositories.factory import build_repository
from .routes import register_routes
from .services.monitoring import MonitoringService


def create_app(config=None, *, repository=None):
    app = Flask(
        __name__,
        template_folder=str(ROOT / "frontend" / "templates"),
        static_folder=str(ROOT / "frontend" / "static"),
        static_url_path="/static",
    )
    app.config.from_mapping(build_config(config))

    if repository is None:
        repository = build_repository(app.config)
    repository.initialize()
    app.extensions["sos_repository"] = repository
    app.extensions["sos_service"] = MonitoringService(repository)
    register_routes(app)
    return app
