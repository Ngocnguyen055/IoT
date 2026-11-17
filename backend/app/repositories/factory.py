"""Select storage while keeping SQLite as the default until migration is complete."""

from .errors import DatabaseUnavailable
from .sqlite import SQLiteRepository


def build_repository(settings):
    if settings["DATABASE_BACKEND"] == "sqlite":
        return SQLiteRepository(settings["DB_PATH"])
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
        from .mongodb import MongoDBRepository
    except ImportError:
        raise RuntimeError("MongoDB driver missing; run Cai-dat.cmd") from None
    try:
        client = MongoClient(
            settings["MONGODB_URI"],
            serverSelectionTimeoutMS=settings["MONGODB_TIMEOUT_MS"],
            connectTimeoutMS=settings["MONGODB_TIMEOUT_MS"],
            socketTimeoutMS=10000,
            maxPoolSize=10,
            appname="iot-sos",
        )
    except PyMongoError:
        raise DatabaseUnavailable("configuration") from None
    return MongoDBRepository(client, settings["MONGODB_DATABASE"])
