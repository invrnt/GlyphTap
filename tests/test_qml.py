from pathlib import Path
import unittest


class QmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("GlyphTap.qml").read_text(encoding="utf-8")

    def test_overlay_lifecycle_and_host_hide_are_present(self):
        self.assertIn("function open(payloadJson)", self.source)
        self.assertIn("function close()", self.source)
        self.assertIn('root.shell.hide((root.manifest && root.manifest.id)', self.source)
        self.assertIn("WlrKeyboardFocus.Exclusive", self.source)

    def test_keyboard_first_contract(self):
        for key in ("Qt.Key_Escape", "Qt.Key_Left", "Qt.Key_Right", "Qt.Key_Up", "Qt.Key_Down", "Qt.Key_Return", "Qt.Key_Space", "Qt.Key_D"):
            self.assertIn(key, self.source)
        self.assertIn("root.activateIndex(root.selectedIndex, control)", self.source)

    def test_backend_never_receives_svg_in_argv(self):
        self.assertIn('["python3", root.backendPath, "copy", row.iconId, root.outputFormat]', self.source)
        self.assertNotIn('"bash", "-c"', self.source)


if __name__ == "__main__":
    unittest.main()
