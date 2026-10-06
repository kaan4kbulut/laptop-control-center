import QtQuick
import QtQuick.Dialogs
import QtQuick.Effects

// LED Klavye: yarım daire renk paleti, klavye önizlemesi, 5 kademeli parlaklık.
Item {
    id: page
    readonly property var tr: win.tr
    readonly property var dk: win.desk
    readonly property int kmax: win.info.kbdMax || 0
    readonly property var palette: ["ff3600", "ff8a00", "ffd000", "b6ff00", "22e55a", "00e5c0",
                                    "00c8ff", "2f6bff", "5a3dff", "a23dff", "ff2dd2", "ffffff"]
    readonly property string hex: (dk.kbdColorValue || "#ffffff").replace("#", "").toLowerCase()
    readonly property int level: kmax > 0 && dk.kbdBrightness !== null && dk.kbdBrightness !== undefined
                                 ? Math.round(dk.kbdBrightness / kmax * 4) : 0
    readonly property color col: "#" + hex
    readonly property color keyColor: level === 0 ? Theme.line
                                      : Qt.rgba(col.r, col.g, col.b, [0, 0.3, 0.5, 0.75, 1][level])

    function setColor(h) { win.bridge.setDesk("kbdColorValue", "#" + h); win.bridge.run("keyboard", ["#" + h, -1]) }
    function setLevel(i) {
        const v = Math.round(i * kmax / 4)
        win.bridge.setDesk("kbdBrightness", v)
        win.bridge.run("keyboard", ["", v])
    }

    SvgLine { path: "M 430 160 A 240 240 0 0 0 430 640"; color: "#1b1f27" }
    SvgLine { path: "M 430 230 A 170 170 0 0 0 430 570 L 720 570 A 170 170 0 0 0 720 230 Z"; color: "#1b1f27"; fill: "black" }

    Row {
        x: 230; y: 92; spacing: 12
        Icon {
            width: 30; height: 30; stroke: 1.4; color: Theme.text
            path: "M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: page.tr["nav.led"]; font.family: Theme.font; font.pixelSize: 26; font.weight: Font.Light
            color: Theme.text
        }
    }

    // --- renk paleti: merkez (430,400), yarıçap 205, soldaki yarım daire --------
    Repeater {
        model: page.palette
        Item {
            id: sw
            required property string modelData
            required property int index
            readonly property real t: (90 + index * 180 / (page.palette.length - 1)) * Math.PI / 180
            readonly property bool on: page.hex === modelData
            x: 430 + 205 * Math.cos(t) - 19; y: 400 - 205 * Math.sin(t) - 19
            width: 38; height: 38
            enabled: page.dk.kbdColorValue !== null && page.dk.kbdColorValue !== undefined && win.info.kbdColor
            opacity: enabled ? 1 : 0.35
            Accessible.role: Accessible.RadioButton
            Accessible.name: page.tr["color." + modelData]
            RectangularShadow {
                anchors.fill: dot; radius: 19
                blur: sw.on ? 16 : 6; color: "#" + sw.modelData
                opacity: sw.on ? 1 : 0.4
            }
            Rectangle {
                id: dot
                anchors.fill: parent; radius: 19
                color: "#" + sw.modelData
                border.width: sw.on ? 3 : 2; border.color: sw.on ? "white" : Theme.bg
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.setColor(sw.modelData) }
        }
    }

    Column {
        x: 470; y: 300; width: 230; spacing: 14
        Pill {
            label: page.tr["led.color.custom"]
            enabled: win.info.kbdColor === true
            opacity: enabled ? 1 : 0.35
            checked: page.palette.indexOf(page.hex) < 0
            onClicked: picker.open()
        }
    }
    ColorDialog {
        id: picker
        selectedColor: page.col
        onAccepted: page.setColor(selectedColor.toString().replace("#", "").slice(-6))
    }

    // --- klavye önizlemesi --------------------------------------------------
    Item {
        id: kb
        x: 820; y: 210; width: 400; height: 300
        layer.enabled: page.level > 0
        layer.effect: MultiEffect {
            shadowEnabled: true; shadowColor: page.col
            shadowBlur: 0.3 + page.level * 0.15; shadowOpacity: 0.3 + page.level * 0.15
            shadowHorizontalOffset: 0; shadowVerticalOffset: 0
            autoPaddingEnabled: true
        }
        Rectangle {
            id: frame
            width: 400; height: keys.height + 52; radius: 14
            color: "transparent"; border.width: 2; border.color: page.keyColor
            Column {
                id: keys
                x: 20; y: 26; width: 360; spacing: 9
                Repeater {
                    model: [[40, 40, 40, 40, 40, 40, 40, 40, 40], [40, 40, 40, 40, 40, 40, 40, 40, 62],
                            [40, 40, 40, 40, 40, 40, 40, 40, 40], [40, 40, 180, 40, 40, 40]]
                    Row {
                        id: krow
                        required property var modelData
                        readonly property real k: (360 - 8 * (modelData.length - 1)) / modelData.reduce((a, b) => a + b, 0)
                        spacing: 8
                        Repeater {
                            model: krow.modelData
                            Rectangle {
                                required property int modelData
                                width: modelData * krow.k; height: 36; radius: 5
                                color: "transparent"; border.width: 1.5; border.color: page.keyColor
                            }
                        }
                    }
                }
            }
        }
        // touchpad yuvası
        Rectangle {
            x: 120; y: 230; width: 160; height: 62
            color: "transparent"; border.width: 2; border.color: page.keyColor
            bottomLeftRadius: 14; bottomRightRadius: 14
            Rectangle { width: parent.width - 4; x: 2; height: 2; color: Theme.bg }
        }
    }
    Row {
        x: 820 + (400 - width) / 2; y: 520; spacing: 6
        Text { id: selLabel; text: page.tr["led.color.selected"]; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
        Text {
            anchors.baseline: selLabel.baseline
            text: page.tr["color." + page.hex] || page.tr["led.color.custom"].replace("…", "") + " #" + page.hex
            font.family: Theme.digits; font.pixelSize: 15; font.weight: Font.DemiBold; color: Theme.text
        }
    }

    // --- parlaklık ----------------------------------------------------------
    Item {
        x: 860; y: 600; width: 320; height: 100
        enabled: page.kmax > 0 && page.dk.kbdBrightness !== null && page.dk.kbdBrightness !== undefined
        opacity: enabled ? 1 : 0.35
        Text {
            width: parent.width; horizontalAlignment: Text.AlignHCenter
            text: page.tr["led.brightness"]; font.family: Theme.font; font.pixelSize: 14; color: Theme.text
        }
        Item {
            y: 30; width: parent.width; height: 44
            Rectangle { x: 22; y: 20; width: parent.width - 44; height: 3; color: Theme.line }
            RectangularShadow {
                anchors.fill: fill; blur: 8; color: Theme.purple; visible: page.level > 0
            }
            Rectangle {
                id: fill
                x: 22; y: 20; height: 3; width: page.level * 69; color: Theme.purple
                Behavior on width { NumberAnimation { duration: 150 } }
            }
            Repeater {
                model: 5
                Item {
                    id: lv
                    required property int index
                    readonly property bool on: page.level === index
                    x: index * 69; width: 44; height: 44
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: page.tr["led.brightness"] + " " + index
                    RectangularShadow { anchors.fill: knob; radius: knob.radius; blur: 8; color: Theme.purple; visible: lv.on }
                    Rectangle {
                        id: knob
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: lv.on ? 10 : 17
                        width: lv.on ? 6 : 8; height: lv.on ? 22 : 8; radius: lv.on ? 2 : 4
                        color: lv.on ? "white" : "#5b6270"
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter; y: 34
                        text: lv.index; font.family: Theme.digits; font.pixelSize: 14; color: Theme.soft
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.setLevel(lv.index) }
                }
            }
        }
    }
}
