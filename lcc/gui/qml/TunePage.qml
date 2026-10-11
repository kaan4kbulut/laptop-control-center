import QtQuick
import QtQuick.Effects

// Optimizasyon: sistem analizi (lcc/tune.py), tek tek veya toplu düzeltme,
// DNS sağlayıcı testi/seçimi ve internet hız testi.
Item {
    id: page
    readonly property var tr: win.tr
    readonly property var tn: win.desk.tune || ({})
    readonly property var checks: tn.checks || []
    readonly property var dns: tn.dns || null
    readonly property var speed: tn.speed || null
    readonly property string busy: tn.busy || ""
    readonly property var providers: [["auto", tr["tune.dns.auto"]]].concat(win.info.dnsProviders || [])
    readonly property real dnsMax: {
        if (!dns) return 1
        let m = 1
        for (const k in dns) m = Math.max(m, dns[k].uncached)
        return m
    }

    function stateColor(s) {
        return s === "ok" ? Theme.cyan : s === "warn" ? Theme.purple : s === "bad" ? Theme.pink : Theme.faint
    }
    function count(s) { return checks.filter(c => c.state === s).length }

    // --- başlık ---------------------------------------------------------------
    Row {
        x: 230; y: 92; spacing: 12
        Icon {
            width: 30; height: 30; stroke: 1.4; color: Theme.text
            path: "M4 20h16M6 16l4-6 4 3 5-8M19 5v4h-4"
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: page.tr["tune.title"]; font.family: Theme.font; font.pixelSize: 26; font.weight: Font.Light
            color: Theme.text
        }
    }

    Row {
        x: 230; y: 156; spacing: 8
        Pill {
            label: page.busy === "analyze" ? page.tr["tune.analyzing"] : page.tr["tune.analyze"]
            accent: Theme.cyan
            checked: page.busy === "analyze"
            onClicked: if (!page.busy) win.bridge.run("tuneAnalyze", [])
        }
        Pill {
            label: page.busy === "fixall" ? page.tr["tune.analyzing"] : page.tr["tune.fixall"]
            checked: page.busy === "fixall"
            opacity: page.checks.some(c => c.fix) ? 1 : 0.4
            onClicked: if (!page.busy && page.checks.some(c => c.fix)) win.bridge.run("tuneFixAll", [])
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            leftPadding: 10
            text: page.checks.length
                  ? page.tr["tune.summary"].replace("{bad}", page.count("bad")).replace("{warn}", page.count("warn")).replace("{ok}", page.count("ok"))
                  : page.tr["tune.never"]
            font.family: Theme.font; font.pixelSize: 13; color: Theme.muted
        }
    }

    Rectangle { x: 230; y: 214; width: 570; height: 1; color: Theme.line }

    // --- kontrol listesi --------------------------------------------------------
    Repeater {
        model: page.checks
        Item {
            id: row
            required property var modelData
            required property int index
            readonly property color tint: page.stateColor(modelData.state)
            x: 230; y: 222 + index * 47; width: 570; height: 46
            RectangularShadow {
                anchors.fill: dot; radius: 5; blur: 8; color: row.tint
                visible: row.modelData.state === "bad" || row.modelData.state === "warn"
            }
            Rectangle {
                id: dot
                x: 0; y: 9; width: 10; height: 10; radius: 5
                color: row.tint
            }
            Column {
                x: 22; y: 2; width: 270
                Text {
                    text: page.tr["tune." + row.modelData.id]
                    font.family: Theme.font; font.pixelSize: 15; color: Theme.text
                }
                Text {
                    width: parent.width; elide: Text.ElideRight
                    text: row.modelData.detail
                    font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
                }
            }
            Text {
                x: 295; y: 3; width: 190
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideLeft
                text: row.modelData.value
                font.family: Theme.digits; font.pixelSize: 16; font.weight: Font.DemiBold
                color: row.modelData.state === "ok" ? Theme.text : row.tint
            }
            Pill {
                x: 494; y: 4; height: 32; implicitWidth: 76
                visible: row.modelData.fix
                label: page.busy === "fix:" + row.modelData.id ? "…" : page.tr["tune.fix"]
                checked: page.busy === "fix:" + row.modelData.id
                onClicked: if (!page.busy) win.bridge.run("tuneFix", [row.modelData.id])
            }
        }
    }

    // --- sağ: DNS ve hız testi ------------------------------------------------------
    Column {
        x: 860; y: 92; width: 360; spacing: 0
        Item {
            width: 360; height: 38
            Section { title: page.tr["tune.dnsbox"]; icon: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" }
            Pill {
                anchors.right: parent.right; anchors.top: parent.top
                height: 30; implicitWidth: 110
                label: page.busy === "dns" ? page.tr["tune.dnstesting"] : page.tr["tune.dnstest"]
                accent: Theme.cyan
                checked: page.busy === "dns"
                onClicked: if (!page.busy) win.bridge.run("dnsTest", [])
            }
        }
        Text {
            topPadding: 8; bottomPadding: 6; width: 360; wrapMode: Text.WordWrap
            text: page.tr["tune.dns.hint"]; font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
        }
        Repeater {
            model: page.providers
            Item {
                id: prov
                required property var modelData
                readonly property string pid: modelData[0]
                readonly property var res: page.dns && page.dns[pid] ? page.dns[pid] : null
                readonly property bool current: (page.tn.dnsCurrent || "auto") === pid
                readonly property bool best: {
                    if (!page.dns || !res) return false
                    for (const k in page.dns) if (page.dns[k].score < res.score) return false
                    return true
                }
                width: 360; height: 34
                RadioOption {
                    x: -8; y: 2
                    label: prov.modelData[1]; accent: Theme.purple; dot: 14; fontSize: 14
                    checked: prov.current
                    onClicked: if (!page.busy && !prov.current) win.bridge.run("dnsSet", [prov.pid])
                }
                Rectangle {
                    x: 170; y: 15; height: 4; radius: 2; color: Theme.track; width: 120
                    visible: prov.res !== null
                    Rectangle {
                        height: parent.height; radius: 2
                        width: prov.res ? Math.max(4, parent.width * prov.res.uncached / page.dnsMax) : 0
                        color: prov.best ? Theme.cyan : Theme.faint
                    }
                }
                Text {
                    anchors.right: parent.right; y: 6
                    text: prov.res ? (prov.res.fails > 0 ? "!" : "") + Math.round(prov.res.uncached) + " ms" : ""
                    font.family: Theme.digits; font.pixelSize: 15; font.weight: Font.DemiBold
                    color: prov.best ? Theme.cyan : Theme.muted
                }
            }
        }

        Item { width: 1; height: 30 }
        Item {
            width: 360; height: 38
            Section { title: page.tr["tune.speed"]; icon: "M4 17a8 8 0 1 1 16 0M12 17l4-6" }
            Pill {
                anchors.right: parent.right; anchors.top: parent.top
                height: 30; implicitWidth: 110
                label: page.busy === "speed" ? page.tr["tune.dnstesting"] : page.tr["tune.speedtest"]
                accent: Theme.cyan
                checked: page.busy === "speed"
                onClicked: if (!page.busy) win.bridge.run("speedTest", [])
            }
        }
        Item { width: 1; height: 18 }
        Row {
            spacing: 34
            Repeater {
                model: [["down", "Mbit/s"], ["up", "Mbit/s"], ["ping", "ms"]]
                Column {
                    required property var modelData
                    readonly property var v: page.speed ? page.speed[modelData[0]] : null
                    Readout {
                        value: v === null || v === undefined ? "–" : Math.round(v)
                        unit: modelData[1]; size: 36; unitSize: 13
                    }
                    Text {
                        text: page.tr["tune." + modelData[0]]
                        font.family: Theme.font; font.pixelSize: 12; color: Theme.dim
                    }
                }
            }
        }
    }

    Component.onCompleted: if (!page.checks.length && !page.busy) win.bridge.run("tuneAnalyze", [])
}
