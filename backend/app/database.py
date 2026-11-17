"""Explicit collection/index/schema setup, separate from normal application startup."""

from .models import COLLECTION_MODELS
from .repositories.indexes import verify_reading_indexes


def collection_options(database):
    return {row["name"]: row.get("options", {}) for row in database.list_collections()
            if row["name"] in COLLECTION_MODELS}


def initialize_database(repository, *, check_only=False):
    database = repository.database
    existing = collection_options(database)
    desired = {name: {"$jsonSchema": model.json_schema()} for name, model in COLLECTION_MODELS.items()}
    # Validate every existing collection before changing any metadata.
    for name, model in COLLECTION_MODELS.items():
        options = existing.get(name)
        if options is None:
            if check_only:
                raise ValueError(f"Missing collection: {name}")
            continue
        for document in database[name].find():
            try:
                model.from_document(document, strict=True)
            except (ValueError, TypeError, KeyError):
                raise ValueError(f"Existing {name} documents do not match the model; data was not rewritten") from None
        validator = options.get("validator", {})
        if validator and validator != desired[name]:
            raise ValueError(f"Collection {name} has a different validator; use an explicit schema migration")
        if check_only and (validator != desired[name] or options.get("validationLevel", "strict") != "strict"
                           or options.get("validationAction", "error") != "error"):
            raise ValueError(f"Collection {name} does not have the expected strict validator")
    if not check_only:
        for name, validator in desired.items():
            options = existing.get(name)
            if options is None:
                database.create_collection(name, validator=validator, validationLevel="strict", validationAction="error")
            elif (options.get("validator") != validator or options.get("validationLevel", "strict") != "strict"
                  or options.get("validationAction", "error") != "error"):
                database.command({"collMod": name, "validator": validator, "validationLevel": "strict", "validationAction": "error"})
        repository._initialize_storage()
    else:
        verify_reading_indexes(repository.readings)
    counter = repository.counters.find_one({"_id": "readings"})
    latest = repository.readings.find_one({}, {"_id": 1}, sort=[("_id", -1)])
    if counter is None or counter["value"] < (latest["_id"] if latest else 0):
        raise ValueError("MongoDB counter must be at least the maximum reading ID")
    return {"ok": True, "database": repository.database_name, "check_only": check_only,
            "collections": list(COLLECTION_MODELS), "counts": {name: database[name].count_documents({}) for name in COLLECTION_MODELS},
            "counter": counter["value"]}
