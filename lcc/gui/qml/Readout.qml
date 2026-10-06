import QtQuick

// Büyük Rajdhani sayı + küçük birim, taban çizgisinde hizalı.
Row {
    id: r
    property string value: "–"
    property string unit
    property int size: 26
    property int unitSize: 13
    spacing: 4
    Text {
        id: num
        text: r.value
        font.family: Theme.digits; font.pixelSize: r.size; font.weight: Font.DemiBold
        color: Theme.text
    }
    Text {
        anchors.baseline: num.baseline
        visible: r.unit !== ""
        text: r.unit
        font.family: Theme.digits; font.pixelSize: r.unitSize
        color: Theme.muted
    }
}
