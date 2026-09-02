import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import qs.Commons
import qs.Ui

Item {
  id: root

  property var shell: null
  property var manifest: null
  property bool opened: false
  property string filterText: ""
  property int selectedIndex: 0
  property bool gridFocused: false
  property bool previewOpen: false
  property bool formatMenuOpen: false
  property bool loading: false
  property bool online: true
  property string statusMessage: ""
  property string outputFormat: "svg"
  property int searchSerial: 0
  property int queuedSerial: 0
  property string queuedQuery: ""
  property bool copyShouldClose: true
  property int copiedThisSession: 0
  property string backendPath: decodeURIComponent(String(Qt.resolvedUrl("glyphtap_backend.py")).replace(/^file:\/\//, ""))
  property var formats: [
    { value: "svg", label: "SVG" },
    { value: "name", label: "Iconify name" },
    { value: "jsx", label: "JSX" },
    { value: "react", label: "React" },
    { value: "vue", label: "Vue" },
    { value: "html", label: "HTML" },
    { value: "css", label: "CSS" },
    { value: "data-uri", label: "Data URI" }
  ]

  property color background: Color.menu.background
  property color foreground: Color.menu.text
  property color borderColor: Color.menu.border
  property color scrim: Color.menu.scrim
  property color selectedBackground: Color.menu.selectedBackground
  property color selectedText: Color.menu.selectedText
  property color accent: Color.accent
  property var borderSpec: Border.surfaceSpec("menu", "border", borderColor, Math.max(1, Style.space(2)))
  readonly property int cornerRadius: Style.cornerRadius
  property string fontFamily: Style.font.menuFamily
  property int cardWidth: Math.min(Style.space(1040), panel.width - Style.gapsOut * 2)
  property int cardHeight: Math.min(Style.space(710), panel.height - Style.gapsOut * 2)
  property int cardPadding: Style.spacing.panelPadding
  property int gridColumns: Math.max(4, Math.floor((cardWidth - cardPadding * 2) / Style.space(142)))
  property int cellWidth: Math.floor((cardWidth - cardPadding * 2 - Style.spacing.md * (gridColumns - 1)) / gridColumns)
  property int cellHeight: Style.space(112)

  function open(payloadJson) {
    root.opened = true
    root.filterText = ""
    root.selectedIndex = 0
    root.gridFocused = false
    root.previewOpen = false
    root.formatMenuOpen = false
    root.statusMessage = ""
    root.copiedThisSession = 0
    root.queueSearch("")
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  function close() {
    root.previewOpen = false
    root.formatMenuOpen = false
    root.opened = false
  }

  function dismiss() {
    root.close()
    if (root.shell && typeof root.shell.hide === "function")
      root.shell.hide((root.manifest && root.manifest.id) || "io.github.invrnt.glyphtap")
  }

  function toggle() {
    if (root.opened) root.dismiss()
    else root.open("{}")
  }

  function themeHex() {
    var value = String(root.foreground)
    if (/^#[0-9a-fA-F]{8}$/.test(value)) return "#" + value.slice(3)
    if (/^#[0-9a-fA-F]{6}$/.test(value)) return value
    return "#f5f5f5"
  }

  function queueSearch(query) {
    root.filterText = query.slice(0, 100)
    root.gridFocused = false
    searchDebounce.restart()
  }

  function launchSearch(query) {
    root.searchSerial += 1
    var serial = root.searchSerial
    if (searchProc.running) {
      root.queuedSerial = serial
      root.queuedQuery = query
      return
    }
    root.loading = true
    searchProc.activeSerial = serial
    searchProc.command = ["python3", root.backendPath, "search", "--query", query, "--color", root.themeHex(), "--limit", "72"]
    searchProc.running = true
  }

  function applySearch(raw, serial) {
    if (serial !== root.searchSerial) return
    var response
    try {
      response = JSON.parse(raw || "{}")
    } catch (error) {
      root.statusMessage = "Could not read Iconify results"
      return
    }
    if (response.ok !== true) {
      root.statusMessage = String(response.message || "Search failed")
      return
    }
    root.online = response.online !== false
    root.statusMessage = response.online === false ? "Offline cache" : ""
    if (response.preferred_format && root.formats.some(function(item) { return item.value === response.preferred_format }))
      root.outputFormat = response.preferred_format
    displayModel.clear()
    var icons = response.icons || []
    for (var i = 0; i < icons.length; i++) {
      var icon = icons[i]
      displayModel.append({
        iconId: String(icon.id || ""),
        iconName: String(icon.name || ""),
        collection: String(icon.collection || icon.prefix || ""),
        licenseName: String(icon.license || ""),
        dimensions: String(icon.width || 16) + " × " + String(icon.height || 16),
        favorite: icon.favorite === true,
        sourceUrl: String(icon.source || "")
      })
    }
    root.selectedIndex = displayModel.count > 0 ? 0 : -1
    Qt.callLater(function() {
      if (displayModel.count > 0) resultGrid.positionViewAtIndex(root.selectedIndex, GridView.Beginning)
    })
  }

  function select(delta) {
    if (displayModel.count === 0) return
    root.gridFocused = true
    root.previewOpen = false
    root.formatMenuOpen = false
    root.selectedIndex = (root.selectedIndex + delta + displayModel.count) % displayModel.count
    resultGrid.positionViewAtIndex(root.selectedIndex, GridView.Contain)
  }

  function selectRow(delta) {
    if (displayModel.count === 0) return
    root.gridFocused = true
    root.previewOpen = false
    root.formatMenuOpen = false
    var next = root.selectedIndex + delta * root.gridColumns
    root.selectedIndex = Math.max(0, Math.min(next, displayModel.count - 1))
    resultGrid.positionViewAtIndex(root.selectedIndex, GridView.Contain)
  }

  function currentRow() {
    return root.selectedIndex >= 0 && root.selectedIndex < displayModel.count ? displayModel.get(root.selectedIndex) : null
  }

  function activateIndex(index, keepOpen) {
    if (index < 0 || index >= displayModel.count || copyProc.running) return
    root.selectedIndex = index
    var row = displayModel.get(index)
    root.copyShouldClose = keepOpen !== true
    root.formatMenuOpen = false
    copyProc.command = ["python3", root.backendPath, "copy", row.iconId, root.outputFormat]
    copyProc.running = true
  }

  function saveIndex(index) {
    if (index < 0 || index >= displayModel.count || actionProc.running) return
    var row = displayModel.get(index)
    actionProc.actionName = "save"
    actionProc.command = ["python3", root.backendPath, "save", row.iconId]
    actionProc.running = true
  }

  function favoriteIndex(index) {
    if (index < 0 || index >= displayModel.count || actionProc.running) return
    var row = displayModel.get(index)
    actionProc.actionName = "favorite"
    actionProc.actionIndex = index
    actionProc.command = ["python3", root.backendPath, "favorite", row.iconId]
    actionProc.running = true
  }

  function parseAction(raw, action, index) {
    var response
    try { response = JSON.parse(raw || "{}") }
    catch (error) { response = { ok: false, message: "GlyphTap action failed" } }
    root.statusMessage = String(response.message || "")
    if (response.ok === true && action === "favorite" && index >= 0 && index < displayModel.count)
      displayModel.setProperty(index, "favorite", response.favorite === true)
    statusTimer.restart()
  }

  function cycleFormat(delta) {
    var index = 0
    for (var i = 0; i < root.formats.length; i++) {
      if (root.formats[i].value === root.outputFormat) { index = i; break }
    }
    index = (index + delta + root.formats.length) % root.formats.length
    root.outputFormat = root.formats[index].value
    root.statusMessage = "Copy format · " + root.formats[index].label
    statusTimer.restart()
  }

  function formatLabel(value) {
    for (var i = 0; i < root.formats.length; i++)
      if (root.formats[i].value === value) return root.formats[i].label
    return "SVG"
  }

  function editFilter(event) {
    if (event.key === Qt.Key_Backspace) {
      if (root.filterText.length > 0) root.queueSearch(root.filterText.slice(0, -1))
      return true
    }
    if (event.key === Qt.Key_Delete && root.filterText.length > 0) {
      root.queueSearch("")
      return true
    }
    if (event.text && event.text.length === 1 && event.text.charCodeAt(0) >= 32 && event.text.charCodeAt(0) !== 127) {
      root.queueSearch(root.filterText + event.text)
      return true
    }
    return false
  }

  ListModel { id: displayModel }

  Timer {
    id: searchDebounce
    interval: 170
    onTriggered: root.launchSearch(root.filterText)
  }

  Timer {
    id: statusTimer
    interval: 1700
    onTriggered: root.statusMessage = ""
  }

  Timer {
    id: closeTimer
    interval: 520
    onTriggered: root.dismiss()
  }

  Process {
    id: searchProc
    property int activeSerial: 0
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applySearch(String(text || ""), searchProc.activeSerial)
    }
    onExited: {
      root.loading = false
      if (root.queuedSerial > activeSerial) {
        var nextQuery = root.queuedQuery
        root.queuedSerial = 0
        root.queuedQuery = ""
        root.launchSearch(nextQuery)
      }
    }
  }

  Process {
    id: copyProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var response
        try { response = JSON.parse(String(text || "{}")) }
        catch (error) { response = { ok: false, message: "Copy failed" } }
        root.statusMessage = String(response.message || "")
        if (response.ok === true) {
          root.copiedThisSession += 1
          if (root.copyShouldClose) closeTimer.restart()
          else statusTimer.restart()
        } else statusTimer.restart()
      }
    }
  }

  Process {
    id: actionProc
    property string actionName: ""
    property int actionIndex: -1
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.parseAction(String(text || ""), actionProc.actionName, actionProc.actionIndex)
    }
  }

  PanelWindow {
    id: panel
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    WlrLayershell.namespace: "glyphtap"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    exclusionMode: ExclusionMode.Ignore

    Rectangle { anchors.fill: parent; color: root.scrim }
    MouseArea { anchors.fill: parent; onClicked: root.dismiss() }

    BorderSurface {
      id: card
      width: root.cardWidth
      height: root.cardHeight
      anchors.centerIn: parent
      radius: root.cornerRadius
      color: root.background
      borderSpec: root.borderSpec
      padding: root.cardPadding

      MouseArea { anchors.fill: parent; onClicked: {} }

      Item {
        id: keyCatcher
        anchors.fill: parent
        focus: true
        Keys.priority: Keys.BeforeItem
        Keys.onPressed: function(event) {
          var control = (event.modifiers & Qt.ControlModifier) !== 0
          if (event.key === Qt.Key_Escape) {
            if (root.formatMenuOpen) root.formatMenuOpen = false
            else if (root.previewOpen) root.previewOpen = false
            else if (root.filterText) root.queueSearch("")
            else root.dismiss()
            event.accepted = true
          } else if (control && event.key === Qt.Key_D) {
            root.favoriteIndex(root.selectedIndex)
            event.accepted = true
          } else if (control && event.key === Qt.Key_S) {
            root.saveIndex(root.selectedIndex)
            event.accepted = true
          } else if (control && event.key === Qt.Key_F) {
            root.cycleFormat(1)
            event.accepted = true
          } else if (event.key === Qt.Key_Left) {
            root.select(-1); event.accepted = true
          } else if (event.key === Qt.Key_Right) {
            root.select(1); event.accepted = true
          } else if (event.key === Qt.Key_Up) {
            root.selectRow(-1); event.accepted = true
          } else if (event.key === Qt.Key_Down) {
            root.selectRow(1); event.accepted = true
          } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            root.activateIndex(root.selectedIndex, control)
            event.accepted = true
          } else if (event.key === Qt.Key_Space && root.gridFocused) {
            root.previewOpen = !root.previewOpen
            root.formatMenuOpen = false
            event.accepted = true
          } else if (!control && root.editFilter(event)) {
            root.previewOpen = false
            root.formatMenuOpen = false
            event.accepted = true
          }
        }
      }

      Column {
        anchors.fill: parent
        anchors.topMargin: card.contentTopInset
        anchors.rightMargin: card.contentRightInset
        anchors.bottomMargin: card.contentBottomInset
        anchors.leftMargin: card.contentLeftInset
        spacing: Style.spacing.md

        Item {
          width: parent.width
          height: Style.space(46)

          Image {
            id: brandIcon
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: Style.space(36)
            height: width
            source: Qt.resolvedUrl("assets/icon.png")
            fillMode: Image.PreserveAspectFit
            mipmap: true
          }

          Column {
            anchors.left: brandIcon.right
            anchors.leftMargin: Style.spacing.sm
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0
            Text {
              text: "GlyphTap"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.heading
              font.bold: true
            }
            Text {
              text: "Find. Tap. Copy."
              color: root.foreground
              opacity: 0.55
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
            }
          }

          Rectangle {
            id: formatButton
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: formatText.implicitWidth + Style.spacing.lg
            height: Style.space(32)
            radius: root.cornerRadius
            color: root.formatMenuOpen ? root.selectedBackground : "transparent"
            border.width: 1
            border.color: root.borderColor
            Text {
              id: formatText
              anchors.centerIn: parent
              text: root.formatLabel(root.outputFormat) + "  ▾"
              color: root.formatMenuOpen ? root.selectedText : root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.body
            }
            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.PointingHandCursor
              onClicked: root.formatMenuOpen = !root.formatMenuOpen
            }
          }
        }

        Rectangle {
          width: parent.width
          height: Style.space(50)
          radius: root.cornerRadius
          color: "transparent"
          border.width: root.gridFocused ? 1 : 2
          border.color: root.gridFocused ? root.borderColor : root.accent

          Text {
            anchors.left: parent.left
            anchors.leftMargin: Style.spacing.md
            anchors.verticalCenter: parent.verticalCenter
            text: "⌕"
            color: root.accent
            font.family: root.fontFamily
            font.pixelSize: Style.font.display
          }
          Text {
            anchors.left: parent.left
            anchors.leftMargin: Style.space(48)
            anchors.right: loadingGlyph.left
            anchors.rightMargin: Style.spacing.md
            anchors.verticalCenter: parent.verticalCenter
            text: root.filterText || "Search 300,000+ icons…"
            color: root.foreground
            opacity: root.filterText ? 1 : 0.5
            elide: Text.ElideRight
            font.family: root.fontFamily
            font.pixelSize: Style.font.title
          }
          Text {
            id: loadingGlyph
            anchors.right: parent.right
            anchors.rightMargin: Style.spacing.md
            anchors.verticalCenter: parent.verticalCenter
            text: root.loading ? "•••" : (root.filterText ? "×" : "")
            color: root.foreground
            opacity: 0.6
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
            MouseArea {
              anchors.fill: parent
              anchors.margins: -Style.spacing.sm
              enabled: !root.loading && !!root.filterText
              cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
              onClicked: root.queueSearch("")
            }
          }
        }

        Item {
          width: parent.width
          height: parent.height - Style.space(46) - Style.space(50) - Style.space(42) - Style.spacing.md * 3

          GridView {
            id: resultGrid
            anchors.fill: parent
            model: displayModel
            clip: true
            cellWidth: root.cellWidth + Style.spacing.md
            cellHeight: root.cellHeight + Style.spacing.md
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
              required property int index
              required property string iconId
              required property string iconName
              required property string collection
              required property bool favorite
              required property string sourceUrl
              readonly property bool selected: index === root.selectedIndex
              width: root.cellWidth
              height: root.cellHeight
              radius: root.cornerRadius
              color: selected ? root.selectedBackground : "transparent"
              border.width: selected ? 1 : 0
              border.color: root.accent

              Image {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: Style.spacing.md
                width: Style.space(48)
                height: width
                source: parent.sourceUrl
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                mipmap: true
              }
              Text {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Style.spacing.sm
                anchors.leftMargin: Style.spacing.sm
                anchors.rightMargin: Style.spacing.sm
                text: parent.iconName
                color: parent.selected ? root.selectedText : root.foreground
                opacity: parent.selected ? 1 : 0.75
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
              }
              Text {
                visible: parent.favorite
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: Style.spacing.sm
                text: "★"
                color: root.accent
                font.pixelSize: Style.font.body
              }
              MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                cursorShape: Qt.PointingHandCursor
                onContainsMouseChanged: if (containsMouse) {
                  root.selectedIndex = index
                  root.gridFocused = true
                }
                onClicked: function(mouse) {
                  root.selectedIndex = index
                  root.gridFocused = true
                  if (mouse.button === Qt.RightButton) root.favoriteIndex(index)
                  else root.activateIndex(index, (mouse.modifiers & Qt.ControlModifier) !== 0)
                }
              }
            }
          }

          Column {
            anchors.centerIn: parent
            visible: !root.loading && displayModel.count === 0
            spacing: Style.spacing.sm
            Text {
              width: parent.width
              text: root.filterText ? "No icons found" : "Search for an icon"
              color: root.foreground
              horizontalAlignment: Text.AlignHCenter
              font.family: root.fontFamily
              font.pixelSize: Style.font.heading
            }
            Text {
              width: parent.width
              text: root.filterText ? (root.online ? "Try a broader term" : "Connect once to expand your offline cache") : "Favorites and recent icons will appear here"
              color: root.foreground
              opacity: 0.55
              horizontalAlignment: Text.AlignHCenter
              font.family: root.fontFamily
              font.pixelSize: Style.font.body
            }
          }

          Rectangle {
            anchors.fill: parent
            visible: root.previewOpen && root.currentRow() !== null
            radius: root.cornerRadius
            color: root.background
            border.width: 1
            border.color: root.borderColor
            z: 10
            property var row: root.currentRow()

            Row {
              anchors.centerIn: parent
              spacing: Style.space(48)
              Image {
                width: Style.space(220)
                height: width
                source: parent.parent.row ? parent.parent.row.sourceUrl : ""
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                mipmap: true
              }
              Column {
                width: Style.space(310)
                anchors.verticalCenter: parent.verticalCenter
                spacing: Style.spacing.md
                Text {
                  width: parent.width
                  text: parent.parent.parent.row ? parent.parent.parent.row.collection : ""
                  color: root.accent
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.title
                }
                Text {
                  width: parent.width
                  text: parent.parent.parent.row ? parent.parent.parent.row.iconName : ""
                  color: root.foreground
                  wrapMode: Text.Wrap
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.display
                  font.bold: true
                }
                Text {
                  width: parent.width
                  text: parent.parent.parent.row ? parent.parent.parent.row.dimensions + "  ·  " + parent.parent.parent.row.licenseName : ""
                  color: root.foreground
                  opacity: 0.58
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                }
                Text {
                  width: parent.width
                  text: "Enter copy  ·  Ctrl+S save  ·  Space close preview"
                  color: root.foreground
                  opacity: 0.72
                  wrapMode: Text.Wrap
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.caption
                }
              }
            }
          }

          Rectangle {
            anchors.top: parent.top
            anchors.right: parent.right
            width: Style.space(190)
            height: formatList.implicitHeight + Style.spacing.sm * 2
            visible: root.formatMenuOpen
            radius: root.cornerRadius
            color: root.background
            border.width: 1
            border.color: root.borderColor
            z: 20
            Column {
              id: formatList
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              Repeater {
                model: root.formats
                delegate: Rectangle {
                  required property var modelData
                  width: formatList.width
                  height: Style.space(34)
                  color: modelData.value === root.outputFormat ? root.selectedBackground : "transparent"
                  Text {
                    anchors.left: parent.left
                    anchors.leftMargin: Style.spacing.md
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: modelData.value === root.outputFormat ? root.selectedText : root.foreground
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.body
                  }
                  MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                      root.outputFormat = modelData.value
                      root.formatMenuOpen = false
                    }
                  }
                }
              }
            }
          }
        }

        Item {
          width: parent.width
          height: Style.space(42)
          Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.statusMessage || (root.copiedThisSession > 0 ? root.copiedThisSession + " icon" + (root.copiedThisSession === 1 ? "" : "s") + " copied this session" : (displayModel.count + " icons" + (root.online ? "" : " · offline")))
            color: root.statusMessage ? root.accent : root.foreground
            opacity: root.statusMessage ? 1 : 0.58
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
          }
          Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: "↑↓←→ navigate   Enter copy   Ctrl+Enter keep open   Space preview   Ctrl+D favorite"
            color: root.foreground
            opacity: 0.5
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
          }
        }
      }
    }
  }
}
