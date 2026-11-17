"""Register HTTP endpoints and translate input errors to the existing JSON form."""

from flask import current_app, jsonify

from ..validation import ValidationError


def service():
    return current_app.extensions["sos_service"]


def validation_error(error):
    return jsonify(error=str(error)), 400


def register_routes(app):
    from .dashboard import blueprint as dashboard
    from .device import blueprint as device
    from .web import blueprint as web

    for blueprint in (web, device, dashboard):
        app.register_blueprint(blueprint)
    app.register_error_handler(ValidationError, validation_error)
