import QtQuick
import QtQuick.Shapes

// Merkezi (cx, cy) olan, kalınlığı `thickness` olan bir yay. Açılar Qt'deki gibi
// derece cinsinden, 3 yönünden saat yönünde. Halka dolgu olarak çizilir; böylece
// renk geçişi (fillGradient) kenar boyunca da uygulanabilir.
Shape {
    id: ring
    property real cx
    property real cy
    property real radius
    property real thickness: 2
    property real startAngle: 0
    property real sweep: 90
    property color color: "white"
    property alias gradient: path.fillGradient

    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer
    visible: Math.abs(sweep) > 0.05

    ShapePath {
        id: path
        strokeWidth: -1
        strokeColor: "transparent"
        fillColor: ring.color
        PathAngleArc {
            centerX: ring.cx; centerY: ring.cy
            radiusX: ring.radius + ring.thickness / 2; radiusY: radiusX
            startAngle: ring.startAngle; sweepAngle: ring.sweep
            moveToStart: true
        }
        PathAngleArc {
            centerX: ring.cx; centerY: ring.cy
            radiusX: ring.radius - ring.thickness / 2; radiusY: radiusX
            startAngle: ring.startAngle + ring.sweep; sweepAngle: -ring.sweep
            moveToStart: false
        }
    }
}
