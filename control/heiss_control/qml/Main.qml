// The Heiss settings window: sidebar of pages on the left, the page on the right, drawn from the `control` object.
// A page is a list of blocks (text, rows, choice, field, action, items, report, links, message); colours are the Heiss tokens.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    visible: true
    width: 920
    height: 640
    minimumWidth: 600
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
        readonly property color textOnAccent: win.dark ? "#26282B" : "#F5F3EF"
        readonly property color error: win.dark ? "#E06C64" : "#B3382F"
        readonly property color caution: win.dark ? "#E2B050" : "#7D5924"
        readonly property color ok: win.dark ? "#8CC49A" : "#2F6B3F"
    }
    font.family: "Inter"

    component Btn: Button {
        id: b
        property bool primary: false
        Accessible.name: text
        focusPolicy: Qt.StrongFocus
        enabled: !win.s.busy
        contentItem: Text { textFormat: Text.PlainText; text: b.text; color: b.primary ? pal.textOnAccent : pal.text; horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter; font.pixelSize: 15; opacity: b.enabled ? 1 : 0.5 }
        background: Rectangle { implicitHeight: 38; implicitWidth: 100; radius: 8; color: b.primary ? pal.accent : pal.button
                                border.width: b.activeFocus ? 2 : 0; border.color: pal.text }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 230
            color: pal.panel
            ColumnLayout {
                anchors { fill: parent; margins: 12 }
                spacing: 4
                Text { textFormat: Text.PlainText; text: win.s.appTitle; color: pal.text; font.pixelSize: 18; font.bold: true
                       Layout.fillWidth: true; Layout.bottomMargin: 10; wrapMode: Text.WordWrap }
                Repeater {
                    model: win.s.sidebar
                    delegate: Button {
                        id: nav
                        required property var modelData
                        Layout.fillWidth: true
                        Accessible.name: modelData.title
                        focusPolicy: Qt.StrongFocus
                        contentItem: Text { textFormat: Text.PlainText; text: nav.modelData.title; color: nav.modelData.current ? pal.textOnAccent : pal.text
                                            font.pixelSize: 15; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                        background: Rectangle { implicitHeight: 38; radius: 8; color: nav.modelData.current ? pal.accent : (nav.hovered ? pal.button : "transparent")
                                                border.width: nav.activeFocus ? 2 : 0; border.color: pal.text }
                        onClicked: control.open(nav.modelData.id)
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        ScrollView {
            id: sv
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: sv.availableWidth - 48
                x: 24
                spacing: 14
                Item { Layout.preferredHeight: 10 }
                Text { textFormat: Text.PlainText; text: win.s.title; color: pal.text; font.pixelSize: 28; font.bold: true
                       Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.Heading }
                Text { textFormat: Text.PlainText; visible: win.s.busy; text: "..."; color: pal.accent; font.pixelSize: 15 }

                Repeater {
                    model: win.s.blocks
                    delegate: ColumnLayout {
                        id: blk
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 8

                        Text { visible: blk.modelData.type === "text"; textFormat: Text.PlainText; text: blk.modelData.text || ""; color: pal.dim
                               font.pixelSize: 15; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Text { visible: blk.modelData.type === "heading"; textFormat: Text.PlainText; text: blk.modelData.text || ""; color: pal.text
                               font.pixelSize: 20; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.topMargin: 10 }
                        Text { visible: blk.modelData.type === "message" && (blk.modelData.text || "") !== ""; textFormat: Text.PlainText; text: blk.modelData.text || ""
                               color: blk.modelData.tone === "error" ? pal.error : (blk.modelData.tone === "warn" ? pal.caution : (blk.modelData.tone === "ok" ? pal.ok : pal.dim))
                               font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }

                        // rows: label and value
                        ColumnLayout {
                            visible: blk.modelData.type === "rows"
                            Layout.fillWidth: true
                            spacing: 4
                            Text { visible: (blk.modelData.title || "") !== ""; textFormat: Text.PlainText; text: blk.modelData.title || ""; color: pal.accent
                                   font.pixelSize: 16; font.bold: true }
                            Repeater {
                                model: blk.modelData.type === "rows" ? blk.modelData.rows : []
                                delegate: Rectangle {
                                    id: rw
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: Math.max(40, rwl.implicitHeight + 14)
                                    radius: 8
                                    color: pal.panel
                                    RowLayout {
                                        id: rwl
                                        anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                                        spacing: 12
                                        Text { visible: text !== ""; textFormat: Text.PlainText; text: rw.modelData.label; color: pal.dim; font.pixelSize: 14
                                               wrapMode: Text.WordWrap; Layout.preferredWidth: 200 }
                                        Text { textFormat: Text.PlainText; text: rw.modelData.value; color: pal.text; font.pixelSize: 14; wrapMode: Text.WordWrap
                                               Layout.fillWidth: true }
                                    }
                                }
                            }
                            Text { visible: (blk.modelData.empty || "") !== ""; textFormat: Text.PlainText; text: blk.modelData.empty || ""; color: pal.dim
                                   font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }

                        // choice: one of a few values
                        ColumnLayout {
                            visible: blk.modelData.type === "choice"
                            Layout.fillWidth: true
                            spacing: 6
                            Text { textFormat: Text.PlainText; text: blk.modelData.title || ""; color: pal.accent; font.pixelSize: 16; font.bold: true }
                            Flow {
                                Layout.fillWidth: true
                                spacing: 8
                                Repeater {
                                    model: blk.modelData.type === "choice" ? blk.modelData.options : []
                                    delegate: Btn {
                                        required property var modelData
                                        text: modelData.label
                                        primary: modelData.selected
                                        enabled: !win.s.busy && blk.modelData.enabled
                                        Accessible.checkable: true
                                        Accessible.checked: modelData.selected
                                        onClicked: control.run(blk.modelData.id, modelData.value)
                                    }
                                }
                            }
                            Text { visible: (blk.modelData.note || "") !== ""; textFormat: Text.PlainText; text: blk.modelData.note || ""; color: pal.dim
                                   font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }

                        // field: a line of text with an Apply button
                        ColumnLayout {
                            visible: blk.modelData.type === "field"
                            Layout.fillWidth: true
                            spacing: 6
                            Text { textFormat: Text.PlainText; text: blk.modelData.title || ""; color: pal.accent; font.pixelSize: 16; font.bold: true }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                TextField {
                                    id: fld
                                    Layout.fillWidth: true
                                    text: blk.modelData.value || ""
                                    placeholderText: blk.modelData.hint || ""
                                    Accessible.name: blk.modelData.title || ""
                                    color: pal.text
                                    placeholderTextColor: pal.dim
                                    font.pixelSize: 15
                                    background: Rectangle { radius: 8; color: pal.panel; border.width: fld.activeFocus ? 2 : 0; border.color: pal.accent }
                                    onAccepted: control.run(blk.modelData.id, text)
                                }
                                Btn { text: blk.modelData.apply || ""; primary: true; onClicked: control.run(blk.modelData.id, fld.text) }
                            }
                            Text { visible: (blk.modelData.note || "") !== ""; textFormat: Text.PlainText; text: blk.modelData.note || ""; color: pal.dim
                                   font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }

                        // action: one button and the reason it did not work
                        ColumnLayout {
                            visible: blk.modelData.type === "action"
                            Layout.fillWidth: true
                            spacing: 4
                            Btn {
                                text: blk.modelData.label || ""
                                primary: true
                                onClicked: {
                                    var id = blk.modelData.id
                                    if (id.indexOf("launch:") === 0) control.run("launch", id.substring(7))
                                    else control.run(id, "")
                                }
                            }
                            Text { visible: (blk.modelData.message || "") !== ""; textFormat: Text.PlainText; text: blk.modelData.message || ""; color: pal.error
                                   font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }

                        // items: check results
                        ColumnLayout {
                            visible: blk.modelData.type === "items"
                            Layout.fillWidth: true
                            spacing: 4
                            Repeater {
                                model: blk.modelData.type === "items" ? blk.modelData.items : []
                                delegate: RowLayout {
                                    id: it
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: 10
                                    Text { textFormat: Text.PlainText; text: it.modelData.status; font.pixelSize: 13; font.bold: true; Layout.preferredWidth: 48
                                           color: it.modelData.status === "FAIL" ? pal.error : (it.modelData.status === "WARN" ? pal.caution : pal.ok) }
                                    Text { textFormat: Text.PlainText; text: it.modelData.name + (it.modelData.detail !== "" ? ": " + it.modelData.detail : ""); color: pal.text
                                           font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }
                            }
                        }

                        // report: text to copy
                        ColumnLayout {
                            visible: blk.modelData.type === "report"
                            Layout.fillWidth: true
                            spacing: 6
                            Text { textFormat: Text.PlainText; text: blk.modelData.title || ""; color: pal.accent; font.pixelSize: 16; font.bold: true }
                            Text { textFormat: Text.PlainText; text: blk.modelData.text || ""; color: pal.dim; font.family: "JetBrains Mono"; font.pixelSize: 12
                                   wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                            RowLayout {
                                spacing: 10
                                Btn { text: blk.modelData.copy || ""; onClicked: control.copyReport() }
                                Text { visible: (blk.modelData.copied || "") !== ""; textFormat: Text.PlainText; text: blk.modelData.copied || ""; color: pal.ok; font.pixelSize: 14 }
                            }
                        }

                        // links
                        Flow {
                            visible: blk.modelData.type === "links"
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: blk.modelData.type === "links" ? blk.modelData.links : []
                                delegate: Btn { required property var modelData; text: modelData.label; onClicked: control.openUrl(modelData.url) }
                            }
                        }
                    }
                }
                Item { Layout.preferredHeight: 24 }
            }
        }
    }
}
