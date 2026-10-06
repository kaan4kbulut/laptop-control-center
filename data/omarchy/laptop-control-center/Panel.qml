import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

// laptop-control-center bar widget'ı: barda etkin mod; tıklayınca mod, fan, sıcaklık,
// klavye ışığı ve pil tasarrufu paneli. Veriyi `lcc bar` verir, işleri `lcc` komutları yapar.
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

  function lbl(key, fallback) { return labels[key] !== undefined ? labels[key] : (fallback || key) }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
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
    fanSampling.command = ["lcc", "bar", "--fans", opened ? "on" : "off"]
    fanSampling.running = true
    refresh()
  }

  visible: info !== null
  implicitWidth: info !== null ? button.implicitWidth : 0
  implicitHeight: info !== null ? button.implicitHeight : 0

  Process {
    id: statusProc
    command: ["lcc", "bar"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var d = Model.parse(text)
        if (d) root.info = d
      }
    }
  }
  Process { id: actionProc; onExited: root.refresh() }
  Process { id: fanSampling }

  Component.onCompleted: refresh()
  // Kapalıyken seyrek yokla; mod değişikliklerinde `lcc` IPC ile hemen yeniletir.
  Timer { interval: root.opened ? 2000 : 30000; running: true; repeat: true; onTriggered: root.refresh() }

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
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(400))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function (direction) { root.switchPanel(direction) }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(14)

        // ---------- Hero: mod simgesi · ad/güç sınırı · sıcaklık ----------
        Item {
          width: parent.width
          implicitHeight: Math.max(heroIcon.implicitHeight, heroLabels.implicitHeight, heroTemp.implicitHeight)

          Text {
            id: heroIcon
            textFormat: Text.PlainText
            text: Model.modeIcon(root.mode)
            color: root.bar.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.display
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
          }
          Column {
            id: heroLabels
            anchors.left: heroIcon.right
            anchors.leftMargin: Style.space(14)
            anchors.right: heroTemp.left
            anchors.rightMargin: Style.space(10)
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(2)
            Text {
              width: parent.width
              text: root.lbl("bar.mode").replace("{mode}", root.modeLabel)
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.title
              font.bold: true
              elide: Text.ElideRight
            }
            Text {
              width: parent.width
              textFormat: Text.PlainText
              text: root.lbl("bar.power.limit") + " " + Model.num(root.info ? root.info.pl1 : null) + " W"
                + (root.info && root.info.power && root.info.power !== "off" ? "  ·  " + root.lbl("power." + root.info.power).toUpperCase() : "")
              color: Qt.darker(root.bar.foreground, 1.4)
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
              font.bold: true
              font.letterSpacing: 1.2
              elide: Text.ElideRight
            }
          }
          Column {
            id: heroTemp
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            Text {
              anchors.right: parent.right
              text: Model.num(root.info ? root.info.cpuTemp : null) + " °C"
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.title
              font.bold: true
            }
            Text {
              anchors.right: parent.right
              text: root.lbl("cpu.short")
              color: Qt.darker(root.bar.foreground, 1.4)
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
            }
          }
        }

        PanelSeparator { foreground: root.bar.foreground }

        // ---------- Güç modu ----------
        Column {
          width: parent.width
          spacing: Style.space(10)
          PanelSectionHeader { text: root.lbl("bar.modes"); foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }
          Row {
            id: modeRow
            width: parent.width
            spacing: Style.space(6)
            readonly property var items: root.info ? root.info.modes.filter(function (m) { return m.id !== "powersave" || m.id === root.mode }) : []
            readonly property real cellWidth: items.length > 0 ? (width - spacing * (items.length - 1)) / items.length : 0
            Repeater {
              model: modeRow.items
              Button {
                required property var modelData
                width: modeRow.cellWidth
                iconText: Model.modeIcon(modelData.id)
                iconSize: Style.font.title
                text: modelData.label
                fontSize: Style.font.bodySmall
                foreground: root.bar.foreground
                fontFamily: root.bar.fontFamily
                verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
                bordered: true
                active: root.mode === modelData.id
                onClicked: root.run(["mode", modelData.id, "--notify"])
              }
            }
          }
        }

        // ---------- Fan ----------
        Column {
          width: parent.width
          spacing: Style.space(10)
          PanelSectionHeader { text: root.lbl("bar.fan"); foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }
          Row {
            id: fanRow
            width: parent.width
            spacing: Style.space(6)
            readonly property var items: root.info ? root.info.fans : []
            readonly property real cellWidth: items.length > 0 ? (width - spacing * (items.length - 1)) / items.length : 0
            Repeater {
              model: fanRow.items
              Button {
                required property var modelData
                width: fanRow.cellWidth
                text: modelData.label
                fontSize: Style.font.bodySmall
                foreground: root.bar.foreground
                fontFamily: root.bar.fontFamily
                bordered: true
                active: root.info && root.info.fan === modelData.id
                onClicked: root.run(["fan", modelData.id])
              }
            }
          }
          Row {
            width: parent.width
            spacing: Style.space(20)
            Repeater {
              model: [["cpu", "fan.cpu"], ["gpu", "fan.gpu"]]
              InfoPair {
                required property var modelData
                width: (parent.width - parent.spacing) / 2
                label: root.lbl(modelData[1])
                value: {
                  var s = root.info && root.info.fanSpeeds ? root.info.fanSpeeds[modelData[0]] : undefined
                  return s === undefined ? "—" : Model.num(s) + " %"
                }
              }
            }
          }
          InfoPair {
            width: parent.width
            label: root.lbl("gpu.short")
            value: !root.info ? "—" : root.info.gpuSleeping ? root.lbl("gpu.sleeping") : Model.num(root.info.gpuTemp) + " °C"
          }
        }

        // ---------- Klavye ışığı ----------
        Column {
          width: parent.width
          spacing: Style.space(10)
          visible: root.kbd !== null
          PanelSectionHeader { text: root.lbl("bar.kbd"); foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }
          Row {
            width: parent.width
            spacing: Style.space(12)
            Rectangle {
              id: swatch
              anchors.verticalCenter: parent.verticalCenter
              width: Style.space(18); height: width; radius: width / 2
              color: root.kbd ? root.kbd.color : "transparent"
              border.width: 1
              border.color: root.bar.foreground
            }
            PanelSlider {
              id: kbdSlider
              anchors.verticalCenter: parent.verticalCenter
              width: parent.width - swatch.width - levelText.width - parent.spacing * 2
              bar: root.bar
              minimum: 0; maximum: 4; step: 1; integer: true; tickCount: 5
              value: root.kbdLevel
              onReleased: function (v) { root.kbdLevel = Math.round(v); root.run(["kbd", "-b", String(Math.round(v) * 25), "-p"]) }
            }
            Text {
              id: levelText
              anchors.verticalCenter: parent.verticalCenter
              text: Math.round(kbdSlider.liveValue) + "/4"
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.bodySmall
            }
          }
        }

        // ---------- Pil tasarrufu ----------
        Column {
          width: parent.width
          spacing: Style.space(10)
          PanelSectionHeader { text: root.lbl("power.title").toUpperCase(); foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }
          Row {
            id: powerRow
            width: parent.width
            spacing: Style.space(6)
            readonly property var items: ["off", "saver", "ultra"]
            readonly property real cellWidth: (width - spacing * (items.length - 1)) / items.length
            Repeater {
              model: powerRow.items
              Button {
                required property string modelData
                width: powerRow.cellWidth
                text: root.lbl("power." + modelData)
                fontSize: Style.font.bodySmall
                foreground: root.bar.foreground
                fontFamily: root.bar.fontFamily
                bordered: true
                active: root.info && root.info.power === modelData
                onClicked: root.run(["power", modelData])
              }
            }
          }
        }

        PanelSeparator { foreground: root.bar.foreground }

        Button {
          width: parent.width
          text: root.lbl("bar.open")
          fontSize: Style.font.bodySmall
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
          bordered: true
          onClicked: {
            root.close()
            Quickshell.execDetached(["uwsm-app", "--", "lcc", "gui"])
          }
        }
        Text {
          width: parent.width
          horizontalAlignment: Text.AlignHCenter
          text: root.lbl("bar.shortcut")
          color: Qt.darker(root.bar.foreground, 1.6)
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.caption
        }
      }
    }
  }

  component InfoPair: Row {
    property string label: ""
    property string value: ""
    spacing: Style.space(8)
    Text {
      id: pairLabel
      textFormat: Text.PlainText
      text: label
      color: root.bar.foreground
      opacity: 0.6
      font.family: root.bar.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
    Item { width: Math.max(0, parent.width - pairLabel.implicitWidth - pairValue.implicitWidth - parent.spacing * 2); height: 1 }
    Text {
      id: pairValue
      textFormat: Text.PlainText
      text: value
      color: root.bar.foreground
      font.family: root.bar.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
  }
}
