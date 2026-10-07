import QtQuick
import QtQuick.Effects

// Pil Tasarrufu: kademe seçimi, kademelere göre özellikler, parlaklık sınırları,
// anlık tüketim. Ayarlar config.json'a yazılır; uygulayan lcc-daemon'dur.
Item {
    id: page
    readonly property var tr: win.tr
    readonly property var lv: win.live
    readonly property var pw: win.desk.power || ({})
    readonly property var conf: pw.settings || ({})
    readonly property var avail: pw.available || ({})
    readonly property var features: ["refresh", "brightness", "wifi", "aspm", "services", "bluetooth", "kbd", "ecores", "dpms", "freeze"]
    readonly property var levels: ["saver", "ultra", "headless"]
    readonly property var capLevels: ["saver", "ultra"]

    function hours(h) {
        if (!h || h <= 0 || h > 48) return "–"
        const m = Math.round(h * 60)
        return Math.floor(m / 60) + (tr["app.title"] === "Control Center" ? " h " : " sa ") + (m % 60) + (tr["app.title"] === "Control Center" ? " min" : " dk")
    }
    function has(level, f) { return (conf[level] || []).indexOf(f) >= 0 }

    Row {
        x: 230; y: 92; spacing: 12
        Icon { width: 30; height: 30; stroke: 1.4; color: Theme.text; path: "M3 7h16v10H3zM21 10v4M7 10v4M10 10v4" }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: page.tr["nav.power"]; font.family: Theme.font; font.pixelSize: 26; font.weight: Font.Light
            color: Theme.text
        }
    }

    // --- kademe ---------------------------------------------------------------
    Row {
        x: 230; y: 160; spacing: 8
        Repeater {
            model: ["auto", "off", "saver", "ultra"]
            Pill {
                required property string modelData
                label: page.tr["power." + modelData]
                checked: (page.pw.requested || "auto") === modelData
                onClicked: win.bridge.run("powerLevel", [modelData])
            }
        }
    }
    Row {
        x: 230; y: 214; spacing: 6
        Text { id: nowLabel; text: page.tr["power.now"] + ":"; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
        Text {
            anchors.baseline: nowLabel.baseline
            text: page.tr["power." + (page.pw.level || "off")]
            font.family: Theme.digits; font.pixelSize: 17; font.weight: Font.DemiBold
            color: page.pw.level && page.pw.level !== "off" ? Theme.purple : Theme.text
        }
        Text {
            anchors.baseline: nowLabel.baseline
            text: "· " + (page.lv.onBattery ? page.tr["power.onbat"] : page.tr["power.onac"])
            font.family: Theme.font; font.pixelSize: 13; color: Theme.muted
        }
    }

    Text {
        x: 230; y: 236
        visible: page.conf.headless_on_lid !== false
        text: page.tr["power.headless.hint"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
    }

    // --- özellik tablosu ----------------------------------------------------------
    Repeater {
        model: page.levels
        Text {
            required property string modelData
            required property int index
            x: 630 + index * 80 - width / 2; y: 262
            text: page.tr["power." + modelData]
            font.family: Theme.font; font.pixelSize: 13; font.weight: Font.DemiBold; font.letterSpacing: 1
            color: page.pw.level === modelData ? Theme.purple : Theme.soft
        }
    }
    Rectangle { x: 230; y: 288; width: 560; height: 1; color: Theme.line }
    Repeater {
        model: page.features
        Item {
            id: row
            required property string modelData
            required property int index
            readonly property bool ok: page.avail[modelData] === true
            readonly property bool active: (page.pw.active || []).indexOf(modelData) >= 0
            x: 230; y: 296 + index * 41; width: 560; height: 40
            opacity: ok ? 1 : 0.4
            RectangularShadow {
                anchors.fill: act; radius: 4; blur: 8; color: Theme.purple; visible: row.active
            }
            Rectangle {
                id: act
                x: 0; y: 10; width: 8; height: 8; radius: 4
                color: row.active ? Theme.purple : "transparent"
                border.width: 1; border.color: row.active ? Theme.purple : "#3a404b"
            }
            Column {
                x: 22; y: 1
                Text {
                    text: page.tr["power.f." + row.modelData]
                    font.family: Theme.font; font.pixelSize: 15; color: Theme.text
                }
                Text {
                    text: page.tr["power.f." + row.modelData + ".hint"]
                    font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
                }
            }
            Repeater {
                model: page.levels
                Item {
                    id: cell
                    required property string modelData
                    required property int index
                    readonly property bool on: page.has(modelData, row.modelData)
                    x: 400 + index * 80 - 20; y: 0; width: 40; height: 40
                    Accessible.role: Accessible.CheckBox
                    Accessible.name: page.tr["power." + modelData] + " " + page.tr["power.f." + row.modelData]
                    RectangularShadow { anchors.fill: box; radius: 8; blur: 10; color: Theme.purple; visible: cell.on && row.ok }
                    Rectangle {
                        id: box
                        anchors.centerIn: parent; width: 16; height: 16; radius: 8
                        color: cell.on ? Theme.purple : Theme.bg
                        border.width: 2; border.color: cell.on ? "#c9a6ff" : "#3a404b"
                    }
                    MouseArea {
                        anchors.fill: parent; enabled: row.ok
                        cursorShape: Qt.PointingHandCursor
                        onClicked: win.bridge.run("powerFeature", [cell.modelData, row.modelData, !cell.on])
                    }
                }
            }
        }
    }

    // --- sağ: otomatik, parlaklık sınırları, tüketim --------------------------------
    Column {
        x: 860; y: 160; width: 360; spacing: 0
        RadioOption {
            x: -8
            label: page.tr["power.auto.label"]; accent: Theme.purple; dot: 16; fontSize: 14
            checked: page.conf.auto !== false
            onClicked: win.bridge.run("powerAuto", [!checked])
        }
        Text {
            leftPadding: 30; width: 360; wrapMode: Text.WordWrap
            text: page.tr["power.auto.hint"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
        Item { width: 1; height: 40 }
        Section { title: page.tr["power.cap"]; icon: "M20 12a8 8 0 1 1-16 0a8 8 0 1 1 16 0M12 4a8 8 0 0 1 0 16z" }
        Item { width: 1; height: 22 }
        Repeater {
            model: page.capLevels
            Column {
                id: capCol
                required property string modelData
                width: 360; spacing: 10
                property real shown: ((page.conf.brightness_cap || {})[modelData]) || 50
                Row {
                    spacing: 8
                    Text { id: capName; text: page.tr["power." + capCol.modelData]; font.family: Theme.font; font.pixelSize: 14; color: Theme.text }
                    Text {
                        anchors.baseline: capName.baseline
                        text: "%" + Math.round(capSlider.live)
                        font.family: Theme.digits; font.pixelSize: 16; font.weight: Font.DemiBold; color: Theme.text
                    }
                }
                LineSlider {
                    id: capSlider
                    width: parent.width
                    value: capCol.shown
                    enabled: page.avail.brightness === true
                    onCommitted: (v) => { capCol.shown = Math.max(5, v); win.bridge.run("powerCap", [capCol.modelData, Math.max(5, v)]) }
                }
            }
        }
        Item { width: 1; height: 20 }
        Row {
            spacing: 60
            Column {
                Readout {
                    value: page.lv.onBattery && page.lv.batteryPower ? Number(page.lv.batteryPower).toFixed(1) : "–"
                    unit: "W"; size: 40; unitSize: 15
                }
                Text { text: page.tr["power.draw"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
            }
            Column {
                Readout { value: page.hours(page.lv.batteryHours); unit: ""; size: 40 }
                Text { text: page.tr["power.left"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
            }
        }
        // Öğrenilmiş mod farklarıyla, şu anki yükte öbür modlarda kalan süre.
        Column {
            id: byMode
            readonly property var est: page.lv.batteryModes || ({})
            readonly property var shown: (win.info.modes || []).filter(m => est[m] !== undefined)
            visible: page.lv.onBattery && shown.length > 1
            topPadding: 18; spacing: 4
            Text { text: page.tr["power.bymode"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim; bottomPadding: 2 }
            Repeater {
                model: byMode.shown
                Row {
                    required property string modelData
                    readonly property bool current: page.lv.mode === modelData
                    spacing: 8
                    Text {
                        id: modeName; width: 130
                        text: page.tr["mode." + modelData]
                        font.family: Theme.font; font.pixelSize: 14; color: parent.current ? Theme.purple : Theme.text
                    }
                    Text {
                        anchors.baseline: modeName.baseline
                        text: page.hours(byMode.est[modelData])
                        font.family: Theme.digits; font.pixelSize: 16; font.weight: Font.DemiBold
                        color: parent.current ? Theme.purple : Theme.text
                    }
                }
            }
        }
        Text {
            topPadding: 14; width: 360; wrapMode: Text.WordWrap
            visible: page.pw.helper === false
            text: page.tr["power.helper.missing"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.pink
        }
    }
}
