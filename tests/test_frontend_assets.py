"""Verify rendered templates and every local module import are served correctly."""

from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit

from backend.app import create_app


ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        self.elements.append((tag, dict(attributes)))


class FrontendAssetTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="asset-tests-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.app = create_app({"TESTING": True, "ADMIN_PASSWORD": "assets-test-admin", "DEVICE_KEY": "assets-test-device", "SESSION_SECRET": "assets-test-session", "DB_PATH": Path(self.temporary.name) / "assets.sqlite3"})
        self.client = self.app.test_client()

    def test_login_and_dashboard_share_styles_and_keep_required_controls(self):
        login = Page(self.client.get("/login").get_data(as_text=True))
        self.assertTrue(any(tag == "input" and attrs.get("name") == "password" for tag, attrs in login.elements))
        self.client.post("/login", data={"password": "assets-test-admin"})
        dashboard = Page(self.client.get("/").get_data(as_text=True))
        ids = [attrs["id"] for _, attrs in dashboard.elements if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"bpm", "spo2", "battery", "voltage", "map", "locate", "alerts", "trackHours", "showTrack", "followGps", "copyCoords", "googleMaps"}.issubset(ids))
        self.assertTrue(any(tag == "form" and attrs.get("action") == "/logout" and attrs.get("method") == "post" for tag, attrs in dashboard.elements))
        for page in (login, dashboard):
            styles = [attrs["href"] for tag, attrs in page.elements if tag == "link" and attrs.get("href", "").startswith("/static/")]
            self.assertEqual(styles, ["/static/css/style.css"])
            response = self.client.get(styles[0])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "text/css")
            response.close()
        selected = [attrs.get("value") for tag, attrs in dashboard.elements if tag == "option" and "selected" in attrs]
        self.assertEqual(selected, ["24"])

    def test_every_local_es_module_import_has_a_javascript_response(self):
        self.client.post("/login", data={"password": "assets-test-admin"})
        page = Page(self.client.get("/").get_data(as_text=True))
        entry = [attrs["src"] for tag, attrs in page.elements if tag == "script" and attrs.get("type") == "module"]
        self.assertEqual(entry, ["/static/js/app.js"])
        visited, pending = set(), list(entry)
        while pending:
            path = pending.pop()
            if path in visited:
                continue
            visited.add(path)
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(response.mimetype, {"text/javascript", "application/javascript"}, path)
            source = response.get_data(as_text=True)
            response.close()
            for target in re.findall(r"\bfrom\s+['\"]([^'\"]+)['\"]", source):
                resolved = urljoin(path, target)
                self.assertFalse(urlsplit(resolved).netloc)
                self.assertTrue(resolved.startswith("/static/js/"), resolved)
                pending.append(resolved)
        self.assertEqual(len(visited), 9)

    def test_original_asset_urls_remain_compatible(self):
        response = self.client.get("/static/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("import('./js/app.js')", response.get_data(as_text=True))
        response.close()
        response = self.client.get("/static/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("css/style.css", response.get_data(as_text=True))
        response.close()


if __name__ == "__main__":
    unittest.main()
