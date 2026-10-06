import QtQuick
import QtQuick.Effects

// Fan Eğrisi: Özel fan modunun (sıcaklık → hız) eğrisi. Sıcaklıklar sabit, hızlar
// sürüklenir; eğri hiçbir yerde azalmaz. Modların Otomatik eğrileri karşılaştırma için
// soluk çizilir; şu anki sıcaklık ve fan hızı işaretlenir.
Item {
    id: page
    readonly property var tr: win.tr
    readonly property var lv: win.live
    readonly property var curves: win.info.fanCurves || ({})
    readonly property var defaults: [[20, 0], [40, 15], [50, 25], [60, 35], [70, 50], [80, 70], [90, 90], [100, 100]]
    property var points: JSON.parse(JSON.stringify(curves.custom || defaults))
    property string status: ""          // "", "saving", "saved"
    readonly property bool dirty: JSON.stringify(points) !== JSON.stringify(curves.custom || defaults)

    // grafik alanı
    readonly property real gx: 280
    readonly property real gw: 620
    readonly property real gy: 220
    readonly property real gh: 400
    readonly property real tmin: 20
    readonly property real tmax: 100
    function px(t) { return gx + (t - tmin) / (tmax - tmin) * gw }
    function py(v) { return gy + gh - v / 100 * gh }

    readonly property var refs: [["performance", Theme.cyan], ["balanced", Theme.soft], ["quiet", Theme.faint]]

    onCurvesChanged: {
        if (status === "saving") { status = "saved"; savedTimer.restart() }
        if (!dirty) points = JSON.parse(JSON.stringify(curves.custom || defaults))
    }
    Timer { id: savedTimer; interval: 4000; onTriggered: page.status = "" }
    Connections {
        target: win.bridge
        function onError(msg) { if (page.status === "saving") page.status = "" }
    }

    function setSpeed(i, v) {
        const p = JSON.parse(JSON.stringify(points))
        v = Math.max(0, Math.min(100, Math.round(v)))
        p[i][1] = v
        // eğri azalmasın: soldakiler en çok bu kadar, sağdakiler en az bu kadar
        for (let k = i - 1; k >= 0; k--) p[k][1] = Math.min(p[k][1], v)
        for (let k = i + 1; k < p.length; k++) p[k][1] = Math.max(p[k][1], v)
        points = p
        canvas.requestPaint()
    }

    Row {
        x: 230; y: 92; spacing: 12
        Icon {
            width: 30; height: 30; stroke: 1.4; color: Theme.text; viewBox: 44
            path: "M26 22a4 4 0 1 1-8 0a4 4 0 1 1 8 0M22 18c0-8 6-12 10-9s-2 9-8 11M26 22c8 0 12 6 9 10s-9-2-11-8M22 26c0 8-6 12-10 9s2-9 8-11M18 22c-8 0-12-6-9-10s9 2 11 8"
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: page.tr["fancurve.title"]; font.family: Theme.font; font.pixelSize: 26; font.weight: Font.Light
            color: Theme.text
        }
    }
    Text {
        x: 230; y: 140; width: 680; wrapMode: Text.WordWrap
        text: page.tr["fancurve.hint"]; font.family: Theme.font; font.pixelSize: 13; color: Theme.dim
    }

    // --- ızgara, karşılaştırma eğrileri, özel eğri ------------------------------
    Canvas {
        id: canvas
        anchors.fill: parent
        property var watch: [page.points, page.curves, page.lv.cpuTemp]
        onWatchChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            ctx.lineWidth = 1
            ctx.strokeStyle = "#1b1f27"
            for (let t = 20; t <= 100; t += 10) {
                ctx.beginPath(); ctx.moveTo(page.px(t) + 0.5, page.gy); ctx.lineTo(page.px(t) + 0.5, page.gy + page.gh); ctx.stroke()
            }
            for (let v = 0; v <= 100; v += 20) {
                ctx.beginPath(); ctx.moveTo(page.gx, page.py(v) + 0.5); ctx.lineTo(page.gx + page.gw, page.py(v) + 0.5); ctx.stroke()
            }
            function curve(pts, color, width, alpha) {
                ctx.globalAlpha = alpha
                ctx.strokeStyle = color
                ctx.lineWidth = width
                ctx.lineJoin = "round"; ctx.lineCap = "round"
                ctx.beginPath()
                const sorted = pts.slice().sort((a, b) => a[0] - b[0])
                // eğrinin 20 °C'den önceki/100'den sonraki kısmı yatay sürer
                sorted.forEach((p, i) => {
                    const x = page.px(Math.max(page.tmin, Math.min(page.tmax, p[0]))), y = page.py(p[1])
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                })
                ctx.stroke()
                ctx.globalAlpha = 1
            }
            for (const r of page.refs) if (page.curves[r[0]]) curve(page.curves[r[0]], r[1], 1.5, 0.45)
            curve(page.points, Theme.purple, 10, 0.22)       // parlama
            curve(page.points, Theme.purple, 3, 1)
            // şu anki sıcaklık
            const t = page.lv.cpuTemp
            if (t) {
                const x = page.px(Math.max(page.tmin, Math.min(page.tmax, t)))
                ctx.setLineDash([4, 4]); ctx.strokeStyle = Theme.pink; ctx.lineWidth = 1
                ctx.beginPath(); ctx.moveTo(x + 0.5, page.gy); ctx.lineTo(x + 0.5, page.gy + page.gh); ctx.stroke()
                ctx.setLineDash([])
            }
        }
    }

    // eksen etiketleri
    Repeater {
        model: [20, 30, 40, 50, 60, 70, 80, 90, 100]
        Text {
            required property int modelData
            x: page.px(modelData) - width / 2; y: page.gy + page.gh + 10
            text: modelData; font.family: Theme.digits; font.pixelSize: 14; color: Theme.soft
        }
    }
    Text { x: page.gx + page.gw - width; y: page.gy + page.gh + 30; text: "°C"; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
    Repeater {
        model: [0, 20, 40, 60, 80, 100]
        Text {
            required property int modelData
            x: page.gx - width - 12; y: page.py(modelData) - height / 2
            text: modelData; font.family: Theme.digits; font.pixelSize: 14; color: Theme.soft
        }
    }
    Text { x: page.gx - 34; y: page.gy - 26; text: "%"; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }

    // şu anki fan hızı noktası
    Rectangle {
        readonly property var f: (page.lv.fans || {}).cpu
        visible: f !== undefined && !!page.lv.cpuTemp
        x: page.px(Math.max(page.tmin, Math.min(page.tmax, page.lv.cpuTemp || 0))) - 5
        y: page.py(f || 0) - 5
        width: 10; height: 10; radius: 5; color: Theme.pink
        Behavior on x { NumberAnimation { duration: 400 } }
        Behavior on y { NumberAnimation { duration: 400 } }
    }

    // sürüklenebilir noktalar
    Repeater {
        model: page.points.length
        Item {
            id: handle
            required property int index
            readonly property var pt: page.points[index]
            x: page.px(pt[0]) - 22; y: page.py(pt[1]) - 22
            width: 44; height: 44
            Accessible.role: Accessible.Slider
            Accessible.name: pt[0] + " °C"
            RectangularShadow { anchors.fill: knob; radius: 9; blur: 10; color: Theme.purple; visible: drag.pressed || drag.containsMouse }
            Rectangle {
                id: knob
                anchors.centerIn: parent
                width: 18; height: 18; radius: 9
                color: drag.pressed ? Theme.purple : Theme.bg
                border.width: 2.5; border.color: drag.pressed || drag.containsMouse ? "#c9a6ff" : Theme.purple
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                y: -10
                visible: drag.pressed || drag.containsMouse
                text: handle.pt[1] + " %"
                font.family: Theme.digits; font.pixelSize: 15; font.weight: Font.DemiBold; color: Theme.text
            }
            MouseArea {
                id: drag
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SizeVerCursor
                preventStealing: true
                onPositionChanged: (m) => {
                    if (!pressed) return
                    const yy = handle.y + m.y
                    page.setSpeed(handle.index, (page.gy + page.gh - yy) / page.gh * 100)
                }
            }
            WheelHandler {
                onWheel: (e) => page.setSpeed(handle.index, handle.pt[1] + (e.angleDelta.y > 0 ? 1 : -1))
            }
        }
    }

    // --- sağ sütun: açıklama, şu an, düğmeler --------------------------------------
    Column {
        x: 960; y: 220; width: 260; spacing: 14
        Row {
            spacing: 10
            Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 22; height: 3; color: Theme.purple }
            Text { text: page.tr["fancurve.custom"]; font.family: Theme.font; font.pixelSize: 14; color: Theme.text }
        }
        Text { text: page.tr["fancurve.compare"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim; topPadding: 4 }
        Repeater {
            model: page.refs
            Row {
                required property var modelData
                visible: !!page.curves[modelData[0]]
                spacing: 10
                Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 22; height: 2; color: modelData[1]; opacity: 0.6 }
                Text { text: page.tr["mode." + modelData[0]]; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
            }
        }
        Item { width: 1; height: 10 }
        Text { text: page.tr["fancurve.now"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
        Row {
            spacing: 28
            Column {
                Readout { value: page.lv.cpuTemp ? Number(page.lv.cpuTemp).toFixed(0) : "–"; unit: "°C" }
                Text { text: page.tr["cpu.temp"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
            }
            Column {
                Readout {
                    readonly property var f: (page.lv.fans || {}).cpu
                    value: f !== undefined ? Number(f).toFixed(0) : "–"; unit: "%"
                }
                Text { text: page.tr["fan.cpu"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
            }
        }
        Item { width: 1; height: 14 }
        Pill {
            width: 260
            label: page.status === "saving" ? page.tr["fancurve.saving"] : page.tr["fancurve.save"]
            checked: page.dirty || win.live.fan !== "custom"
            enabled: page.status !== "saving"
            onClicked: { page.status = "saving"; win.bridge.run("fanCurve", [page.points]) }
        }
        Pill {
            width: 260
            label: page.tr["fancurve.reset"]
            onClicked: { page.points = JSON.parse(JSON.stringify(page.defaults)); canvas.requestPaint() }
        }
        Pill {
            width: 260
            label: page.tr["fancurve.back"]
            onClicked: win.page = "monitor"
        }
        Text {
            width: 260; wrapMode: Text.WordWrap
            visible: page.status === "saved"
            text: page.tr["fancurve.saved"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.cyan
        }
    }
}
