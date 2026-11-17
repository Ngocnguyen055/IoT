"""Verify the Atlas diagnostic rejects scans and cannot seed application data."""

import io
import importlib.util
import unittest
from unittest.mock import MagicMock, patch

from backend.app.repositories.mongodb import MongoDBRepository
from scripts import check_alert_history as check


@unittest.skipUnless(importlib.util.find_spec("mongomock"), "Install test dependencies first")
class HistoryQueryCheckTests(unittest.TestCase):
    def test_explain_accepts_bounded_index_plan_and_rejects_scan_sort_or_excessive_reads(self):
        database = MagicMock()
        statistics = {"nReturned": 21, "totalKeysExamined": 22, "totalDocsExamined": 21,
                      "executionTimeMillis": 1, "executionStages": {"stage": "FETCH", "inputStage": {"stage": "IXSCAN"}}}
        database.command.return_value = {"executionStats": statistics}
        report = check.explain_query(database, {"event": {"$in": ["button"]}}, "alert_index")
        self.assertEqual(report["keys_examined"], 22)
        command = database.command.call_args.args[0]
        self.assertEqual(command["explain"]["limit"], 21)
        self.assertEqual(command["explain"]["hint"], "alert_index")
        for changes in ({"executionStages": {"stage": "COLLSCAN"}}, {"executionStages": {"stage": "SORT"}},
                        {"totalKeysExamined": 10000}, {"totalDocsExamined": 10000}):
            database.command.return_value = {"executionStats": {**statistics, **changes}}
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                check.explain_query(database, {}, "alert_index")

    def test_fixture_namespace_is_removed_and_application_documents_are_untouched(self):
        import mongomock
        control = mongomock.MongoClient()
        control.application_data.readings.insert_one({"_id": 50, "event": "button", "existing": True})
        before = list(control.application_data.readings.find())
        fake_plan = {"returned": 1, "keys_examined": 1, "documents_examined": 1, "execution_ms": 0}
        settings = {"MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "application_data", "MONGODB_TIMEOUT_MS": 5000}
        with patch.object(check, "MongoClient", return_value=control), \
             patch.object(control.admin, "command", return_value={"ok": 1, "setName": "mock"}), \
             patch.object(check, "initialize_database", side_effect=lambda repo: repo._initialize_storage()), \
             patch.object(MongoDBRepository, "_with_transaction", lambda self, operation: operation(None)), \
             patch.object(check, "explain_query", return_value=fake_plan):
            report = check.run_checks(settings, io.StringIO(), telemetry_count=100)
        self.assertTrue(report["ok"])
        self.assertTrue(report["temporary_database_removed"])
        self.assertEqual(list(control.application_data.readings.find()), before)
        self.assertEqual(control.list_database_names(), ["application_data"])

    def test_failed_verification_also_removes_temporary_collections(self):
        import mongomock
        control = mongomock.MongoClient()
        settings = {"MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "application_data", "MONGODB_TIMEOUT_MS": 5000}
        def fail_after_creation(repository):
            repository.database.readings.insert_one({"_id": 1})
            raise ValueError("intentional failure")
        with patch.object(check, "MongoClient", return_value=control), \
             patch.object(control.admin, "command", return_value={"ok": 1}), \
             patch.object(check, "initialize_database", side_effect=fail_after_creation):
            with self.assertRaisesRegex(ValueError, "intentional failure"):
                check.run_checks(settings, io.StringIO(), telemetry_count=100)
        self.assertEqual(control.list_database_names(), [])


if __name__ == "__main__":
    unittest.main()
