import tempfile
import unittest
from pathlib import Path

from scripts.configure import (
    ConfigError,
    install_binding,
    install_menu,
    remove_marked,
    remove_menu,
    BINDING_START,
    BINDING_END,
)


class ConfigureTests(unittest.TestCase):
    def test_binding_install_is_idempotent(self):
        original = "-- Personal bindings\n"
        once = install_binding(original, False)
        twice = install_binding(once, False)
        self.assertEqual(once, twice)
        self.assertEqual(remove_marked(once, BINDING_START, BINDING_END), original)

    def test_binding_conflict_requires_force(self):
        with self.assertRaisesRegex(ConfigError, "already mentioned"):
            install_binding('o.bind("SUPER + I", "Other", "other")\n', False)

    def test_menu_round_trip_preserves_comment_only_template(self):
        original = "{\n  // Keep my notes.\n}\n"
        installed = install_menu(original)
        self.assertIn('"glyphtap"', installed)
        self.assertEqual(remove_menu(installed), original)

    def test_menu_round_trip_preserves_existing_entries(self):
        original = '{\n  "personal": {"label":"Personal"}\n}\n'
        installed = install_menu(original)
        self.assertIn("Personal", installed)
        self.assertEqual(remove_menu(installed), original)

    def test_existing_unmanaged_menu_entry_is_refused(self):
        with self.assertRaisesRegex(ConfigError, "non-managed"):
            install_menu('{"glyphtap":{"label":"Mine"}}\n')


if __name__ == "__main__":
    unittest.main()
