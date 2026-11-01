/* Heiss OS installation slideshow: "running light" logo animation.
 *
 * The logo is ONE stroked path. Layer 1 (base) is always visible, layer 2 (comet) is a short
 * dash that runs along the path in a loop, with a soft glow. Progress bar and log icon are
 * drawn by Calamares itself, not here.
 *
 * Switch: animated = false shows the static logo (sand path) only.
 * All animation parameters are properties below; tune them after the VM test.
 */
import QtQuick
import QtQuick.Shapes
import QtQuick.Effects

Rectangle {
    id: slideshow

    // ---- switches ----
    readonly property bool animated: true
    readonly property bool glow: true             // false = no glow layer at all
    readonly property bool glowUsesEffects: true  // false = plain wider low-opacity copy (no QtQuick.Effects)

    // ---- tunable parameters ----
    readonly property color pageColor: "#1E1F21"
    readonly property color baseColor: "#C9B28A"
    readonly property real  baseOpacity: 0.28
    readonly property color cometColor: "#F4E9D2"
    readonly property color glowColor: "#C9B28A"
    readonly property real  glowOpacity: 0.9
    readonly property real  glowRadius: 24        // blur, in pixels of the shown logo
    readonly property int   periodMs: 3600        // one loop of the comet
    readonly property real  dashFraction: 0.16    // comet length as a fraction of the path
    readonly property real  logoWidthFraction: 0.38
    readonly property real  logoMaxWidth: 150

    // ---- logo geometry (viewBox 20 6 62 96) ----
    readonly property string pathData:
        "M28 95 V32 A19 19 0 0 1 66 32 A19 19 0 0 1 47 51 H55 A19.5 19.5 0 0 1 55 90 H38"
    readonly property real strokeW: 12
    readonly property real vbX: 20
    readonly property real vbY: 6
    readonly property real vbW: 62
    readonly property real vbH: 96
    // total path length in viewBox units:
    // 63 (V) + 19*pi (half circle) + 19*pi/2 (quarter) + 8 (H) + 19.5*pi (half circle) + 17 (H)
    readonly property real pathLength: 63 + 19 * Math.PI + 19 * Math.PI / 2 + 8 + 19.5 * Math.PI + 17

    color: pageColor

    // The logo is drawn in viewBox units and scaled as a whole, so the dash pattern
    // (multiples of strokeWidth) and strokeWidth stay in viewBox space.
    readonly property real logoW: Math.min(logoMaxWidth, width * logoWidthFraction)
    readonly property real logoScale: logoW / vbW

    // Dash pattern lengths are in multiples of strokeWidth.
    readonly property real patternLen: pathLength / strokeW   // whole path, in stroke widths
    readonly property real dashLen: patternLen * dashFraction
    readonly property real gapLen: patternLen - dashLen        // gap >= rest of the path: one comet only

    Item {
        id: logo
        width: slideshow.logoW
        height: slideshow.logoW * slideshow.vbH / slideshow.vbW
        anchors.centerIn: parent

        // One drawn copy of the logo. The Shape sits inside a padded item so that an offscreen
        // layer (used for the glow blur) has room around the logo and is not clipped.
        component LogoShape: Item {
            id: copy
            property color lineColor: "#FFFFFF"
            property bool dashed: false
            property real lineWidth: slideshow.strokeW
            property real dashOffsetValue: 0
            property int cap: ShapePath.FlatCap
            readonly property real pad: 48
            x: -pad
            y: -pad
            width: logo.width + 2 * pad
            height: logo.height + 2 * pad

            Shape {
                x: copy.pad
                y: copy.pad
                width: slideshow.vbW
                height: slideshow.vbH
                // shift the viewBox origin to (0,0), then scale to the shown size
                transform: [
                    Translate { x: -slideshow.vbX; y: -slideshow.vbY },
                    Scale { xScale: slideshow.logoScale; yScale: slideshow.logoScale }
                ]
                transformOrigin: Item.TopLeft
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeColor: copy.lineColor
                    strokeWidth: copy.lineWidth
                    fillColor: "transparent"
                    capStyle: copy.cap
                    joinStyle: ShapePath.MiterJoin
                    strokeStyle: copy.dashed ? ShapePath.DashLine : ShapePath.SolidLine
                    // dash units are multiples of strokeWidth: rescale for wider copies
                    dashPattern: copy.dashed ? [slideshow.dashLen * slideshow.strokeW / copy.lineWidth,
                                                slideshow.gapLen * slideshow.strokeW / copy.lineWidth] : []
                    dashOffset: copy.dashOffsetValue * slideshow.strokeW / copy.lineWidth
                    PathSvg { path: slideshow.pathData }
                }
            }
        }

        // Layer 1: base (also the static fallback when animated is false)
        LogoShape {
            lineColor: slideshow.baseColor
            opacity: slideshow.animated ? slideshow.baseOpacity : 1.0
        }

        // Layer 2: comet (+ glow)
        Item {
            id: cometLayer
            visible: slideshow.animated
            anchors.fill: parent   // children are positioned relative to the logo box

            // Dash offset runs from 0 to patternLen: the dash travels once along the whole path.
            // Negative offset moves the dash forward along the path direction.
            property real offset: 0
            NumberAnimation on offset {
                running: slideshow.animated && slideshow.visible
                from: 0
                to: -slideshow.patternLen
                duration: slideshow.periodMs
                loops: Animation.Infinite
                easing.type: Easing.Linear
            }

            // glow, variant 1: blurred copy via QtQuick.Effects
            LogoShape {
                id: glowSource
                visible: false
                dashed: true
                lineColor: slideshow.glowColor
                dashOffsetValue: cometLayer.offset
                layer.enabled: slideshow.glow && slideshow.glowUsesEffects
            }
            MultiEffect {
                visible: slideshow.glow && slideshow.glowUsesEffects
                anchors.fill: glowSource
                source: glowSource
                blurEnabled: true
                blur: 1.0
                blurMax: 48
                blurMultiplier: slideshow.glowRadius / 24
                opacity: slideshow.glowOpacity
            }

            // glow, variant 2 (no effects module): wider, low-opacity copy
            LogoShape {
                visible: slideshow.glow && !slideshow.glowUsesEffects
                dashed: true
                lineColor: slideshow.glowColor
                lineWidth: slideshow.strokeW * 1.8
                cap: ShapePath.RoundCap
                opacity: 0.22
                dashOffsetValue: cometLayer.offset
            }

            // the comet itself
            LogoShape {
                dashed: true
                lineColor: slideshow.cometColor
                dashOffsetValue: cometLayer.offset
            }
        }
    }

    // Slideshow API 2 hooks (nothing to do: the animation runs while the page is shown).
    function onActivate() {}
    function onLeave() {}
}
