import QtQuick
import QtQuick.Effects
import QtQuick.Shapes

// Yapılandırma: yay üzerindeki anahtarlar, ekran kartı modu, şarj sınırı ve
// alttaki üç kaydırıcı (gece ışığı, ses, ekran parlaklığı).
Item {
    id: page
    readonly property var tr: win.tr
    readonly property var dk: win.desk
    // [anahtar, desk alanı, bridge komutu (yoksa yalnızca gösterge)]
    readonly property var toggles: [
        ["fnlock", "fnlock", "fnlock"], ["touchpad", "touchpad", "touchpad"],
        ["airplane", "airplane", "airplane"], ["mic", "mic", "mic"],
        ["numlock", "numlock", ""], ["capslock", "capslock", ""]
    ]
    property string sel: "touchpad"
    readonly property var selDef: toggles.find(t => t[0] === sel)
    readonly property var selVal: dk[selDef[1]]

    function hintKey(id) { return id === "numlock" || id === "capslock" ? "toggle.indicator.hint" : "toggle." + id + ".hint" }

    // --- sol: siyah D biçimli alan ve mor yay (merkez 330,380) ---------------
    SvgLine { path: "M 120 130 L 330 130 A 250 250 0 0 1 330 630 L 120 630"; color: "#1b1f27"; fill: "black" }
    Glow {
        strength: 0.3; blur: 0.6; sharp: false
        ArcRing { cx: 330; cy: 380; radius: 250; thickness: 9; startAngle: -50; sweep: 100; color: Theme.purple }
    }
    ArcRing { cx: 330; cy: 380; radius: 250; thickness: 3; startAngle: -50; sweep: 100; color: Theme.purple }

    Row {
        x: 230; y: 300; spacing: 24
        Grid {
            columns: 2; spacing: 6
            anchors.verticalCenter: parent.verticalCenter
            Repeater {
                model: 4
                Rectangle {
                    required property int index
                    width: 45; height: 44; radius: 4
                    border.width: 2; border.color: Theme.text
                    gradient: index === 0 && page.selVal === true ? selGrad : null
                    color: "transparent"
                    Gradient { id: selGrad; GradientStop { position: 0; color: "white" } GradientStop { position: 1; color: "#5b6270" } }
                }
            }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            Text { text: page.tr["toggle." + page.sel]; font.family: Theme.font; font.pixelSize: 15; color: Theme.text }
            Text {
                topPadding: 6
                text: page.selVal === true ? page.tr["state.on"] : page.selVal === false ? page.tr["state.off"] : "–"
                font.family: Theme.digits; font.pixelSize: 32; font.weight: Font.DemiBold; color: Theme.text
            }
            Text {
                topPadding: 4; width: 170; wrapMode: Text.WordWrap
                text: page.tr[page.hintKey(page.sel)]
                font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
            }
        }
    }

    Repeater {
        model: page.toggles
        Item {
            id: tg
            required property var modelData
            required property int index
            readonly property real deg: 42 - index * 84 / (page.toggles.length - 1)
            readonly property var val: page.dk[modelData[1]]
            readonly property bool on: val === true
            readonly property bool known: val === true || val === false
            x: 330 + 250 * Math.cos(deg * Math.PI / 180) - 12
            y: 380 - 250 * Math.sin(deg * Math.PI / 180) - 22
            width: label.x + label.implicitWidth + 8; height: 44
            opacity: known ? 1 : 0.4
            RectangularShadow {
                anchors.fill: dot; radius: 8; blur: 10; color: Theme.purple; visible: tg.on
            }
            Rectangle {
                id: dot
                x: 4; anchors.verticalCenter: parent.verticalCenter
                width: 16; height: 16; radius: 8
                color: tg.on ? Theme.purple : Theme.bg
                border.width: 2; border.color: tg.on ? "#c9a6ff" : "#3a404b"
            }
            Text {
                id: label
                x: 34; anchors.verticalCenter: parent.verticalCenter
                text: page.tr["toggle." + tg.modelData[0]]
                font.family: Theme.font; font.pixelSize: 15
                font.weight: page.sel === tg.modelData[0] ? Font.DemiBold : Font.Normal
                color: tg.on ? "white" : Theme.faint
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    page.sel = tg.modelData[0]
                    if (tg.known && tg.modelData[2]) {
                        win.bridge.setDesk(tg.modelData[1], !tg.on)
                        win.bridge.run(tg.modelData[2], [!tg.on])
                    }
                }
            }
        }
    }

    // --- sağ: ekran kartı modu ve şarj sınırı ------------------------------------
    Column {
        x: 860; y: 250; width: 360; spacing: 0
        Section {
            title: page.tr["gpu.mode"]
            icon: "M6 6h12v12H6zM9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"
        }
        Item { width: 1; height: 18 }
        RadioOption { label: page.tr["gpu.mode.dgpu"]; enabled: false; accent: Theme.purple; dot: 16; fontSize: 14 }
        RadioOption { label: page.tr["gpu.mode.hybrid"]; checked: true; enabled: false; accent: Theme.purple; dot: 16; fontSize: 14 }
        Text {
            leftPadding: 38; width: 360; wrapMode: Text.WordWrap; lineHeight: 1.3
            text: page.tr["gpu.mode.note"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
        Item { width: 1; height: 36 }
        Section { title: page.tr["charge.title"]; icon: "M3 7h16v10H3zM21 10v4M7 10v4M10 10v4" }
        Item { width: 1; height: 18 }
        Flow {
            width: 360; spacing: 8
            enabled: page.dk.chargeEnd !== null && page.dk.chargeEnd !== undefined
            opacity: enabled ? 1 : 0.35
            Repeater {
                model: win.info.chargeEnd || []
                Pill {
                    required property int modelData
                    label: modelData === 100 ? page.tr["charge.full"] : "%" + modelData
                    checked: page.dk.chargeEnd === modelData
                    onClicked: { win.bridge.setDesk("chargeEnd", modelData); win.bridge.run("chargeEnd", [modelData]) }
                }
            }
        }
        Text {
            topPadding: 10; width: 360; wrapMode: Text.WordWrap; lineHeight: 1.3
            text: page.tr["charge.note"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
    }

    // --- alt: üç kaydırıcı --------------------------------------------------
    Row {
        x: 190; y: 664; spacing: 60
        Repeater {
            model: [
                ["night", "night", "M17 12a5 5 0 1 1-10 0a5 5 0 1 1 10 0M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"],
                ["volume", "volume", "M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11"],
                ["brightness", "screen.brightness", "M20 12a8 8 0 1 1-16 0a8 8 0 1 1 16 0M12 4a8 8 0 0 1 0 16z"]
            ]
            Column {
                id: sl
                required property var modelData
                readonly property var val: page.dk[modelData[0]]
                width: 310; spacing: 10
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter; spacing: 8
                    Icon { width: 18; height: 18; stroke: 1.5; color: Theme.text; path: sl.modelData[2] }
                    Text { text: page.tr[sl.modelData[1]]; font.family: Theme.font; font.pixelSize: 14; color: Theme.text }
                }
                LineSlider {
                    width: parent.width
                    // gece ışığı kapalıyken hyprsunset çalışmıyor olabilir; yine de ayarlanabilir
                    enabled: sl.val !== null && sl.val !== undefined || sl.modelData[0] === "night"
                    value: sl.val || 0
                    leftLabel: sl.modelData[0] === "night" ? page.tr["night.off"] : "0"
                    rightLabel: sl.modelData[0] === "night" ? page.tr["night.warm"] : "100"
                    onMoved: (v) => win.bridge.setDesk(sl.modelData[0], v)
                    onCommitted: (v) => { win.bridge.setDesk(sl.modelData[0], v); win.bridge.run(sl.modelData[0], [v]) }
                }
            }
        }
    }
}
