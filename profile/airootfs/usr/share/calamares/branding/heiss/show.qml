/* Heiss OS installation slideshow: dark page with the centered Heiss logo (static for now,
 * animation comes later). Progress bar and log icon are drawn by Calamares itself.
 *
 * Switch: showLogo = false leaves only the dark background.
 */
import QtQuick 2.0

Rectangle {
    id: slideshow

    readonly property bool showLogo: true

    color: "#1E1F21"

    Image {
        visible: slideshow.showLogo
        anchors.centerIn: parent
        width: Math.min(220, parent.width * 0.5)
        height: width
        source: "heiss-logo.png"
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    // Slideshow API 2 hooks (nothing to do for a static page).
    function onActivate() {}
    function onLeave() {}
}
