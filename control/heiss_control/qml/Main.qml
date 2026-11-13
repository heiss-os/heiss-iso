// Plain QtQuick.Controls window, colours from the Heiss tokens (sand accent), driven by the `control` object.
// Layout: sidebar with search on the left, page on the right. Read-only in this version.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    visible: true
    width: 1000
    height: 680
    minimumWidth: 640
    minimumHeight: 420
    title: s.appTitle
    color: pal.window

    readonly property var s: control.screen
    readonly property bool dark: Qt.styleHints.colorScheme !== Qt.Light
    QtObject {
        id: pal
        readonly property color window: win.dark ? "#26282B" : "#F5F3EF"
        readonly property color panel: win.dark ? "#1E1F21" : "#ECE9E3"
        readonly property color button: win.dark ? "#34373B" : "#DEDAD2"
        readonly property color text: win.dark ? "#ECEAE5" : "#26282B"
        readonly property color dim: win.dark ? "#A9A7A1" : "#6B6963"
        readonly property color accent: win.dark ? "#C9B28A" : "#8C7448"
        readonly property color error: win.dark ? "#E06C64" : "#B3382F"
    }
    font.family: "Inter"

    property bool searching: searchField.text.length > 0

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 260
            color: pal.panel

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                TextField {
                    id: searchField
                    Layout.fillWidth: true
                    placeholderText: s.searchLabel
                    color: pal.text
                    Accessible.name: s.searchLabel
                    onTextChanged: control.search(text)
                    Keys.onEscapePressed: text = ""
                    background: Rectangle { radius: 8; color: pal.button
                                            border.width: searchField.activeFocus ? 2 : 0; border.color: pal.accent }
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 2
                    model: win.searching ? control.results : s.sidebar
                    delegate: ItemDelegate {
                        id: row
                        required property var modelData
                        width: ListView.view.width
                        focusPolicy: Qt.StrongFocus
                        Accessible.name: modelData.title + (modelData.built ? "" : ", " + s.soonTitle)
                        onClicked: { control.open(modelData.id); searchField.text = "" }
                        contentItem: Text { text: row.modelData.title; font.pixelSize: 16; elide: Text.ElideRight
                                            color: row.modelData.built ? pal.text : pal.dim
                                            font.bold: !win.searching && row.modelData.current }
                        background: Rectangle { radius: 8
                            color: (!win.searching && row.modelData.current) ? pal.button : "transparent"
                            border.width: row.activeFocus ? 2 : 0; border.color: pal.accent }
                    }
                    footer: Text { visible: win.searching && control.results.length === 0; text: s.noResults
                                   color: pal.dim; wrapMode: Text.WordWrap; width: parent.width; padding: 8 }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Repeater {
                        model: ["en", "ru"]
                        delegate: Button {
                            id: lb
                            required property string modelData
                            flat: true
                            text: modelData.toUpperCase()
                            Accessible.name: text
                            checkable: true
                            checked: s.language === modelData
                            onClicked: control.setLanguage(modelData)
                            contentItem: Text { text: lb.text; color: lb.checked ? pal.accent : pal.dim
                                                font.bold: lb.checked; horizontalAlignment: Text.AlignHCenter }
                        }
                    }
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: Math.min(parent.width - 64, 820)
                x: 32
                y: 32
                spacing: 16

                Text { text: s.title; color: pal.text; font.pixelSize: 32; font.bold: true
                       Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.Heading }

                // pages that are not built yet
                Text { visible: !s.built; text: s.soonTitle; color: pal.accent; font.pixelSize: 18; font.bold: true }
                Text { visible: !s.built; text: s.soonWhat; color: pal.dim; font.pixelSize: 16
                       wrapMode: Text.WordWrap; Layout.fillWidth: true }

                // overview
                Text { visible: s.page === "overview"; text: s.overview ? s.overview.what : ""; color: pal.dim
                       font.pixelSize: 16; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Repeater {
                    model: s.page === "overview" ? s.overview.cards : []
                    delegate: Rectangle {
                        id: card
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: cc.implicitHeight + 24
                        radius: 10
                        color: pal.panel
                        Accessible.role: Accessible.StaticText
                        Accessible.name: modelData.title + ": " + modelData.value + (modelData.detail ? ", " + modelData.detail : "")
                        ColumnLayout {
                            id: cc
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 2
                            Text { text: card.modelData.title; color: pal.dim; font.pixelSize: 14 }
                            Text { text: card.modelData.value; color: pal.text; font.pixelSize: 22; font.bold: true }
                            Text { visible: card.modelData.detail !== ""; text: card.modelData.detail; color: pal.dim; font.pixelSize: 14 }
                            Text { visible: card.modelData.error !== ""; text: card.modelData.error; color: pal.error
                                   font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                }

                // about
                Text { visible: s.page === "about"; text: s.about ? s.about.what : ""; color: pal.dim; font.pixelSize: 16 }
                Repeater {
                    model: s.page === "about" ? s.about.rows : []
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Text { text: parent.modelData.label; color: pal.dim; font.pixelSize: 16; Layout.preferredWidth: 160 }
                        Text { text: parent.modelData.value; color: pal.text; font.pixelSize: 16; Layout.fillWidth: true
                               wrapMode: Text.WrapAnywhere }
                    }
                }
                Repeater {
                    model: s.page === "about" ? s.about.links : []
                    delegate: ItemDelegate {
                        id: lk
                        required property var modelData
                        Layout.fillWidth: true
                        focusPolicy: Qt.StrongFocus
                        Accessible.name: modelData.label + ": " + modelData.url
                        onClicked: control.openUrl(modelData.url)
                        contentItem: RowLayout {
                            Text { text: lk.modelData.label; color: pal.dim; font.pixelSize: 16; Layout.preferredWidth: 160 }
                            Text { text: lk.modelData.url; color: pal.accent; font.pixelSize: 16; Layout.fillWidth: true
                                   elide: Text.ElideMiddle }
                        }
                        background: Rectangle { radius: 8; color: "transparent"
                                                border.width: lk.activeFocus ? 2 : 0; border.color: pal.accent }
                    }
                }
                Repeater {
                    model: s.page === "about" ? s.about.notes : []
                    delegate: Text { required property string modelData; text: modelData; color: pal.dim; font.pixelSize: 14
                                     wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }
        }
    }
}
