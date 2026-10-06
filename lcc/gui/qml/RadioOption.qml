import QtQuick

// Tasarımdaki yuvarlak işaretli seçenek (fan modları, anahtarlar).
Item {
    id: opt
    property string label
    property bool checked: false
    property bool bold: false
    property bool enabled: true
    property color accent: Theme.cyan
    property color ring: accent
    property color offColor: Theme.dim
    property int dot: 14
    property int fontSize: 15
    signal clicked()

    implicitWidth: row.implicitWidth + 16
    implicitHeight: 44
    opacity: enabled ? 1 : 0.4

    Row {
        id: row
        x: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 14
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: opt.dot; height: opt.dot; radius: width / 2
            color: opt.checked ? opt.accent : Theme.bg
            border.width: 2
            border.color: opt.checked ? opt.ring : (opt.ring === opt.accent ? opt.accent : "#3a404b")
            Behavior on color { ColorAnimation { duration: 150 } }
            Rectangle {
                anchors.centerIn: parent
                width: parent.width + 10; height: width; radius: width / 2
                color: "transparent"
                border.width: 4
                border.color: opt.accent
                opacity: opt.checked ? 0.25 : 0
                Behavior on opacity { NumberAnimation { duration: 150 } }
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: opt.label
            font.family: Theme.font
            font.pixelSize: opt.fontSize
            font.weight: opt.bold ? Font.DemiBold : Font.Normal
            color: opt.checked ? "white" : opt.offColor
        }
    }
    MouseArea {
        anchors.fill: parent
        enabled: opt.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: opt.clicked()
    }
}
