"""MongoDB implementation of the existing readings and commands storage contract."""

from functools import wraps

from pymongo import ASCENDING, DESCENDING, ReadPreference, ReturnDocument, timeout
from pymongo.errors import OperationFailure, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .errors import DatabaseUnavailable
from ..models import DeviceCommand, READING_FIELDS, Reading, ReadingCounter
from ..alerts import ALERT_PAGE_SIZE, HOME_ALERT_LIMIT, alert_filter, alert_page_result
from .indexes import ALERT_INDEX, DEVICE_LOCATION_INDEX, GPS_FILTER, LOCATION_INDEX, ensure_reading_indexes


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
        ensure_reading_indexes(self.readings)
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
    def dashboard_snapshot(self, *, compact=False):
        history = [public_reading(row) for row in self.readings.find().sort("_id", DESCENDING).limit(1 if compact else 150)]
        location = next(self.readings.find(GPS_FILTER).hint(LOCATION_INDEX).sort("_id", DESCENDING).limit(1), None)
        alerts = [public_reading(row) for row in self.readings.find(alert_filter()).hint(ALERT_INDEX).sort("_id", DESCENDING).limit(HOME_ALERT_LIMIT if compact else 20)]
        commands = [{"device_id": row["_id"], "cmd": row.get("cmd", "NONE")} for row in self.commands.find()]
        result = {
            "latest": history[0] if history else None,
            "history": history,
            "last_location": {key: location.get(key) for key in ("device_id", "lat", "lon", "ts")} if location else None,
            "alerts": alerts,
            "commands": commands,
        }
        if compact:
            result.pop("history")
        return result

    @storage_errors
    def alert_by_id(self, identifier):
        return public_reading(self.readings.find_one({"_id": identifier, **alert_filter()}))

    @storage_errors
    def alert_page(self, snapshot=None, before=None, after=None):
        query = alert_filter(snapshot, before, after)
        direction = ASCENDING if after is not None else DESCENDING
        rows = list(self.readings.find(query).hint(ALERT_INDEX).sort("_id", direction).limit(ALERT_PAGE_SIZE + 1))
        extra = len(rows) > ALERT_PAGE_SIZE
        rows = rows[:ALERT_PAGE_SIZE]
        if after is not None:
            rows.reverse()
        if snapshot is None:
            snapshot = rows[0]["_id"] if rows else 0
        has_previous = extra if after is not None else False
        has_next = extra if after is None else False
        if rows and before is not None:
            has_previous = next(self.readings.find(alert_filter(snapshot, after=rows[0]["_id"]), {"_id": 1}).hint(ALERT_INDEX).limit(1), None) is not None
        if rows and after is not None:
            has_next = next(self.readings.find(alert_filter(snapshot, before=rows[-1]["_id"]), {"_id": 1}).hint(ALERT_INDEX).limit(1), None) is not None
        return alert_page_result([public_reading(row) for row in rows], snapshot, has_previous=has_previous, has_next=has_next)

    @storage_errors
    def track_points(self, device_id, since):
        query = {**GPS_FILTER, "device_id": device_id, "ts": {"$gte": since}}
        rows = list(self.readings.find(query).hint(DEVICE_LOCATION_INDEX).sort("_id", DESCENDING).limit(1000))
        return [{"id": int(row["_id"]), **{key: row.get(key) for key in ("ts", "lat", "lon", "gps_satellites", "event")}}
                for row in reversed(rows)]
