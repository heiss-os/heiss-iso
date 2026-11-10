// Plain QtQuick.Controls window, colours from the Heiss tokens (sand accent), driven by the `wizard` object.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    visible: true
    visibility: Window.FullScreen
    title: "Heiss Welcome"
    color: pal.window

    readonly property var s: wizard.screen
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
    }
    font.family: "Inter"

    Shortcut { sequence: "Alt+Left"; enabled: s.canBack; onActivated: wizard.back() }

    component Btn: Button {
        id: b
        property bool primary: false
        Accessible.name: text
        focusPolicy: Qt.StrongFocus
        contentItem: Text { text: b.text; color: b.primary ? pal.onAccent : pal.text; horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter; font.pixelSize: 16 }
        background: Rectangle { radius: 8; color: b.primary ? pal.accent : pal.button
                                border.width: b.activeFocus ? 2 : 0; border.color: pal.text }
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 760)
        spacing: 20

        Text { text: s.progressText; color: pal.dim; font.pixelSize: 14 }
        ProgressBar { Layout.fillWidth: true; value: s.progress; Accessible.name: s.progressText }
        Text { text: s.title; color: pal.text; font.pixelSize: 32; font.bold: true; wrapMode: Text.WordWrap
               Layout.fillWidth: true; Accessible.role: Accessible.Heading }
        Text { text: s.whatLabel + ": " + s.what; color: pal.dim; font.pixelSize: 16; wrapMode: Text.WordWrap
               Layout.fillWidth: true }
        Repeater { model: s.lines; Text { text: modelData; color: pal.text; font.pixelSize: 18 } }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, win.height - 380)
            clip: true
            ColumnLayout {
                width: parent.width
                spacing: 12
                Repeater {
                    model: s.questions
                    delegate: ColumnLayout {
                        id: q
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 6
                        Text { visible: text !== ""; text: q.modelData.title; color: pal.accent; font.pixelSize: 16; font.bold: true }
                        Repeater {
                            model: q.modelData.options
                            delegate: ItemDelegate {
                                id: opt
                                required property var modelData
                                Layout.fillWidth: true
                                focusPolicy: Qt.StrongFocus
                                Accessible.name: modelData.label + (modelData.hint ? ". " + modelData.hint : "")
                                Accessible.checkable: true
                                Accessible.checked: modelData.selected
                                onClicked: q.modelData.kind === "multi" ? wizard.toggleAddon(modelData.value)
                                                                        : wizard.choose(modelData.path, modelData.value)
                                contentItem: ColumnLayout {
                                    Text { text: (opt.modelData.selected ? "● " : "○ ") + opt.modelData.label
                                           color: pal.text; font.pixelSize: 18 }
                                    Text { visible: opt.modelData.hint !== ""; text: opt.modelData.hint; color: pal.dim
                                           font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }
                                background: Rectangle { radius: 8; color: opt.modelData.selected ? pal.button : pal.panel
                                                        border.width: opt.activeFocus ? 2 : (opt.modelData.selected ? 1 : 0)
                                                        border.color: opt.activeFocus ? pal.text : pal.accent }
                            }
                        }
                    }
                }
            }
        }

        Text { visible: s.error !== ""; text: s.error; color: "#E06C64"; wrapMode: Text.WordWrap; Layout.fillWidth: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Btn { text: s.labels.back; visible: s.canBack; onClicked: wizard.back() }
            Btn { text: s.labels.skip_all; visible: s.isFirst; onClicked: wizard.skipAll() }
            Item { Layout.fillWidth: true }
            Btn { text: s.labels.skip; visible: s.canSkip; onClicked: wizard.skip() }
            Btn { text: s.labels.save_later; visible: s.isSummary; primary: true; onClicked: wizard.saveLater() }
            Btn { text: s.isFirst ? s.labels.start : s.labels.next; visible: !s.isSummary && !s.isDone; primary: true
                  onClicked: wizard.next() }
            Btn { text: s.labels.close; visible: s.isDone; primary: true; onClicked: Qt.quit() }
        }
    }
}
