import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

// laptop-control-center bar widget'ı: barda etkin mod; tıklayınca Kontrol Merkezi'nin
// görünümünde sade bir panel (mod, fan, canlı halka göstergeler, ayrıntı karoları,
// klavye ışığı, pil tasarrufu). Kapalıyken `lcc bar` seyrek yoklanır; açıkken
// `lcc bar --watch` saniyede bir yazar.
// Sol tık paneli açar, sağ tık mod adını gizler/gösterir, tekerlek modlar arasında gezer.
Panel {
  id: root
  moduleName: "laptop-control-center"
  ipcTarget: "laptop-control-center"
  manageIpc: false

  property var info: null
  readonly property var labels: info && info.labels ? info.labels : ({})
  readonly property string mode: info && info.mode ? info.mode : ""
  readonly property string modeLabel: info ? Model.labelOf(info.modes, mode) : ""
  readonly property bool showLabel: setting("showLabel", true) === true
  readonly property var kbd: info ? info.keyboard : null
  property int kbdLevel: kbd && kbd.max ? Math.round(kbd.brightness / kbd.max * 4) : 0

  // Kontrol Merkezi teması (lcc/gui/qml/Theme.qml ile aynı).
  readonly property color bg: "#050608"
  readonly property color tile: "#0d0f13"
  readonly property color text: "#e8ecf2"
  readonly property color soft: "#c9d1dc"
  readonly property color muted: "#a3acba"
  readonly property color dim: "#8a93a3"
  readonly property color faint: "#6b7382"
  readonly property color line: "#2a2f38"
  readonly property color track: "#14171d"
  readonly property color cyan: "#22b8ff"
  readonly property color purple: "#8b3dff"
  readonly property color red: "#ff2d55"
  readonly property string uiFont: exo.status === FontLoader.Ready ? exo.name : root.bar.fontFamily
  readonly property string digitFont: rajdhani.status === FontLoader.Ready ? rajdhani.name : root.bar.fontFamily

  FontLoader { id: exo; source: "fonts/Exo2.ttf" }
  FontLoader { id: rajdhani; source: "fonts/Rajdhani-SemiBold.ttf" }

  function lbl(key, fallback) { return labels[key] !== undefined ? labels[key] : (fallback || key) }
  function fanSpeed(name) {
    var s = info && info.fanSpeeds ? info.fanSpeeds[name] : undefined
    return s === undefined ? null : s
  }
  function tempColor(t) { return t >= 90 ? root.red : t >= 75 ? root.purple : root.cyan }

  function refresh() {
    if (!statusProc.running && !watchProc.running) statusProc.running = true
  }

  function run(args) {
    if (actionProc.running) return
    actionProc.command = ["lcc"].concat(args)
    actionProc.running = true
  }

  function toggleLabel() {
    root.settings = Object.assign({}, root.settings, { showLabel: !root.showLabel })
    if (root.bar && root.bar.shell) root.bar.shell.updateEntryInline(root.moduleName, root.settings)
  }

  IpcHandler {
    target: "laptop-control-center"
    function open() { root.open() }
    function close() { root.close() }
    function toggle() { root.toggle() }
    function refresh() { root.refresh() }
  }

  onOpenedChanged: {
    watchProc.running = opened
    if (!opened) refresh()
  }

  visible: info !== null
  implicitWidth: info !== null ? button.implicitWidth : 0
  implicitHeight: info !== null ? button.implicitHeight : 0

  Process {
    id: statusProc
    command: ["lcc", "bar"]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: { var d = Model.parse(text); if (d) root.info = d } }
  }
  Process {
    id: watchProc
    command: ["lcc", "bar", "--watch"]
    stdout: SplitParser { onRead: function (line) { var d = Model.parse(line); if (d) root.info = d } }
  }
  Process { id: actionProc; onExited: root.refresh() }

  Component.onCompleted: refresh()
  // Kapalıyken seyrek yokla; mod değişikliklerinde `lcc` IPC ile hemen yeniletir.
  Timer { interval: 30000; running: !root.opened; repeat: true; onTriggered: root.refresh() }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: Model.modeIcon(root.mode) + (root.showLabel && !vertical && root.modeLabel ? "  " + root.modeLabel : "")
    tooltipText: root.showLabel ? "" : root.modeLabel
    onPressed: function (b) {
      if (b === Qt.RightButton) root.toggleLabel()
      else root.toggle()
    }
    onWheelMoved: function (delta) {
      var next = Model.cycleMode(root.info ? root.info.modes : [], root.mode, delta > 0 ? -1 : 1)
      if (next) root.run(["mode", next, "--notify"])
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened && root.info !== null
    padding: 0
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(420)
    contentHeight: panel.fittedContentHeight(column.implicitHeight + 40)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function (direction) { root.switchPanel(direction) }

      Rectangle { anchors.fill: parent; color: root.bg }

      Flickable {
        anchors.fill: parent
        anchors.margins: 20
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
          id: column
          width: parent.width
          spacing: 18

          // ---------- Hero: parlayan mod halkası · ad · sıcaklık ----------
          Item {
            width: parent.width
            height: 56
            RectangularShadow {
              anchors.fill: heroRing; radius: 26; blur: 14; color: root.cyan; opacity: 0.8
            }
            Rectangle {
              id: heroRing
              width: 52; height: 52; radius: 26
              color: root.bg
              border.width: 2; border.color: root.cyan
              Text {
                anchors.centerIn: parent
                text: Model.modeIcon(root.mode)
                color: root.text
                font.family: root.bar.fontFamily
                font.pixelSize: 24
              }
            }
            Column {
              anchors.left: heroRing.right; anchors.leftMargin: 14
              anchors.right: heroTemp.left; anchors.rightMargin: 10
              anchors.verticalCenter: parent.verticalCenter
              spacing: 2
              Text {
                width: parent.width; elide: Text.ElideRight
                text: root.lbl("bar.mode").replace("{mode}", root.modeLabel)
                color: root.text; font.family: root.uiFont; font.pixelSize: 18; font.weight: Font.DemiBold
              }
              // Güç sınırları: işlemci (PL1) ve ekran kartı (şu anki sınır).
              Text {
                width: parent.width; elide: Text.ElideRight
                text: root.lbl("cpu.short").toUpperCase() + " " + Model.num(root.info ? root.info.pl1 : null) + " W"
                  + (root.info && root.info.gpuPowerLimit ? "  ·  " + root.lbl("gpu.short").toUpperCase() + " " + Model.num(root.info.gpuPowerLimit) + " W" : "")
                color: root.dim; font.family: root.uiFont; font.pixelSize: 11; font.letterSpacing: 1.2
              }
              Text {
                readonly property bool boost: !!root.info && root.mode === "performance"
                  && root.info.gpuPowerMax > (root.info.gpuPowerLimit || 0)
                readonly property bool saving: !!root.info && !!root.info.power && root.info.power !== "off"
                visible: boost || saving
                width: parent.width; elide: Text.ElideRight
                text: !root.info ? "" : saving ? root.lbl("power." + root.info.power).toUpperCase()
                             : root.lbl("gpu.short").toUpperCase() + " " + root.lbl("bar.boost").replace("{w}", Model.num(root.info.gpuPowerMax)).toUpperCase()
                color: saving ? root.purple : root.cyan
                font.family: root.uiFont; font.pixelSize: 11; font.letterSpacing: 1.2
              }
            }
            Column {
              id: heroTemp
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              Text {
                anchors.right: parent.right
                text: Model.num(root.info ? root.info.cpuTemp : null) + " °C"
                color: root.text; font.family: root.digitFont; font.pixelSize: 22; font.weight: Font.DemiBold
              }
              Text {
                anchors.right: parent.right
                text: root.lbl("cpu.short")
                color: root.dim; font.family: root.uiFont; font.pixelSize: 12
              }
            }
          }

          // ---------- Güç modu ----------
          Column {
            width: parent.width; spacing: 10
            Caption { text: root.lbl("bar.modes") }
            Row {
              id: modeRow
              width: parent.width; spacing: 8
              readonly property var items: root.info ? root.info.modes.filter(function (m) { return m.id !== "powersave" || m.id === root.mode }) : []
              Repeater {
                model: modeRow.items
                Item {
                  id: modeTile
                  required property var modelData
                  readonly property bool on: root.mode === modelData.id
                  width: (modeRow.width - modeRow.spacing * (modeRow.items.length - 1)) / modeRow.items.length
                  height: 64
                  RectangularShadow {
                    anchors.fill: modeBox; radius: 12; blur: 12; color: root.cyan; visible: modeTile.on
                  }
                  Rectangle {
                    id: modeBox
                    anchors.fill: parent; radius: 12
                    color: modeTile.on ? "#07141c" : root.tile
                    border.width: 2; border.color: modeTile.on ? root.cyan : "transparent"
                  }
                  Column {
                    anchors.centerIn: parent; spacing: 4
                    Text {
                      anchors.horizontalCenter: parent.horizontalCenter
                      text: Model.modeIcon(modeTile.modelData.id)
                      color: modeTile.on ? root.cyan : root.dim
                      font.family: root.bar.fontFamily; font.pixelSize: 16
                    }
                    Text {
                      anchors.horizontalCenter: parent.horizontalCenter
                      text: modeTile.modelData.label
                      color: modeTile.on ? "white" : root.soft
                      font.family: root.uiFont; font.pixelSize: 14
                    }
                  }
                  MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: root.run(["mode", modeTile.modelData.id, "--notify"])
                  }
                }
              }
            }
          }

          // ---------- Fan ----------
          Column {
            width: parent.width; spacing: 10
            Caption { text: root.lbl("bar.fan") }
            Row {
              id: fanRow
              width: parent.width; spacing: 6
              readonly property var items: root.info ? root.info.fans : []
              Repeater {
                model: fanRow.items
                PillButton {
                  required property var modelData
                  width: (fanRow.width - fanRow.spacing * (fanRow.items.length - 1)) / fanRow.items.length
                  label: modelData.label
                  checked: root.info && root.info.fan === modelData.id
                  accent: root.cyan
                  onClicked: root.run(["fan", modelData.id])
                }
              }
            }
          }

          // ---------- Canlı halka göstergeler ----------
          Row {
            id: rings
            width: parent.width
            readonly property real cell: width / 4
            Ring {
              width: rings.cell
              value: root.info ? root.info.cpuTemp : null
              text: Model.num(root.info ? root.info.cpuTemp : null); unit: "°C"
              label: root.lbl("cpu.short")
              color: root.tempColor(root.info ? root.info.cpuTemp : 0)
            }
            Ring {
              width: rings.cell
              readonly property bool sleeping: !root.info || root.info.gpuSleeping
              value: sleeping ? null : root.info.gpuTemp
              text: sleeping ? "–" : Model.num(root.info.gpuTemp); unit: sleeping ? "" : "°C"
              label: root.lbl("gpu.short")
              color: root.tempColor(sleeping ? 0 : root.info.gpuTemp)
            }
            Ring {
              width: rings.cell
              value: root.fanSpeed("cpu")
              text: Model.num(root.fanSpeed("cpu")); unit: "%"
              label: root.lbl("fan.cpu")
              color: root.cyan
            }
            Ring {
              width: rings.cell
              value: root.fanSpeed("gpu")
              text: Model.num(root.fanSpeed("gpu")); unit: "%"
              label: root.lbl("fan.gpu")
              color: root.cyan
            }
          }

          // ---------- Ayrıntı karoları ----------
          Grid {
            id: tiles
            width: parent.width
            columns: 3; spacing: 8
            readonly property real cell: (width - spacing * 2) / 3
            StatTile {
              width: tiles.cell
              value: root.info && root.info.cpuFreq ? Model.num(root.info.cpuFreq / 1000, 1) : "–"; unit: "GHz"
              label: root.lbl("bar.freq")
            }
            StatTile {
              width: tiles.cell
              value: Model.num(root.info ? root.info.cpuUsage : null); unit: "%"
              label: root.lbl("cpu.short") + " · " + root.lbl("bar.usage").toLowerCase()
            }
            StatTile {
              width: tiles.cell
              readonly property bool sleeping: !root.info || root.info.gpuSleeping
              value: sleeping ? root.lbl("gpu.sleeping") : Model.num(root.info.gpuPower, 0)
              unit: sleeping ? "" : (root.info.gpuPowerLimit ? "/ " + Model.num(root.info.gpuPowerLimit) + " W" : "W")
              label: root.lbl("gpu.short")
            }
            StatTile {
              width: tiles.cell
              value: root.info ? Model.num(root.info.mem * root.info.memTotal / 100, 1) : "–"
              unit: root.info ? "/ " + Model.num(root.info.memTotal) + " GB" : ""
              label: root.lbl("bar.mem")
            }
            StatTile {
              width: tiles.cell
              value: Model.num(root.info ? root.info.disk : null); unit: "%"
              label: root.lbl("bar.disk")
            }
            StatTile {
              width: tiles.cell
              value: Model.num(root.info ? root.info.battery : null); unit: "%"
              label: {
                var d = root.info
                if (!d) return root.lbl("bar.battery")
                if (d.onBattery)
                  return d.batteryHours ? Model.duration(d.batteryHours, root.lbl("app.title") === "Control Center") : Model.num(d.batteryPower, 1) + " W"
                return d.batteryPower > 0.5 ? root.lbl("bar.charging") : root.lbl("power.onac")
              }
            }
          }

          // ---------- Klavye ışığı ----------
          Column {
            width: parent.width; spacing: 10
            visible: root.kbd !== null
            Caption { text: root.lbl("bar.kbd") }
            Item {
              width: parent.width; height: 28
              RectangularShadow {
                anchors.fill: kbdDot; radius: 14; blur: 10; color: kbdDot.color
                visible: root.kbdLevel > 0
              }
              Rectangle {
                id: kbdDot
                width: 28; height: 28; radius: 14
                color: root.kbd ? root.kbd.color : root.line
                border.width: 2; border.color: "white"
              }
              Item {
                id: kbdTrack
                anchors.left: kbdDot.right; anchors.leftMargin: 14
                anchors.right: kbdText.left; anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                height: 28
                Rectangle { anchors.verticalCenter: parent.verticalCenter; width: parent.width; height: 4; color: root.line }
                RectangularShadow {
                  anchors.fill: kbdFill; blur: 8; color: root.purple; visible: root.kbdLevel > 0
                }
                Rectangle {
                  id: kbdFill
                  anchors.verticalCenter: parent.verticalCenter
                  width: parent.width * root.kbdLevel / 4; height: 4; color: root.purple
                  Behavior on width { NumberAnimation { duration: 150 } }
                }
                MouseArea {
                  anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                  function levelAt(x) { return Math.max(0, Math.min(4, Math.round(x / width * 4))) }
                  onPressed: function (m) { root.kbdLevel = levelAt(m.x) }
                  onPositionChanged: function (m) { if (pressed) root.kbdLevel = levelAt(m.x) }
                  onReleased: root.run(["kbd", "-b", String(root.kbdLevel * 25), "-p"])
                }
              }
              Text {
                id: kbdText
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                text: root.kbdLevel + "/4"
                color: root.soft; font.family: root.digitFont; font.pixelSize: 14
              }
            }
          }

          // ---------- Pil tasarrufu ----------
          Column {
            width: parent.width; spacing: 10
            Caption { text: root.lbl("power.title").toUpperCase() }
            Row {
              id: powerRow
              width: parent.width; spacing: 6
              readonly property var items: ["off", "saver", "ultra"]
              Repeater {
                model: powerRow.items
                PillButton {
                  required property string modelData
                  width: (powerRow.width - powerRow.spacing * 2) / 3
                  label: root.lbl("power." + modelData)
                  checked: root.info && root.info.power === modelData
                  accent: root.purple
                  onClicked: root.run(["power", modelData])
                }
              }
            }
          }

          // ---------- Ana pencere ----------
          Column {
            width: parent.width; spacing: 8
            Rectangle {
              width: parent.width; height: 44; radius: 22
              color: openArea.containsMouse ? "#0d1117" : "transparent"
              border.width: 1.5; border.color: openArea.containsMouse ? root.cyan : root.line
              Text {
                anchors.centerIn: parent
                text: root.lbl("bar.open")
                color: root.text; font.family: root.uiFont; font.pixelSize: 14
              }
              MouseArea {
                id: openArea
                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                onClicked: {
                  root.close()
                  Quickshell.execDetached(["uwsm-app", "--", "lcc", "gui"])
                }
              }
            }
            Text {
              width: parent.width; horizontalAlignment: Text.AlignHCenter
              text: root.lbl("bar.shortcut")
              color: root.faint; font.family: root.uiFont; font.pixelSize: 11
            }
          }
        }
      }
    }
  }

  // Küçük, aralıklı büyük harfli bölüm başlığı.
  component Caption: Text {
    color: root.dim
    font.family: root.uiFont
    font.pixelSize: 11
    font.letterSpacing: 1.5
  }

  // Yuvarlak seçim düğmesi (fan, pil tasarrufu).
  component PillButton: Rectangle {
    id: pill
    property string label
    property bool checked: false
    property color accent: root.cyan
    signal clicked()
    height: 40; radius: 20
    color: checked ? Qt.rgba(accent.r, accent.g, accent.b, 0.14) : (pillArea.containsMouse ? "#0d1117" : "transparent")
    border.width: 1.5
    border.color: checked ? accent : root.line
    Text {
      anchors.centerIn: parent
      text: pill.label
      color: pill.checked ? "white" : root.muted
      font.family: root.uiFont; font.pixelSize: 13
    }
    MouseArea {
      id: pillArea
      anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
      onClicked: pill.clicked()
    }
  }

  // 270° halka gösterge (0–100); ortada değer, altında etiket.
  component Ring: Column {
    id: ring
    property var value: null
    property string text: "–"
    property string unit: ""
    property string label: ""
    property color color: root.cyan
    readonly property real frac: value === null || value === undefined ? 0 : Math.max(0, Math.min(1, Number(value) / 100))
    spacing: 6
    Item {
      anchors.horizontalCenter: parent.horizontalCenter
      width: 72; height: 72
      Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
          strokeColor: root.track; strokeWidth: 6; fillColor: "transparent"; capStyle: ShapePath.RoundCap
          PathAngleArc { centerX: 36; centerY: 36; radiusX: 31; radiusY: 31; startAngle: 135; sweepAngle: 270 }
        }
        // hafif parlama: aynı yayın geniş ve saydam kopyası
        ShapePath {
          strokeColor: Qt.rgba(ring.color.r, ring.color.g, ring.color.b, 0.22); strokeWidth: 12
          fillColor: "transparent"; capStyle: ShapePath.RoundCap
          PathAngleArc { centerX: 36; centerY: 36; radiusX: 31; radiusY: 31; startAngle: 135; sweepAngle: Math.max(0.1, 270 * ring.frac) }
        }
        ShapePath {
          strokeColor: ring.frac > 0 ? ring.color : "transparent"; strokeWidth: 6
          fillColor: "transparent"; capStyle: ShapePath.RoundCap
          PathAngleArc { centerX: 36; centerY: 36; radiusX: 31; radiusY: 31; startAngle: 135; sweepAngle: Math.max(0.1, 270 * ring.frac) }
        }
      }
      Row {
        anchors.centerIn: parent
        spacing: 1
        Text {
          id: ringValue
          text: ring.text
          color: root.text; font.family: root.digitFont; font.pixelSize: 20; font.weight: Font.DemiBold
        }
        Text {
          anchors.baseline: ringValue.baseline
          text: ring.unit
          color: root.muted; font.family: root.digitFont; font.pixelSize: 11
        }
      }
    }
    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      width: ring.width; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
      text: ring.label
      color: root.dim; font.family: root.uiFont; font.pixelSize: 11
    }
  }

  // Koyu karo: büyük değer + birim, altında etiket.
  component StatTile: Rectangle {
    id: st
    property string value: "–"
    property string unit: ""
    property string label: ""
    height: 58; radius: 10
    color: root.tile
    Column {
      anchors.fill: parent; anchors.margins: 10
      spacing: 2
      Row {
        spacing: 3
        Text {
          id: stValue
          text: st.value
          color: root.text; font.family: root.digitFont; font.pixelSize: 20; font.weight: Font.DemiBold
        }
        Text {
          anchors.baseline: stValue.baseline
          text: st.unit
          color: root.muted; font.family: root.digitFont; font.pixelSize: 12
        }
      }
      Text {
        width: parent.width; elide: Text.ElideRight
        text: st.label
        color: root.dim; font.family: root.uiFont; font.pixelSize: 11
      }
    }
  }
}
