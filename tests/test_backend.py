import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import glyphtap_backend as backend


ICON_SET = {
    "prefix": "lucide",
    "width": 24,
    "height": 24,
    "icons": {
        "calendar": {"body": '<path fill="currentColor" d="M2 2h20v20H2z"/>'},
        "house": {"body": '<path fill="currentColor" d="M3 12l9-9 9 9v9H3z"/>'},
    },
    "aliases": {},
}


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"XDG_STATE_HOME": self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    @staticmethod
    def api(endpoint, params=None):
        if endpoint == "/search":
            return {"icons": ["lucide:calendar", "lucide:house"]}
        if endpoint == "/lucide.json":
            return ICON_SET
        if endpoint == "/collections":
            return {
                "lucide": {
                    "name": "Lucide",
                    "license": {"spdx": "ISC"},
                }
            }
        raise AssertionError(endpoint)

    @patch("glyphtap_backend.fetch_json", side_effect=api.__func__)
    def test_search_returns_renderable_icons_and_writes_bounded_cache(self, _fetch):
        args = backend.parser().parse_args(["search", "--query", "calendar", "--color", "#abcdef"])
        response = backend.command_search(args)
        self.assertTrue(response["ok"])
        self.assertTrue(response["online"])
        self.assertEqual([row["id"] for row in response["icons"]], ["lucide:calendar", "lucide:house"])
        encoded = response["icons"][0]["source"].split(",", 1)[1]
        import base64

        svg = base64.b64decode(encoded).decode()
        self.assertIn("#abcdef", svg)
        self.assertIn("viewBox=\"0 0 24 24\"", svg)
        self.assertTrue(backend.icon_cache("lucide:calendar").is_file())

    @patch("glyphtap_backend.fetch_json", side_effect=api.__func__)
    def test_favorites_rank_first_and_recents_survive(self, _fetch):
        backend.save_library(
            {"version": 1, "favorites": ["lucide:house"], "recents": ["lucide:calendar"], "preferred_format": "name"}
        )
        args = backend.parser().parse_args(["search", "--query", "home"])
        response = backend.command_search(args)
        self.assertEqual(response["icons"][0]["id"], "lucide:house")
        self.assertTrue(response["icons"][0]["favorite"])
        self.assertEqual(response["preferred_format"], "name")

    @patch("glyphtap_backend.fetch_json", side_effect=api.__func__)
    def test_offline_exact_query_uses_cache(self, _fetch):
        args = backend.parser().parse_args(["search", "--query", "calendar"])
        backend.command_search(args)
        query_path = backend.query_cache("calendar")
        os.utime(query_path, (0, 0))
        with patch("glyphtap_backend.fetch_json", side_effect=backend.GlyphTapError("offline")):
            response = backend.command_search(args)
        self.assertFalse(response["online"])
        self.assertEqual(response["icons"][0]["id"], "lucide:calendar")

    def test_copy_passes_markup_on_stdin_not_argv(self):
        backend.atomic_json(
            backend.icon_cache("lucide:calendar"),
            {"id": "lucide:calendar", "width": 24, "height": 24, "body": ICON_SET["icons"]["calendar"]["body"]},
        )
        args = backend.parser().parse_args(["copy", "lucide:calendar", "svg"])
        completed = subprocess.CompletedProcess([], 0)
        with patch("glyphtap_backend.subprocess.run", return_value=completed) as run:
            response = backend.command_copy(args)
        self.assertTrue(response["ok"])
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["wl-copy", "--type"])
        self.assertNotIn("<svg", " ".join(command))
        self.assertIn(b"<svg", run.call_args.kwargs["input"])
        self.assertEqual(backend.load_library()["recents"][0], "lucide:calendar")

    def test_invalid_icon_id_is_rejected_before_network_or_filesystem_use(self):
        for value in ("../secret", "mdi:../../secret", "mdi:bad name", "", "mdi:"):
            with self.subTest(value=value), self.assertRaises(backend.GlyphTapError):
                backend.valid_icon_id(value)

    def test_active_or_external_svg_content_is_rejected(self):
        self.assertTrue(backend.safe_svg_body('<path fill="currentColor" d="M0 0h1v1z"/>'))
        for body in (
            '<script>alert(1)</script>',
            '<foreignObject><iframe/></foreignObject>',
            '<path onload="alert(1)"/>',
            '<use href="https://evil.example/icon.svg"/>',
            '<a href="javascript:alert(1)">x</a>',
        ):
            with self.subTest(body=body):
                self.assertFalse(backend.safe_svg_body(body))

    def test_favorite_toggle_is_idempotent_pair(self):
        args = backend.parser().parse_args(["favorite", "lucide:calendar"])
        self.assertTrue(backend.command_favorite(args)["favorite"])
        self.assertFalse(backend.command_favorite(args)["favorite"])
        self.assertEqual(backend.load_library()["favorites"], [])


if __name__ == "__main__":
    unittest.main()
