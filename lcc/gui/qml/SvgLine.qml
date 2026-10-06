import QtQuick
import QtQuick.Shapes

// Tasarımdaki sabit SVG çizgileri (aynı 1280×760 koordinatlarıyla).
Shape {
    id: l
    property string path
    property color color: Theme.line
    property real width_: 2
    property color fill: "transparent"
    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer
    ShapePath {
        strokeColor: l.color
        strokeWidth: l.width_
        fillColor: l.fill
        capStyle: ShapePath.FlatCap
        PathSvg { path: l.path }
    }
}
