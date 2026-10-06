import QtQuick

// Yuvarlatılmış seçim düğmesi (şarj sınırı vb.).
Rectangle {
    id: pill
    property string label
    property bool checked: false
    property color accent: Theme.purple
    signal clicked()

    implicitWidth: txt.implicitWidth + 28
    implicitHeight: 40
    radius: height / 2
    color: checked ? Qt.rgba(accent.r, accent.g, accent.b, 0.18) : "transparent"
    border.width: 1.5
    border.color: checked ? accent : Theme.line

    Text {
        id: txt
        anchors.centerIn: parent
        text: pill.label
        font.family: Theme.font
        font.pixelSize: 13
        color: pill.checked ? "white" : Theme.muted
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: pill.clicked()
    }
}
