import QtQuick

Item {
    id: b
    property string path
    property string label
    signal clicked()
    width: 36; height: 32
    Accessible.role: Accessible.Button
    Accessible.name: label
    Rectangle { anchors.fill: parent; radius: 4; color: "white"; opacity: area.containsMouse ? 0.08 : 0 }
    Icon {
        anchors.centerIn: parent
        width: 16; height: 16; viewBox: 16; stroke: 1.5
        path: b.path; color: Theme.soft
    }
    MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; onClicked: b.clicked() }
}
