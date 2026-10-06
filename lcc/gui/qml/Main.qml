import QtQuick
import QtQuick.Window

Window {
    id: win
    required property var bridge
    property string startPage: "monitor"
    property string page: startPage
    readonly property var tr: bridge.tr
    readonly property var info: bridge.info
    readonly property var live: bridge.live
    readonly property var desk: bridge.desk
    readonly property color accent: page === "monitor" || page === "fancurve" ? Theme.cyan : Theme.purple

    width: Theme.stageW
    height: Theme.stageH
    minimumWidth: 960
    minimumHeight: 570
    visible: true
    color: Theme.bg
    title: tr["app.title"]

    // Tasarım 1280×760 sabit koordinatlarla çizildi; pencere boyutuna oranlanır.
    Item {
        id: stage
        width: Theme.stageW
        height: Theme.stageH
        scale: Math.min(win.width / width, win.height / height)
        transformOrigin: Item.TopLeft
        x: (win.width - width * scale) / 2
        y: (win.height - height * scale) / 2

        Waves { anchors.fill: parent; centerX: win.page === "settings" ? 330 : 1180 }

        // --- başlık çubuğu ---------------------------------------------------
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 13
            text: win.tr["app.title"]
            font.family: Theme.font; font.pixelSize: 19; font.weight: Font.Medium
            font.letterSpacing: 0.5
            color: Theme.text
        }
        Row {
            x: 24; y: 16; spacing: 8
            visible: win.live.battery !== undefined && win.live.battery !== null
            Text {
                text: win.tr["battery.short"] + " " + Math.round(win.live.battery || 0) + " %"
                font.family: Theme.digits; font.pixelSize: 15; font.weight: Font.DemiBold
                color: win.live.onBattery && win.live.battery < 20 ? Theme.pink : Theme.muted
            }
            Text {
                text: win.live.onBattery ? "" : "⚡"
                font.pixelSize: 13; color: Theme.cyan
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 12; y: 8
            spacing: 4
            WinButton { path: "M3 12h10"; label: win.tr["win.minimize"]; onClicked: win.showMinimized() }
            WinButton {
                path: "M3 3h10v10H3z"; label: win.tr["win.maximize"]
                onClicked: win.visibility === Window.Maximized ? win.showNormal() : win.showMaximized()
            }
            WinButton { path: "M3 3l10 10M13 3L3 13"; label: win.tr["win.close"]; onClicked: Qt.quit() }
        }

        // --- gezinme ---------------------------------------------------------
        Column {
            x: 0; y: 100; width: 180; spacing: 6
            z: 2
            Repeater {
                model: [["monitor", "nav.monitor"], ["led", "nav.led"], ["settings", "nav.settings"], ["power", "nav.power"]]
                delegate: Item {
                    required property var modelData
                    readonly property bool current: win.page === modelData[0]
                    width: 180; height: 44
                    Rectangle {
                        width: 3; height: parent.height
                        color: parent.current ? win.accent : "transparent"
                    }
                    Text {
                        x: 19; anchors.verticalCenter: parent.verticalCenter
                        text: win.tr[modelData[1]]
                        font.family: Theme.font; font.pixelSize: 14
                        color: parent.current ? "white" : Theme.muted
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: win.page = modelData[0]
                    }
                }
            }
        }

        // --- sayfalar --------------------------------------------------------
        Loader {
            anchors.fill: parent
            source: win.page === "led" ? "LedPage.qml"
                  : win.page === "settings" ? "SettingsPage.qml"
                  : win.page === "power" ? "PowerPage.qml"
                  : win.page === "fancurve" ? "FanCurvePage.qml" : "MonitorPage.qml"
        }

        // --- hata bildirimi --------------------------------------------------
        Rectangle {
            id: toast
            property string message
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height - 64
            width: toastText.implicitWidth + 40; height: 40; radius: 20
            color: "#1a0d12"; border.color: Theme.red; border.width: 1
            opacity: 0
            Text {
                id: toastText
                anchors.centerIn: parent
                text: toast.message
                font.family: Theme.font; font.pixelSize: 13; color: Theme.text
            }
            SequentialAnimation {
                id: toastAnim
                NumberAnimation { target: toast; property: "opacity"; to: 1; duration: 150 }
                PauseAnimation { duration: 3500 }
                NumberAnimation { target: toast; property: "opacity"; to: 0; duration: 400 }
            }
            Connections {
                target: win.bridge
                function onError(msg) { toast.message = msg; toastAnim.restart() }
            }
        }
    }

    Shortcut { sequences: [StandardKey.Quit, "Ctrl+W", "Escape"]; onActivated: Qt.quit() }
    Shortcut { sequence: "Ctrl+1"; onActivated: win.page = "monitor" }
    Shortcut { sequence: "Ctrl+2"; onActivated: win.page = "led" }
    Shortcut { sequence: "Ctrl+3"; onActivated: win.page = "settings" }
    Shortcut { sequence: "Ctrl+4"; onActivated: win.page = "power" }
}
