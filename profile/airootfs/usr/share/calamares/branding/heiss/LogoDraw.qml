/* Heiss logo "line drawing" animation, shared component.
 *
 * Draws the logo path (viewBox 20 6 62 96, stroke 12, butt caps) from nothing, holds, fades out,
 * then repeats. Same path data and dash technique as show.qml (dash length = drawn part of the
 * path, gap = more than the whole path). Used by usersq.qml.
 *
 * The item is `boxW` x `boxH` big (default: the viewBox); put it inside a scaled/centered parent
 * or set `logoScale`. restart() starts a new cycle from nothing.
 */
import QtQuick
import QtQuick.Shapes

Item {
    id: root

    // ---- tunable parameters ----
    property color lineColor: "#C9B28A"
    property real  peakOpacity: 0.11     // low contrast: 0.08 .. 0.14
    property int   drawMs: 2400
    property int   holdMs: 1200
    property int   fadeMs: 800
    property real  logoScale: 4.2        // viewBox units -> pixels
    property bool  running: true

    // ---- logo geometry ----
    readonly property string pathData:
        "M28 95 V32 A19 19 0 0 1 66 32 A19 19 0 0 1 47 51 H55 A19.5 19.5 0 0 1 55 90 H38"
    readonly property real strokeW: 12
    readonly property real vbX: 20
    readonly property real vbY: 6
    readonly property real vbW: 62
    readonly property real vbH: 96
    readonly property real pathLength: 63 + 19 * Math.PI + 19 * Math.PI / 2 + 8 + 19.5 * Math.PI + 17

    // 0..1 share of the path that is drawn
    property real progress: 0

    width: vbW * logoScale
    height: vbH * logoScale
    opacity: peakOpacity

    function restart() {
        cycle.stop()
        progress = 0
        opacity = peakOpacity
        if (running) cycle.start()
    }
    onRunningChanged: restart()
    Component.onCompleted: restart()

    Shape {
        width: root.vbW
        height: root.vbH
        transform: [
            Translate { x: -root.vbX; y: -root.vbY },
            Scale { xScale: root.logoScale; yScale: root.logoScale }
        ]
        transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: root.lineColor
            strokeWidth: root.strokeW
            fillColor: "transparent"
            capStyle: ShapePath.FlatCap
            joinStyle: ShapePath.MiterJoin
            strokeStyle: ShapePath.DashLine
            // dash units are multiples of strokeWidth
            dashPattern: [Math.max(root.progress, 0.0005) * root.pathLength / root.strokeW,
                          (root.pathLength + 10) / root.strokeW]
            PathSvg { path: root.pathData }
        }
    }

    SequentialAnimation {
        id: cycle
        loops: Animation.Infinite
        NumberAnimation { target: root; property: "progress"; from: 0; to: 1
                          duration: root.drawMs; easing.type: Easing.InOutQuad }
        PauseAnimation { duration: root.holdMs }
        NumberAnimation { target: root; property: "opacity"; from: root.peakOpacity; to: 0
                          duration: root.fadeMs; easing.type: Easing.InOutQuad }
        ScriptAction { script: { root.progress = 0; root.opacity = root.peakOpacity } }
    }
}
