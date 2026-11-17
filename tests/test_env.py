"""Dotenv precedence, literal credentials and backward compatibility."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app.config import build_config
from env_config import read_env, update_env, write_env
import project_config
from scripts.configure_env import configure


ROOT = Path(__file__).resolve().parents[1]
VALUES = {"ADMIN_PASSWORD": "env-test-admin", "DEVICE_KEY": "env-test-device", "SESSION_SECRET": "env-test-session"}


class EnvTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="env-test-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.json_path = self.root / "config.local.json"
        self.env_path = self.root / ".env"
        self.json_path.write_text(json.dumps({**VALUES, "DATABASE_BACKEND": "sqlite"}), encoding="utf-8")
        for patcher in (patch.object(project_config, "CONFIG_PATH", self.json_path), patch.dict(os.environ, {}, clear=True)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_explicit_config_then_process_then_dotenv_then_json_precedence(self):
        write_env(self.env_path, {"ADMIN_PASSWORD": "dotenv-admin"})
        self.assertEqual(project_config.application_config()["ADMIN_PASSWORD"], "dotenv-admin")
        self.assertEqual(project_config.application_config()["DEVICE_KEY"], VALUES["DEVICE_KEY"])
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "process-admin"}):
            self.assertEqual(project_config.application_config()["ADMIN_PASSWORD"], "process-admin")
            self.assertEqual(build_config({"ADMIN_PASSWORD": "explicit-admin"})["ADMIN_PASSWORD"], "explicit-admin")

    def test_quoted_values_are_literal_and_reading_never_changes_process_environment(self):
        values = {**VALUES, "ADMIN_PASSWORD": 'quote" slash\\ # equals= ${UNSET} tiếng Việt\nsecond line'}
        write_env(self.env_path, values)
        before = dict(os.environ)
        self.assertEqual(read_env(self.env_path), values)
        self.assertEqual(project_config.application_config()["ADMIN_PASSWORD"], values["ADMIN_PASSWORD"])
        self.assertEqual(dict(os.environ), before)

    def test_dotenv_can_run_without_legacy_json_and_complete_environment_is_isolated(self):
        self.json_path.unlink()
        write_env(self.env_path, {**VALUES, "DATABASE_BACKEND": "sqlite"})
        self.assertEqual(project_config.application_config()["DEVICE_KEY"], VALUES["DEVICE_KEY"])
        self.assertFalse(self.json_path.exists())
        with patch.dict(os.environ, VALUES):
            self.assertEqual(project_config.application_config(), VALUES)

    def test_updates_preserve_other_values_and_detect_concurrent_edits(self):
        write_env(self.env_path, {**VALUES, "CUSTOM": "keep"})
        original = self.env_path.read_bytes()
        update_env(self.env_path, {"DATABASE_BACKEND": "mongodb"})
        self.assertEqual(read_env(self.env_path)["CUSTOM"], "keep")
        with self.assertRaises(ValueError):
            update_env(self.env_path, {"CUSTOM": "lost"}, expected=original)
        self.assertEqual(read_env(self.env_path)["CUSTOM"], "keep")

    def test_conversion_preserves_credentials_database_and_existing_json(self):
        original = self.json_path.read_bytes()
        mongo = {"MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "selected_database", "MONGODB_TIMEOUT_MS": 5000}
        (self.root / "mongodb.local.json").write_text(json.dumps(mongo), encoding="utf-8")
        result = configure(self.root)
        values = read_env(self.env_path)
        self.assertTrue(result["created"])
        self.assertEqual({key: values[key] for key in VALUES}, VALUES)
        self.assertEqual(values["MONGODB_DATABASE"], "selected_database")
        self.assertEqual(self.json_path.read_bytes(), original)
        before = self.env_path.read_bytes()
        self.assertFalse(configure(self.root)["created"])
        self.assertEqual(before, self.env_path.read_bytes())
