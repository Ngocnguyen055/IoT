"""Authentication reads settings from the application handling each request."""

from functools import wraps
from hmac import compare_digest

from flask import current_app, jsonify, request, session


def device_auth(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        provided = request.headers.get("X-Device-Key", "").encode("utf-8")
        expected = current_app.config["DEVICE_KEY"].encode("utf-8")
        if not compare_digest(provided, expected):
            return jsonify(error="device unauthorized"), 401
        return function(*args, **kwargs)
    return wrapped


def admin_auth(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return jsonify(error="login required"), 401
        return function(*args, **kwargs)
    return wrapped


def password_matches(provided):
    expected = current_app.config["ADMIN_PASSWORD"]
    return compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
