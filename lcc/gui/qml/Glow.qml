import QtQuick
import QtQuick.Effects

// İçindeki öğenin bulanık bir kopyasını arkasına koyarak neon parlaması verir.
Item {
    id: glow
    default property alias content: holder.data
    property real blur: 0.7
    property real strength: 0.6
    property bool sharp: true      // false: yalnızca bulanık hale çizilir
    anchors.fill: parent

    Item {
        id: holder
        anchors.fill: parent
        visible: false
        layer.enabled: true
    }
    MultiEffect {
        anchors.fill: holder
        source: holder
        blurEnabled: true
        blur: glow.blur
        blurMax: 32
        opacity: glow.strength
    }
    ShaderEffectSource {
        visible: glow.sharp
        anchors.fill: holder
        sourceItem: holder
    }
}
