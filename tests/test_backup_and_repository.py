import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.backup_project import create_backup
from scripts.check_repository import content_problems, forbidden_path


ROOT = Path(__file__).resolve().parents[1]


class BackupTests(unittest.TestCase):
    def test_snapshot_contains_private_config_and_consistent_database(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="backup-tests-", dir=ROOT / ".runtime") as folder:
            root = Path(folder)
            (root / "app.py").write_text("# test source\n", encoding="utf-8")
            (root / "config.local.json").write_text('{"private": "test-only"}', encoding="utf-8")
            (root / ".venv").mkdir()
            (root / ".venv/excluded.txt").write_text("excluded")
            with closing(sqlite3.connect(root / "iot_ngoc.sqlite3")) as db:
                with db:
                    db.execute("CREATE TABLE readings (id INTEGER)")
                    db.execute("INSERT INTO readings VALUES (42)")
            destination, manifest = create_backup(root)
            self.assertTrue(destination.is_relative_to(root / ".runtime/backups"))
            self.assertEqual({f["path"] for f in manifest["files"]}, {"app.py", "config.local.json"})
            self.assertEqual((destination / "files/config.local.json").read_bytes(), (root / "config.local.json").read_bytes())
            self.assertEqual(manifest["database"]["counts"]["readings"], 1)
            with closing(sqlite3.connect(destination / "iot_ngoc.sqlite3")) as db:
                self.assertEqual(db.execute("SELECT id FROM readings").fetchone()[0], 42)
            saved_manifest = json.loads((destination / "manifest.json").read_text())
            for item in saved_manifest["files"]:
                self.assertEqual(hashlib.sha256((destination / "files" / item["path"]).read_bytes()).hexdigest(), item["sha256"])


class RepositoryGuardTests(unittest.TestCase):
    def test_private_paths_are_blocked_and_examples_allowed(self):
        for path in ("config.local.json", ".runtime/backup.txt", ".venv/a.py", "iot_ngoc.sqlite3", "firmware/ESP32_Firmware/device_config.local.h", ".env", "frontend/node_modules/package/index.js"):
            self.assertTrue(forbidden_path(path), path)
        for path in ("config.example.json", ".env.example", "firmware/ESP32_Firmware/device_config.example.h", "app.py"):
            self.assertFalse(forbidden_path(path), path)

    def test_secret_detection_does_not_print_secret(self):
        secret = "private-test-value"
        messages = content_problems("app.py", "key = " + secret, [secret])
        self.assertTrue(messages)
        self.assertNotIn(secret, " ".join(messages))
        self.assertTrue(content_problems("header.h", 'key = "' + "a" * 64 + '";'))
        self.assertEqual(content_problems("example.h", 'key = "REPLACE_WITH_YOUR_DEVICE_KEY";'), [])


if __name__ == "__main__":
    unittest.main()
