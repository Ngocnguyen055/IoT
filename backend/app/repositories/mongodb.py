"""MongoDB implementation of the existing readings and commands storage contract."""

from functools import wraps

from pymongo import ASCENDING, DESCENDING, ReadPreference, ReturnDocument, timeout
from pymongo.errors import OperationFailure, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .errors import DatabaseUnavailable
from ..models import DeviceCommand, READING_FIELDS, Reading, ReadingCounter


GPS_FILTER = {"lat": {"$ne": None}, "lon": {"$ne": None}}


def storage_errors(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except PyMongoError as error:
            reason = "connection"
            if isinstance(error, OperationFailure) and error.code in {13, 18}:
                reason = "authentication"
            raise DatabaseUnavailable(reason) from None
    return wrapped


def public_reading(document):
    if document is None:
        return None
    return Reading.from_document(document).to_public()


class MongoDBRepository:
    def __init__(self, client, database):
        self.client = client
        self.database_name = database
        self.database = client[database]
        self.readings = self.database["readings"]
        self.commands = self.database["commands"]
        self.counters = self.database["counters"]

    @storage_errors
    def initialize(self):
        try:
            self.client.admin.command("ping")
            hello = self.client.admin.command("hello")
            if not hello.get("setName") and hello.get("msg") != "isdbgrid":
                raise DatabaseUnavailable("transactions_require_replica_set")
            self._initialize_storage()
        except Exception:
            self.close()
            raise

    def _initialize_storage(self):
        self.readings.create_index([("device_id", ASCENDING), ("ts", ASCENDING)], name="idx_readings_device_ts")
        self.readings.create_index([("device_id", ASCENDING), ("_id", DESCENDING)], name="idx_readings_device_id")
        latest = self.readings.find_one({}, {"_id": 1}, sort=[("_id", DESCENDING)])
        maximum = latest["_id"] if latest else 0
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
            raise ValueError("MongoDB readings must use positive integer IDs")
        self.counters.update_one({"_id": "readings"}, {"$max": {"value": maximum}}, upsert=True)
        counter = self.counters.find_one({"_id": "readings"})
        ReadingCounter.from_document(counter)

    def close(self):
        self.client.close()

    def _with_transaction(self, operation):
        with timeout(10), self.client.start_session() as session:
            return session.with_transaction(
                operation,
                read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern("majority"),
                read_preference=ReadPreference.PRIMARY,
            )

    @storage_errors
    def save_reading(self, reading, timestamp):
        def persist(session):
            counter = self.counters.find_one_and_update(
                {"_id": "readings"}, {"$inc": {"value": 1}},
                return_document=ReturnDocument.AFTER, session=session,
            )
            document = Reading(id=counter["value"], ts=timestamp, **reading).to_document()
            self.readings.insert_one(document, session=session)
            if reading["event"] == "remote":
                self.commands.update_one({"_id": reading["device_id"]}, {"$set": {"cmd": "NONE"}}, session=session)
        self._with_transaction(persist)

    @storage_errors
    def pending_command(self, device_id):
        command = self.commands.find_one({"_id": device_id})
        return DeviceCommand.from_document(command).cmd if command else "NONE"

    @storage_errors
    def queue_locate(self, device_id):
        command = DeviceCommand(device_id, "LOCATE")
        self.commands.update_one({"_id": command.device_id}, {"$set": {"cmd": command.cmd}}, upsert=True)

    @storage_errors
    def dashboard_snapshot(self):
        history = [public_reading(row) for row in self.readings.find().sort("_id", DESCENDING).limit(150)]
        location = self.readings.find_one(GPS_FILTER, sort=[("_id", DESCENDING)])
        alerts = [public_reading(row) for row in self.readings.find({"event": {"$ne": "telemetry"}}).sort("_id", DESCENDING).limit(20)]
        commands = [{"device_id": row["_id"], "cmd": row.get("cmd", "NONE")} for row in self.commands.find()]
        return {
            "latest": history[0] if history else None,
            "history": history,
            "last_location": {key: location.get(key) for key in ("device_id", "lat", "lon", "ts")} if location else None,
            "alerts": alerts,
            "commands": commands,
        }

    @storage_errors
    def track_points(self, device_id, since):
        query = {**GPS_FILTER, "device_id": device_id, "ts": {"$gte": since}}
        rows = list(self.readings.find(query).sort("_id", DESCENDING).limit(1000))
        return [{"id": int(row["_id"]), **{key: row.get(key) for key in ("ts", "lat", "lon", "gps_satellites", "event")}}
                for row in reversed(rows)]
