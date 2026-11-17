"""Register HTTP endpoints and translate input errors to the existing JSON form."""

from flask import current_app, jsonify

from ..validation import ValidationError
from ..repositories.errors import DatabaseUnavailable


def service():
    return current_app.extensions["sos_service"]


def validation_error(error):
    return jsonify(error=str(error)), 400


def database_error(error):
    return jsonify(error="database unavailable"), 503


def register_routes(app):
    from .dashboard import blueprint as dashboard
    from .device import blueprint as device
    from .web import blueprint as web

    for blueprint in (web, device, dashboard):
        app.register_blueprint(blueprint)
    app.register_error_handler(ValidationError, validation_error)
    app.register_error_handler(DatabaseUnavailable, database_error)
