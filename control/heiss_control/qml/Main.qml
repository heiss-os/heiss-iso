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
        readonly property color onAccent: win.dark ? "#26282B" : "#F5F3EF"
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
                        contentItem: Text { textFormat: Text.PlainText; text: row.modelData.title; font.pixelSize: 16; elide: Text.ElideRight
                                            color: row.modelData.built ? pal.text : pal.dim
                                            font.bold: !win.searching && row.modelData.current }
                        background: Rectangle { radius: 8
                            color: (!win.searching && row.modelData.current) ? pal.button : "transparent"
                            border.width: row.activeFocus ? 2 : 0; border.color: pal.accent }
                    }
                    footer: Text { textFormat: Text.PlainText; visible: win.searching && control.results.length === 0; text: s.noResults
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
                            contentItem: Text { textFormat: Text.PlainText; text: lb.text; color: lb.checked ? pal.accent : pal.dim
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

                Text { textFormat: Text.PlainText; text: s.title; color: pal.text; font.pixelSize: 32; font.bold: true
                       Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.Heading }

                // pages that are not built yet
                Text { textFormat: Text.PlainText; visible: !s.built; text: s.soonTitle; color: pal.accent; font.pixelSize: 18; font.bold: true }
                Text { textFormat: Text.PlainText; visible: !s.built; text: s.soonWhat; color: pal.dim; font.pixelSize: 16
                       wrapMode: Text.WordWrap; Layout.fillWidth: true }

                // overview
                Text { textFormat: Text.PlainText; visible: s.page === "overview"; text: s.overview ? s.overview.what : ""; color: pal.dim
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
                            Text { textFormat: Text.PlainText; text: card.modelData.title; color: pal.dim; font.pixelSize: 14 }
                            Text { textFormat: Text.PlainText; text: card.modelData.value; color: pal.text; font.pixelSize: 22; font.bold: true }
                            Text { textFormat: Text.PlainText; visible: card.modelData.detail !== ""; text: card.modelData.detail; color: pal.dim; font.pixelSize: 14 }
                            Text { textFormat: Text.PlainText; visible: card.modelData.error !== ""; text: card.modelData.error; color: pal.error
                                   font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                }

                // profiles and software (read-only)
                Text { textFormat: Text.PlainText; visible: s.page === "profiles"; text: s.profiles ? s.profiles.what : ""; color: pal.dim
                       font.pixelSize: 16; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Repeater {
                    model: s.page === "profiles" ? s.profiles.rows : []
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Text { textFormat: Text.PlainText; text: parent.modelData.label; color: pal.dim; font.pixelSize: 16; Layout.preferredWidth: 200 }
                        Text { textFormat: Text.PlainText; text: parent.modelData.value; color: pal.text; font.pixelSize: 16; Layout.fillWidth: true
                               wrapMode: Text.WordWrap }
                    }
                }
                Repeater {
                    model: s.page === "profiles" ? s.profiles.errors : []
                    delegate: Text { textFormat: Text.PlainText; required property string modelData; text: modelData; color: pal.error; font.pixelSize: 14
                                     wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                Text { textFormat: Text.PlainText; visible: s.page === "profiles" && s.profiles.pending.length > 0; text: s.profiles ? s.profiles.pendingTitle : ""
                       color: pal.accent; font.pixelSize: 18; font.bold: true }
                Repeater {
                    model: s.page === "profiles" ? s.profiles.pending : []
                    delegate: Text { textFormat: Text.PlainText; required property var modelData
                                     text: modelData.text + ": " + modelData.status + (modelData.error ? " (" + modelData.error + ")" : "")
                                     color: pal.text; font.pixelSize: 16; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                Repeater {
                    model: s.page === "profiles" ? s.profiles.sections : []
                    delegate: ColumnLayout {
                        id: sec
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        Text { textFormat: Text.PlainText; text: sec.modelData.title; color: pal.accent; font.pixelSize: 18; font.bold: true
                               Accessible.role: Accessible.Heading }
                        Text { textFormat: Text.PlainText; visible: sec.modelData.items.length > 0; text: sec.modelData.items.join("\n"); color: pal.dim
                               font.family: "JetBrains Mono"; font.pixelSize: 13; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                    }
                }
                Text { textFormat: Text.PlainText; visible: s.page === "profiles"; text: s.profiles ? s.profiles.note : ""; color: pal.dim; font.pixelSize: 14
                       wrapMode: Text.WordWrap; Layout.fillWidth: true }

                // appearance
                Text { textFormat: Text.PlainText; visible: s.page === "appearance"; text: s.appearance ? s.appearance.what : ""; color: pal.dim
                       font.pixelSize: 16; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { textFormat: Text.PlainText; visible: s.page === "appearance"; color: pal.text; font.pixelSize: 16
                       text: s.appearance ? s.appearance.currentLabel + ": " + s.appearance.current : "" }
                RowLayout {
                    visible: s.page === "appearance"
                    spacing: 12
                    Repeater {
                        model: s.page === "appearance" ? s.appearance.choices : []
                        delegate: Button {
                            id: tb
                            required property var modelData
                            text: modelData.label
                            enabled: s.appearance.state !== "running"
                            checkable: true
                            checked: modelData.selected
                            focusPolicy: Qt.StrongFocus
                            Accessible.name: text
                            onClicked: control.setTheme(modelData.id)
                            contentItem: Text { textFormat: Text.PlainText; text: tb.text; color: tb.checked ? pal.onAccent : pal.text; font.pixelSize: 16
                                                horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { radius: 8; color: tb.checked ? pal.accent : pal.button
                                                    border.width: tb.activeFocus ? 2 : 0; border.color: pal.text }
                        }
                    }
                }
                ProgressBar { visible: s.page === "appearance" && s.appearance.state === "running"; indeterminate: true
                              Layout.fillWidth: true; Accessible.name: s.appearance ? s.appearance.running : "" }
                Text { textFormat: Text.PlainText; visible: s.page === "appearance" && s.appearance.state === "failed"; text: s.appearance ? s.appearance.message : ""
                       color: pal.error; font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { textFormat: Text.PlainText; visible: s.page === "appearance"; text: s.appearance ? s.appearance.note : ""; color: pal.dim; font.pixelSize: 14
                       wrapMode: Text.WordWrap; Layout.fillWidth: true }

                // about
                Text { textFormat: Text.PlainText; visible: s.page === "about"; text: s.about ? s.about.what : ""; color: pal.dim; font.pixelSize: 16 }
                Repeater {
                    model: s.page === "about" ? s.about.rows : []
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Text { textFormat: Text.PlainText; text: parent.modelData.label; color: pal.dim; font.pixelSize: 16; Layout.preferredWidth: 160 }
                        Text { textFormat: Text.PlainText; text: parent.modelData.value; color: pal.text; font.pixelSize: 16; Layout.fillWidth: true
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
                            Text { textFormat: Text.PlainText; text: lk.modelData.label; color: pal.dim; font.pixelSize: 16; Layout.preferredWidth: 160 }
                            Text { textFormat: Text.PlainText; text: lk.modelData.url; color: pal.accent; font.pixelSize: 16; Layout.fillWidth: true
                                   elide: Text.ElideMiddle }
                        }
                        background: Rectangle { radius: 8; color: "transparent"
                                                border.width: lk.activeFocus ? 2 : 0; border.color: pal.accent }
                    }
                }
                Repeater {
                    model: s.page === "about" ? s.about.notes : []
                    delegate: Text { textFormat: Text.PlainText; required property string modelData; text: modelData; color: pal.dim; font.pixelSize: 14
                                     wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }
        }
    }
}
