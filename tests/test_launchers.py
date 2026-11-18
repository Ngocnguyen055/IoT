"""Verify entry points wire the real factory to isolated credentials and storage."""

import contextlib
import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from flask import Flask

from backend.app import create_app
import run_local


ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = {"ADMIN_PASSWORD": "launcher-test-admin", "DEVICE_KEY": "launcher-test-device", "SESSION_SECRET": "launcher-test-session"}


class LauncherTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="launcher-tests-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def test_local_launcher_passes_saved_configuration_to_the_factory(self):
        original_directory = Path.cwd()
        try:
            with (patch.object(run_local, "ROOT", self.directory),
                  patch.object(run_local, "application_config", return_value=CREDENTIALS),
                  patch("sys.argv", ["run_local.py", "--no-browser"]),
                  patch.object(run_local.urllib.request, "urlopen", side_effect=URLError("test: no running server")),
                  patch.object(run_local.webbrowser, "open") as browser,
                  patch.object(Flask, "run", autospec=True) as serve,
                  contextlib.redirect_stdout(io.StringIO())):
                run_local.main()
                app = serve.call_args.args[0]
                self.assertEqual(app.config["DB_PATH"], str(self.directory / "iot_ngoc.sqlite3"))
                self.assertEqual(app.config["DEVICE_KEY"], CREDENTIALS["DEVICE_KEY"])
                self.assertEqual(serve.call_args.kwargs, {"host": "127.0.0.1", "port": 5000, "debug": False})
                self.assertEqual(app.test_client().post("/login", data={"password": CREDENTIALS["ADMIN_PASSWORD"]}).status_code, 302)
                browser.assert_not_called()
        finally:
            os.chdir(original_directory)

    def test_legacy_python_entry_point_uses_the_same_factory(self):
        with (patch.dict(os.environ, {**CREDENTIALS, "DB_PATH": str(self.directory / "legacy.sqlite3")}),
              patch.object(Flask, "run", autospec=True) as serve):
            entry = runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
        app = entry["app"]
        self.assertIs(serve.call_args.args[0], app)
        self.assertEqual(serve.call_args.kwargs, {"host": "127.0.0.1", "port": 5000, "debug": False})
        self.assertEqual(app.config["DB_PATH"], str(self.directory / "legacy.sqlite3"))
        self.assertEqual(app.test_client().get("/login").status_code, 200)

    def test_local_launcher_recognizes_rebranded_and_legacy_running_websites(self):
        app = create_app({**CREDENTIALS, "TESTING": True, "DB_PATH": self.directory / "running.sqlite3"})
        current_login = app.test_client().get("/login").get_data()
        original_directory = Path.cwd()
        try:
            for page, should_start in ((current_login, False), ("<h1>IOT - Ngọc</h1>".encode("utf-8"), False), (b"<h1>Another application</h1>", True)):
                with (self.subTest(page=page[:80]),
                      patch.object(run_local, "ROOT", self.directory),
                      patch.object(run_local, "application_config", return_value=CREDENTIALS),
                      patch("sys.argv", ["run_local.py", "--no-browser"]),
                      patch.object(run_local.urllib.request, "urlopen", return_value=io.BytesIO(page)),
                      patch.object(run_local.webbrowser, "open") as browser,
                      patch.object(Flask, "run", autospec=True) as serve,
                      contextlib.redirect_stdout(io.StringIO())):
                    run_local.main()
                    self.assertEqual(serve.called, should_start)
                    browser.assert_not_called()
        finally:
            os.chdir(original_directory)


if __name__ == "__main__":
    unittest.main()
