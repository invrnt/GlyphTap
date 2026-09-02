import QtQuick
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.invrnt.glyphtap"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    labelVisible: false
    hasVisualContent: true
    fixedWidth: root.vertical ? root.barSize : Style.bar.iconSlot
    fixedHeight: root.vertical ? Style.bar.iconSlot : root.barSize
    tooltipText: "GlyphTap · Search and copy icons"

    onPressed: function(pressedButton) {
      if (pressedButton !== Qt.LeftButton || !root.bar) return
      root.bar.run("omarchy-shell shell toggle io.github.invrnt.glyphtap")
    }

    GlyphTapMark {
      anchors.centerIn: parent
      width: Style.space(18)
      height: width
      color: button.foreground
    }
  }
}
