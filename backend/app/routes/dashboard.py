"""Authenticated dashboard data and requests for remote location."""

from flask import Blueprint, jsonify, request

from ..auth import admin_auth
from . import service


blueprint = Blueprint("dashboard", __name__, url_prefix="/api")


@blueprint.get("/status")
@admin_auth
def status():
    return jsonify(service().status())


@blueprint.get("/track")
@admin_auth
def track():
    return jsonify(service().track(request.args.get("device_id", "ngoc-01"), request.args.get("hours", "24")))


@blueprint.post("/command")
@admin_auth
def issue_command():
    service().issue_locate(request.get_json(silent=True))
    return jsonify(ok=True, message="Đã xếp lệnh; chờ thiết bị kết nối")
