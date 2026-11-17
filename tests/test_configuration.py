import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import connect_device
import project_config


ROOT = Path(__file__).resolve().parents[1]
VALUES = {"ADMIN_PASSWORD": "local-test-admin", "DEVICE_KEY": "local-test-device", "SESSION_SECRET": "local-test-session"}


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="config-tests-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "config.local.json"
        self.config_patch = patch.object(project_config, "CONFIG_PATH", self.path)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)

    def test_first_run_generates_and_preserves_independent_credentials(self):
        first = project_config.load_config()
        contents = self.path.read_bytes()
        self.assertEqual(project_config.load_config(), first)
        self.assertEqual(self.path.read_bytes(), contents)
        self.assertEqual(set(first), set(project_config.REQUIRED_KEYS))
        self.assertNotEqual(first["DEVICE_KEY"], first["SESSION_SECRET"])
        self.assertEqual(len(first["DEVICE_KEY"]), 64)

    def test_existing_utf8_bom_configuration_is_preserved(self):
        self.path.write_text(json.dumps(VALUES), encoding="utf-8-sig")
        contents = self.path.read_bytes()
        self.assertEqual(project_config.load_config(), VALUES)
        self.assertEqual(self.path.read_bytes(), contents)

    def test_invalid_configuration_is_rejected_without_replacement(self):
        for config in (None, [], {}, {**VALUES, "DEVICE_KEY": ""}, {**VALUES, "ADMIN_PASSWORD": " "}, {**VALUES, "SESSION_SECRET": 7}):
            with self.subTest(config=config):
                self.path.write_text(json.dumps(config), encoding="utf-8")
                contents = self.path.read_bytes()
                with self.assertRaises(ValueError):
                    project_config.load_config()
                self.assertEqual(self.path.read_bytes(), contents)

    def test_complete_environment_does_not_create_local_config(self):
        with patch.dict(os.environ, VALUES, clear=True):
            self.assertEqual(project_config.application_config(), VALUES)
        self.assertFalse(self.path.exists())

    def test_partial_environment_overrides_local_values(self):
        self.path.write_text(json.dumps(VALUES), encoding="utf-8")
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "environment-test-admin"}, clear=True):
            self.assertEqual(project_config.application_config(), {**VALUES, "ADMIN_PASSWORD": "environment-test-admin"})


class FirmwareConfigurationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="header-tests-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.sketch = self.directory / "ESP32_Firmware.ino"
        self.sketch.write_text("// unchanged test sketch\n", encoding="utf-8")
        self.header = self.directory / "device_config.local.h"
        for name, value in (("FIRMWARE", self.sketch), ("FIRMWARE_CONFIG", self.header)):
            item = patch.object(connect_device, name, value)
            item.start()
            self.addCleanup(item.stop)

    def prepare(self, url, config=None):
        with patch.object(connect_device, "load_config", return_value=config or VALUES), contextlib.redirect_stdout(io.StringIO()):
            connect_device.prepare_firmware(url)

    def test_only_local_header_is_generated_with_matching_values(self):
        self.prepare("  https://test-tunnel.trycloudflare.com/  ")
        content = self.header.read_text(encoding="utf-8")
        self.assertIn(json.dumps(VALUES["DEVICE_KEY"]), content)
        self.assertIn('"https://test-tunnel.trycloudflare.com"', content)
        self.assertIn('"ngoc-01"', content)
        self.assertEqual(self.sketch.read_text(encoding="utf-8"), "// unchanged test sketch\n")
        self.prepare("https://new-tunnel.trycloudflare.com")
        self.assertNotIn("test-tunnel", self.header.read_text(encoding="utf-8"))

    def test_key_and_device_strings_are_escaped_for_cpp(self):
        key = 'test-quote-"-and-backslash-\\'
        self.prepare("https://test.trycloudflare.com", {**VALUES, "DEVICE_KEY": key, "DEVICE_ID": "test-device"})
        line = next(line for line in self.header.read_text().splitlines() if "DEVICE_KEY" in line)
        self.assertEqual(json.loads(line.split(" = ", 1)[1][:-1]), key)

    def test_bad_url_keeps_existing_header(self):
        self.prepare("https://test.trycloudflare.com")
        contents = self.header.read_bytes()
        for url in ("http://test.com", "https://test.com /api", "https://user:pass@test.com", "https://test.com?query=1", "https://test.com#frag", "https://test.com\\api"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.prepare(url)
            self.assertEqual(self.header.read_bytes(), contents)


if __name__ == "__main__":
    unittest.main()
