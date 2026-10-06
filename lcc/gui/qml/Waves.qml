import QtQuick
import QtQuick.Shapes

// Arka plandaki iç içe elips "dalga" çizgileri.
Item {
    id: waves
    property real centerX: 1180
    property real centerY: 380
    Repeater {
        model: 12
        delegate: Shape {
            required property int index
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: Qt.rgba(1, 1, 1, 0.045)
                strokeWidth: 1
                fillColor: "transparent"
                PathAngleArc {
                    centerX: waves.centerX; centerY: waves.centerY
                    radiusX: 520 + index * 25; radiusY: 470 + index * 20
                    startAngle: 0; sweepAngle: 360
                    moveToStart: true
                }
            }
        }
    }
}
