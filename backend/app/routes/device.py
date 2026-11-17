"""HTTP endpoints used by ESP32 firmware."""

from flask import Blueprint, jsonify, request

from ..auth import device_auth
from . import service


blueprint = Blueprint("device", __name__, url_prefix="/api/device")


@blueprint.post("/telemetry")
@device_auth
def telemetry():
    service().record_telemetry(request.get_json(silent=True))
    return jsonify(ok=True)


@blueprint.get("/command")
@device_auth
def device_command():
    command = service().pending_command(request.args.get("device_id", ""))
    return command, 200, {"Content-Type": "text/plain"}
