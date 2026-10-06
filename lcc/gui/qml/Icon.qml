import QtQuick
import QtQuick.Shapes

// 24x24 tasarım alanında SVG yol(lar)ı olarak çizilen çizgi simgesi.
Item {
    id: icon
    property string path
    property color color: "white"
    property real stroke: 1.6
    property real viewBox: 24
    property color fill: "transparent"
    implicitWidth: 20
    implicitHeight: 20

    Shape {
        width: icon.viewBox; height: icon.viewBox
        scale: icon.width / icon.viewBox
        transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: icon.color
            strokeWidth: icon.stroke
            fillColor: icon.fill
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: icon.path }
        }
    }
}
