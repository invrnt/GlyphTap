import json
from pathlib import Path
import unittest


class QmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("GlyphTap.qml").read_text(encoding="utf-8")
        cls.bar_widget = Path("GlyphTapBar.qml").read_text(encoding="utf-8")
        cls.search_glyph = Path("SearchGlyph.qml").read_text(encoding="utf-8")
        cls.bar_glyph = Path("GlyphTapMark.qml").read_text(encoding="utf-8")
        cls.manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))

    def test_overlay_lifecycle_and_host_hide_are_present(self):
        self.assertIn("function open(payloadJson)", self.source)
        self.assertIn("function close()", self.source)
        self.assertIn('root.shell.hide((root.manifest && root.manifest.id)', self.source)
        self.assertIn("WlrKeyboardFocus.Exclusive", self.source)

    def test_keyboard_first_contract(self):
        for key in ("Qt.Key_Escape", "Qt.Key_Left", "Qt.Key_Right", "Qt.Key_Up", "Qt.Key_Down", "Qt.Key_Return", "Qt.Key_Space", "Qt.Key_D"):
            self.assertIn(key, self.source)
        self.assertIn("root.activateIndex(root.selectedIndex, control)", self.source)

    def test_vertical_navigation_uses_the_rendered_grid_columns(self):
        self.assertIn("delta * root.gridColumns", self.source)
        self.assertIn("Math.floor(resultGrid.width / gridColumns)", self.source)
        self.assertIn("cellWidth: root.cellWidth", self.source)
        self.assertNotIn("cellWidth: root.cellWidth +", self.source)
        self.assertIn("if (next < 0 || next >= displayModel.count) return", self.source)

    def test_svg_previews_request_high_resolution_rasterization(self):
        self.assertGreaterEqual(self.source.count("sourceSize.width:"), 2)
        self.assertGreaterEqual(self.source.count("sourceSize.height:"), 2)
        self.assertNotIn('source: Qt.resolvedUrl("assets/icon.png")', self.source)

    def test_shared_search_mark_uses_the_supplied_vector_path(self):
        self.assertIn("import QtQuick.Shapes", self.search_glyph)
        self.assertIn('path: "m19.6 21-6.3-6.3', self.search_glyph)
        self.assertIn("SearchGlyph {", self.source)
        self.assertIn("GlyphTapMark {", self.bar_widget)
        self.assertNotIn("id: brandIcon", self.source)
        self.assertNotIn('text: "G"', self.bar_widget)

    def test_search_has_an_explicit_animated_loading_state(self):
        self.assertIn('text: "Searching…"', self.source)
        self.assertIn("SequentialAnimation on scale", self.source)
        self.assertIn("SequentialAnimation on x", self.source)
        self.assertIn("visible: root.loading", self.source)

    def test_bar_mark_uses_the_supplied_circle_square_and_triangle(self):
        self.assertIn("import QtQuick.Shapes", self.bar_glyph)
        self.assertIn("M42.5 34.376a8.119", self.bar_glyph)
        self.assertIn("M29.456 6.459h9.85", self.bar_glyph)
        self.assertIn("m12.325 27.686-6.553 11.35", self.bar_glyph)
        self.assertGreaterEqual(self.bar_glyph.count("ShapePath {"), 3)

    def test_backend_never_receives_svg_in_argv(self):
        self.assertIn('["python3", root.backendPath, "copy", row.iconId, root.outputFormat]', self.source)
        self.assertNotIn('"bash", "-c"', self.source)

    def test_bar_launcher_is_declared_and_opens_the_overlay(self):
        self.assertIn("bar-widget", self.manifest["kinds"])
        self.assertEqual(self.manifest["entryPoints"]["barWidget"], "GlyphTapBar.qml")
        self.assertEqual(self.manifest["barWidget"]["defaultSection"], "right")
        self.assertIn("BarWidget {", self.bar_widget)
        self.assertIn(
            'root.bar.run("omarchy-shell shell toggle io.github.invrnt.glyphtap")',
            self.bar_widget,
        )


if __name__ == "__main__":
    unittest.main()
