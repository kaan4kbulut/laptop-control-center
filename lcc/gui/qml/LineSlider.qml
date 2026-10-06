import QtQuick

// İnce çizgi + dikey tutamaçlı kaydırıcı (0–100). Sürüklerken `moved`, bırakınca
// `committed` yayınlanır; sistem değeri her sürükleme adımında değiştirilmez.
Item {
    id: s
    property real value: 0
    property bool enabled: true
    property color accent: Theme.purple
    property string leftLabel: "0"
    property string rightLabel: "100"
    property real live: drag.pressed ? drag.dragValue : value
    signal moved(real v)
    signal committed(real v)

    implicitHeight: 52
    opacity: enabled ? 1 : 0.35

    Rectangle {
        id: track
        y: 10; width: parent.width; height: 4
        color: Theme.line
        Rectangle {
            height: parent.height
            width: parent.width * s.live / 100
            color: s.accent
        }
        Rectangle {
            x: parent.width * s.live / 100 - 3
            y: -9; width: 6; height: 22; radius: 2
            color: "white"
        }
    }
    Row {
        y: 30; width: parent.width
        Text { text: s.leftLabel; font.family: Theme.digits; font.pixelSize: 14; color: Theme.soft; width: parent.width / 2 }
        Text { text: s.rightLabel; font.family: Theme.digits; font.pixelSize: 14; color: Theme.soft; width: parent.width / 2; horizontalAlignment: Text.AlignRight }
    }
    MouseArea {
        id: drag
        property real dragValue: 0
        x: -10; y: -6; width: parent.width + 20; height: 34
        enabled: s.enabled
        cursorShape: Qt.PointingHandCursor
        function at(mx) { return Math.max(0, Math.min(100, Math.round((mx - 10) / track.width * 100))) }
        onPressed: (m) => { dragValue = at(m.x); s.moved(dragValue) }
        onPositionChanged: (m) => { if (pressed) { dragValue = at(m.x); s.moved(dragValue) } }
        onReleased: s.committed(dragValue)
    }
    WheelHandler {
        enabled: s.enabled
        onWheel: (e) => { s.committed(Math.max(0, Math.min(100, s.value + (e.angleDelta.y > 0 ? 5 : -5)))) }
    }
}
