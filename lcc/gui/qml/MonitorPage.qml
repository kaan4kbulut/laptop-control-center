import QtQuick
import QtQuick.Effects
import QtQuick.Shapes

// Sistem İzleme: işlemci frekansı/sıcaklığı, disk/RAM, mod ve fan seçimi.
Item {
    id: page
    readonly property var lv: win.live
    readonly property var tr: win.tr
    readonly property var inf: win.info
    readonly property real scaleMax: 6000      // MHz; yay 0–6 GHz

    function n(v, d) { return v === undefined || v === null ? "–" : Number(v).toFixed(d || 0) }
    function frac(v, max) { return v ? Math.max(0, Math.min(1, v / max)) : 0 }

    // --- donanım adları --------------------------------------------------------
    Column {
        x: 230; y: 72
        Repeater {
            model: [page.inf.cpuName || "", page.inf.gpuName || ""]
            Text {
                required property string modelData
                text: modelData; height: 22
                font.family: Theme.font; font.pixelSize: 14; color: Theme.text2
            }
        }
    }

    // --- modlar ----------------------------------------------------------------
    Row {
        id: modeRow
        anchors.right: parent.right; anchors.rightMargin: 36
        y: 84; spacing: 10
        Repeater {
            // Pil tasarrufu yalnızca pilde kendiliğinden gelir; etkinse o da görünür.
            model: (page.inf.modes || []).filter(m => m !== "powersave" || page.lv.mode === m)
            delegate: Item {
                id: mb
                required property string modelData
                readonly property bool on: page.lv.mode === modelData
                width: content.implicitWidth + 44; height: 44
                RectangularShadow {
                    anchors.fill: frame; radius: frame.radius
                    blur: 14; spread: 0; color: Theme.cyan
                    visible: mb.on
                }
                Rectangle {
                    id: frame
                    anchors.fill: parent; radius: 22
                    color: mb.on ? "#07141c" : Theme.bg
                    border.width: 2; border.color: mb.on ? Theme.cyan : "transparent"
                }
                Row {
                    id: content
                    anchors.centerIn: parent; spacing: 10
                    Icon {
                        anchors.verticalCenter: parent.verticalCenter
                        color: mb.on ? "white" : Theme.soft
                        path: ({
                            performance: "M4 16a8 8 0 1 1 16 0M12 16l5-6M6.5 11.5l1 .6M12 8v1.2M17.5 11.5l-1 .6",
                            balanced: "M10 3l1.8 5.2L17 10l-5.2 1.8L10 17l-1.8-5.2L3 10l5.2-1.8zM18 14l.8 2.2L21 17l-2.2.8L18 20l-.8-2.2L15 17l2.2-.8z",
                            quiet: "M8 7a7 7 0 0 0 0 10M5 4.5a11 11 0 0 0 0 15M15 12a2 2 0 1 1-4 0a2 2 0 1 1 4 0",
                            powersave: "M3 7h16v10H3zM21 10v4M7 10v4M10 10v4"
                        })[mb.modelData] || ""
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: page.tr["mode." + mb.modelData]
                        font.family: Theme.font; font.pixelSize: 15
                        color: mb.on ? "white" : Theme.soft
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: win.bridge.run("mode", [mb.modelData])
                }
            }
        }
    }
    Row {
        anchors.right: parent.right; anchors.rightMargin: 40
        y: 136; spacing: 5
        visible: !!page.lv.mode
        Text { id: limLabel; text: page.tr["cpu.limit"]; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
        Text {
            anchors.baseline: limLabel.baseline
            text: page.lv.pl1 ? page.n(page.lv.pl1) + " W" : "–"
            font.family: Theme.digits; font.pixelSize: 16; font.weight: Font.DemiBold; color: Theme.text
        }
        Text {
            anchors.baseline: limLabel.baseline
            text: "· " + (page.tr["mode.note." + page.lv.mode] || "")
            font.family: Theme.font; font.pixelSize: 13; color: Theme.muted
        }
    }

    // --- işlemci frekansı yayı (merkez 560,370) ---------------------------------
    ArcRing {
        cx: 560; cy: 370; radius: 280; thickness: 3
        startAngle: 128.2; sweep: 103.6
        gradient: LinearGradient {
            x1: 0; y1: 590; x2: 0; y2: 150
            GradientStop { position: 0; color: Theme.cyan }
            GradientStop { position: 0.6; color: Theme.purple }
            GradientStop { position: 1; color: Theme.red }
        }
    }
    ArcRing {
        cx: 560; cy: 370; radius: 250; thickness: 40
        startAngle: 125; sweep: 110; color: Theme.track
    }
    // Parlama: aynı yayın bulanık kopyası (Glow içinde sıfırdan başlayan yay çizilmiyordu).
    Glow {
        strength: 0.6; sharp: false
        ArcRing {
            cx: 560; cy: 370; radius: 250; thickness: 40
            startAngle: 125; sweep: freqArc.sweep; color: "#1a8cff"
        }
    }
    ArcRing {
        id: freqArc
        cx: 560; cy: 370; radius: 250; thickness: 40
        startAngle: 125
        sweep: 110 * page.frac(page.lv.cpuFreq, page.scaleMax)
        Behavior on sweep { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }
        gradient: LinearGradient {
            x1: 0; y1: 575; x2: 0; y2: 165
            GradientStop { position: 0; color: "#0a4dff" }
            GradientStop { position: 1; color: "#22d3ff" }
        }
    }
    SvgLine { path: "M 310 370 L 500 330"; color: "#3a7bff" }
    Repeater {
        model: [[383, 597], [318, 533], [275, 451], [260, 360], [275, 269], [318, 187], [383, 122]]
        Text {
            required property var modelData
            required property int index
            x: modelData[0]; y: modelData[1]
            text: index
            font.family: Theme.digits; font.pixelSize: 14
            color: index === 6 ? Theme.pink : Theme.soft
        }
    }
    Text { x: 372; y: 628; text: page.tr["unit.ghz"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }

    Column {
        x: 400; y: 196
        Text { text: page.tr["cpu.freq"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
        Readout { value: page.n(page.lv.cpuFreq); unit: "MHz"; size: 48; unitSize: 14 }
    }
    Text {
        x: 470; y: 330; text: "CPU"
        font.family: Theme.font; font.pixelSize: 40; font.weight: Font.Light; font.letterSpacing: 2
        color: Theme.text
    }
    Column {
        x: 520; y: 412
        Readout { value: page.n(page.lv.cpuTemp); unit: "°C"; size: 46; unitSize: 15 }
        Text { text: page.tr["cpu.temp"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
    }

    // --- sıcaklık yayı: altta 0 °C, üstte 100 °C ---------------------------------
    ArcRing { cx: 560; cy: 370; radius: 200; thickness: 2; startAngle: -60; sweep: 120; color: Theme.line }
    ArcRing {
        cx: 560; cy: 370; radius: 200; thickness: 2; startAngle: 60
        sweep: -120 * page.frac(page.lv.cpuTemp, 100)
        color: (page.lv.cpuTemp || 0) >= 90 ? Theme.pink : Theme.text
        Behavior on sweep { NumberAnimation { duration: 600 } }
    }
    Text { x: 618; y: 186; text: "100 °C"; font.family: Theme.font; font.pixelSize: 11; color: Theme.dim }
    Text { x: 626; y: 540; text: "0 °C"; font.family: Theme.font; font.pixelSize: 11; color: Theme.dim }

    // --- disk (üst yarı) ve RAM (alt yarı) --------------------------------------
    ArcRing { cx: 573.8; cy: 370; radius: 245; thickness: 10; startAngle: -59; sweep: 118; color: Theme.line }
    ArcRing {
        cx: 573.8; cy: 370; radius: 245; thickness: 10; startAngle: -59
        sweep: 59 * page.frac(page.lv.disk, 100); color: Theme.text
    }
    ArcRing {
        cx: 573.8; cy: 370; radius: 245; thickness: 10; startAngle: 59
        sweep: -59 * page.frac(page.lv.mem, 100); color: Theme.text
        Behavior on sweep { NumberAnimation { duration: 600 } }
    }
    Column {
        x: 828; y: 230
        Text {
            text: page.tr["disk.label"].replace("{gb}", page.n(page.lv.diskTotal))
            font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
        Readout { value: page.n(page.lv.disk); unit: "%" }
    }
    Column {
        x: 828; y: 440
        Readout { value: page.n(page.lv.mem); unit: "%" }
        Text {
            text: page.tr["mem.label"].replace("{gb}", page.n(page.lv.memTotal))
            font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
    }

    // --- fan modu ---------------------------------------------------------------
    Glow {
        strength: 0.35; blur: 0.6; sharp: false
        SvgLine { path: "M 923.7 160 A 420 420 0 0 1 904 610.9"; color: Theme.cyan; width_: 8 }
    }
    SvgLine { path: "M 923.7 160 A 420 420 0 0 1 904 610.9"; color: Theme.cyan; width_: 2.5 }
    SvgLine { path: "M 935 205 L 1150 205"; color: Theme.cyan; width_: 1.5 }
    Text {
        x: 940; y: 166; text: page.tr["fan.control"]; lineHeight: 1.2
        font.family: Theme.font; font.pixelSize: 13; font.weight: Font.DemiBold; font.letterSpacing: 1.5
        color: Theme.text
    }
    Repeater {
        model: [["auto", 950, 230], ["silent", 966, 301], ["max", 970, 374], ["custom", 961, 447]]
        RadioOption {
            required property var modelData
            x: modelData[1]; y: modelData[2]
            label: page.tr["fan." + modelData[0]]
            checked: page.lv.fan === modelData[0]
            enabled: (page.inf.fanModes || []).indexOf(modelData[0]) >= 0
            onClicked: win.bridge.run("fan", [modelData[0]])
        }
    }

    Text {
        x: 1000; y: 505
        visible: !!page.inf.fanCurves
        text: page.tr["fan.curve.edit"]
        font.family: Theme.font; font.pixelSize: 12
        color: curveLink.containsMouse ? "white" : Theme.cyan
        MouseArea {
            id: curveLink
            anchors.fill: parent; anchors.margins: -8
            hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: win.page = "fancurve"
        }
    }

    // --- kullanım ve ekran kartı -----------------------------------------------
    Item {
        x: 230; y: 660; width: 300; height: 8
        clip: true
        Repeater {
            model: 46
            Rectangle {
                required property int index
                x: index * 7 - 4; y: -6; width: 3; height: 20
                rotation: 25
                color: index / 43 < page.frac(page.lv.cpuUsage, 100) ? Theme.cyan : "#3a404b"
            }
        }
    }
    Repeater {
        model: [["cpu.usage", 674, page.lv.cpuUsage], ["gpu.usage", 712, page.lv.gpuSleeping ? 0 : page.lv.gpuUsage]]
        Item {
            required property var modelData
            x: 230; y: modelData[1]; width: 300; height: 20
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: page.tr[modelData[0]]; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted
            }
            Text {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                text: page.n(modelData[2]) + " %"
                font.family: Theme.digits; font.pixelSize: 16; font.weight: Font.DemiBold; color: Theme.text
            }
        }
    }
    Column {
        x: 580; y: 652; width: 180
        visible: !!page.inf.gpuName
        Text {
            width: parent.width; horizontalAlignment: Text.AlignHCenter
            text: page.lv.gpuSleeping ? page.tr["gpu.sleeping"] : page.n(page.lv.gpuUsage) + " %"
            font.family: Theme.digits; font.pixelSize: 22; font.weight: Font.DemiBold; color: Theme.text
        }
        Text {
            width: parent.width; horizontalAlignment: Text.AlignHCenter
            text: page.tr["gpu.short"] + (page.lv.gpuTemp ? " · " + page.n(page.lv.gpuTemp) + " °C" : "")
            font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
        Text {
            width: parent.width; horizontalAlignment: Text.AlignHCenter
            visible: !!page.lv.gpuPowerLimit
            text: page.tr["gpu.limit.upto"].replace("{w}", page.n(page.lv.gpuPowerLimit))
            font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
    }

    Row {
        x: 860; y: 640; spacing: 44
        Repeater {
            model: [["cpu", "fan.cpu"], ["gpu", "fan.gpu"]]
            Row {
                id: fanItem
                required property var modelData
                readonly property var speed: (page.lv.fans || {})[modelData[0]]
                visible: speed !== undefined
                spacing: 12
                Icon {
                    width: 44; height: 44; viewBox: 44; color: Theme.dim
                    path: "M26 22a4 4 0 1 1-8 0a4 4 0 1 1 8 0M22 18c0-8 6-12 10-9s-2 9-8 11M26 22c8 0 12 6 9 10s-9-2-11-8M22 26c0 8-6 12-10 9s2-9 8-11M18 22c-8 0-12-6-9-10s9 2 11 8"
                    RotationAnimator on rotation {
                        from: 0; to: 360; loops: Animation.Infinite
                        duration: 600 + 4000 * (1 - Math.min(1, (fanItem.speed || 0) / 100))
                        running: (fanItem.speed || 0) > 0
                    }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Readout { value: page.n(fanItem.speed); unit: "%" }
                    Text { text: page.tr[modelData[1]]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim }
                }
            }
        }
    }
}
