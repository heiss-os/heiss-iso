// The welcome window: the key bindings of the active Hyprland configuration, drawn from the `welcome` object.
// Colours are the Heiss tokens (sand accent); the theme follows the desktop (dark or light).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    visible: true
    width: 760
    height: 640
    minimumWidth: 480
    minimumHeight: 420
    title: "Heiss"
    color: pal.window

    readonly property var s: welcome.screen
    readonly property bool dark: Qt.styleHints.colorScheme !== Qt.Light
    QtObject {
        id: pal
        readonly property color window: win.dark ? "#26282B" : "#F5F3EF"
        readonly property color panel: win.dark ? "#1E1F21" : "#ECE9E3"
        readonly property color button: win.dark ? "#34373B" : "#DEDAD2"
        readonly property color text: win.dark ? "#ECEAE5" : "#26282B"
        readonly property color dim: win.dark ? "#A9A7A1" : "#6B6963"
        readonly property color accent: win.dark ? "#C9B28A" : "#8C7448"
        readonly property color textOnAccent: win.dark ? "#26282B" : "#F5F3EF"
    }
    font.family: "Inter"

    Shortcut { sequence: "Escape"; onActivated: Qt.quit() }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14

        Text { textFormat: Text.PlainText; text: win.s.title; color: pal.text; font.pixelSize: 30; font.bold: true
               wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.Heading }
        Text { textFormat: Text.PlainText; text: win.s.intro; color: pal.dim; font.pixelSize: 15; wrapMode: Text.WordWrap
               Layout.fillWidth: true }
        Text { textFormat: Text.PlainText; text: win.s.mainKey; color: pal.accent; font.pixelSize: 17; font.bold: true
               Layout.fillWidth: true }
        Text { textFormat: Text.PlainText; text: win.s.mainKeyNote; color: pal.dim; font.pixelSize: 13; wrapMode: Text.WordWrap
               Layout.fillWidth: true }

        TextField {
            id: box
            Layout.fillWidth: true
            placeholderText: win.s.search
            Accessible.name: win.s.search
            color: pal.text
            placeholderTextColor: pal.dim
            font.pixelSize: 15
            background: Rectangle { radius: 8; color: pal.panel; border.width: box.activeFocus ? 2 : 0; border.color: pal.accent }
            onTextChanged: welcome.search(text)
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: win.s.rows
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: Rectangle {
                required property var modelData
                width: list.width - 12
                height: Math.max(40, row.implicitHeight + 16)
                radius: 8
                color: pal.panel
                RowLayout {
                    id: row
                    anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                    spacing: 16
                    Text { textFormat: Text.PlainText; text: modelData.keys; color: pal.accent; font.family: "JetBrains Mono"; font.pixelSize: 14
                           font.bold: true; wrapMode: Text.WordWrap; Layout.preferredWidth: Math.min(270, list.width * 0.42); Layout.maximumWidth: Math.min(270, list.width * 0.42) }
                    Text { textFormat: Text.PlainText; text: modelData.description; color: pal.text; font.pixelSize: 14; wrapMode: Text.WordWrap
                           Layout.fillWidth: true }
                }
            }
            Text { anchors.centerIn: parent; visible: win.s.empty !== ""; textFormat: Text.PlainText; text: win.s.empty; color: pal.dim
                   font.pixelSize: 15; wrapMode: Text.WordWrap; width: parent.width - 40; horizontalAlignment: Text.AlignHCenter }
        }

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Button {
                id: closeBtn
                text: win.s.close
                Accessible.name: text
                focusPolicy: Qt.StrongFocus
                contentItem: Text { textFormat: Text.PlainText; text: closeBtn.text; color: pal.textOnAccent; font.pixelSize: 16
                                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { implicitWidth: 120; implicitHeight: 40; radius: 8; color: pal.accent
                                        border.width: closeBtn.activeFocus ? 2 : 0; border.color: pal.text }
                onClicked: Qt.quit()
            }
        }
    }
}
