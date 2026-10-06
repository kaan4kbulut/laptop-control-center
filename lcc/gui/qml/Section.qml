import QtQuick

// Mor alt çizgili bölüm başlığı (simge + başlık).
Item {
    id: sec
    property string title
    property string icon
    width: row.implicitWidth; height: 38
    Row {
        id: row
        spacing: 12
        Icon { width: 28; height: 28; stroke: 1.4; color: Theme.text; path: sec.icon }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: sec.title; font.family: Theme.font; font.pixelSize: 17; color: Theme.text
        }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; color: Theme.purple }
}
