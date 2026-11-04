/*
 * Heiss OS login splash. Deliberately simple so it works with software rendering
 * (VirtualBox) and never blocks login: a Rectangle, one SVG Image, two animations.
 * No Shapes, no ShaderEffects, no OpenGL-only features.
 * Plasma sets `stage` (1..6) while the session starts; it is not needed for the look.
 * Switch: set `animated` to false for a static logo.
 */
import QtQuick

Rectangle {
    id: root
    color: "#1E1F21"

    property int stage
    readonly property bool animated: true

    Image {
        id: logo
        anchors.centerIn: parent
        // the SVG is rasterized at this size (a square, 25% of the shorter screen side)
        readonly property real side: Math.round(Math.min(root.width, root.height) * 0.25)
        width: side
        height: side
        sourceSize: Qt.size(side * 2, side * 2)   // 2x for crisp edges on HiDPI
        source: "images/heiss-glyph.svg"
        fillMode: Image.PreserveAspectFit
        smooth: true
        opacity: 0.72
        scale: 1.0

        // Breathing: 4.6 s per full cycle, scale 1.0 -> 1.035, opacity 0.72 -> 1.0
        ParallelAnimation {
            running: root.animated && logo.status === Image.Ready
            loops: Animation.Infinite
            SequentialAnimation {
                NumberAnimation { target: logo; property: "scale"; from: 1.0; to: 1.035; duration: 2300; easing.type: Easing.InOutSine }
                NumberAnimation { target: logo; property: "scale"; from: 1.035; to: 1.0; duration: 2300; easing.type: Easing.InOutSine }
            }
            SequentialAnimation {
                NumberAnimation { target: logo; property: "opacity"; from: 0.72; to: 1.0; duration: 2300; easing.type: Easing.InOutSine }
                NumberAnimation { target: logo; property: "opacity"; from: 1.0; to: 0.72; duration: 2300; easing.type: Easing.InOutSine }
            }
        }
    }
}
