/* Heiss OS minimal installer sidebar: thin step indicator (no text) + social links.
 *
 * Switches (set to false to turn a part off):
 */
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.3

Rectangle {
    id: sideBar

    // ---- feature switches ----
    readonly property bool showStepDots: true
    readonly property bool showSocial: true
    // Open links through the live-session helper (heiss-open-link, 127.0.0.1 only).
    // false = fall back to Qt.openUrlExternally (does not work when Calamares runs as root).
    readonly property bool useLinkHelper: true
    readonly property string helperUrl: "http://127.0.0.1:48731/open?name="
    // --------------------------

    readonly property string brandDir: "file:///usr/share/calamares/branding/heiss/"

    color: Branding.styleString(Branding.SidebarBackground)

    // name: "telegram" | "x" (the helper maps these to two fixed URLs)
    function openLink(name, fallbackUrl) {
        if (!useLinkHelper) {
            Qt.openUrlExternally(fallbackUrl)
            return
        }
        var xhr = new XMLHttpRequest()
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 0)
                Qt.openUrlExternally(fallbackUrl)   // helper not running
        }
        xhr.open("GET", helperUrl + name)
        xhr.send()
    }

    Image {
        id: glyph
        anchors.top: parent.top
        anchors.topMargin: 20
        anchors.horizontalCenter: parent.horizontalCenter
        width: 28; height: 28
        source: brandDir + "heiss-glyph.png"
        smooth: true
    }

    Column {
        id: dots
        visible: sideBar.showStepDots
        anchors.centerIn: parent
        spacing: 14
        Repeater {
            model: ViewManager
            Rectangle {
                width: 8; height: 8; radius: 4
                anchors.horizontalCenter: parent.horizontalCenter
                color: index === ViewManager.currentStepIndex
                       ? Branding.styleString(Branding.SidebarTextCurrent)
                       : Branding.styleString(Branding.SidebarText)
                opacity: index === ViewManager.currentStepIndex ? 1.0 : 0.35
            }
        }
    }

    Column {
        id: social
        visible: sideBar.showSocial
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 16

        Image {
            width: 20; height: 20
            source: brandDir + "icon-telegram.png"
            smooth: true; opacity: tg.containsMouse ? 1.0 : 0.6
            MouseArea { id: tg; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: sideBar.openLink("telegram", "https://t.me/heiss_os") }
        }
        Image {
            width: 20; height: 20
            source: brandDir + "icon-x.png"
            smooth: true; opacity: xx.containsMouse ? 1.0 : 0.6
            MouseArea { id: xx; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: sideBar.openLink("x", "https://x.com/heiss_OS") }
        }
    }
}
