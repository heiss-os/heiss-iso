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
        readonly property color textOnAccent: win.dark ? "#26282B" : "#F5F3EF"
    }
    font.family: "Inter"

    // Heiss-styled progress bar (the stock one is blue on white): sand fill on a button-coloured track
    component Bar: ProgressBar {
        id: pb
        implicitHeight: 8
        background: Rectangle { radius: 4; color: pal.button }
        contentItem: Item {
            id: track
            Rectangle { visible: !pb.indeterminate; width: pb.visualPosition * track.width; height: track.height; radius: 4; color: pal.accent }
            Rectangle {
                id: block
                visible: pb.indeterminate; width: track.width * 0.3; height: track.height; radius: 4; color: pal.accent
                SequentialAnimation on x {
                    running: pb.indeterminate && pb.visible; loops: Animation.Infinite
                    NumberAnimation { from: 0; to: track.width * 0.7; duration: 900; easing.type: Easing.InOutQuad }
                    NumberAnimation { from: track.width * 0.7; to: 0; duration: 900; easing.type: Easing.InOutQuad }
                }
            }
        }
    }
    // closing mid-apply would orphan the command that is changing the system
    onClosing: function(close) { close.accepted = !s.isRunning }

    Shortcut { sequence: "Alt+Left"; enabled: s.canBack; onActivated: wizard.back() }

    component Btn: Button {
        id: b
        property bool primary: false
        Accessible.name: text
        focusPolicy: Qt.StrongFocus
        contentItem: Text { textFormat: Text.PlainText; text: b.text; color: b.primary ? pal.textOnAccent : pal.text; horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter; font.pixelSize: 16 }
        background: Rectangle { radius: 8; color: b.primary ? pal.accent : pal.button
                                border.width: b.activeFocus ? 2 : 0; border.color: pal.text }
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 760)
        // never taller than the window: the list of choices below scrolls, the buttons stay on screen
        height: Math.min(implicitHeight, parent.height - 48)
        spacing: 20

        Text { textFormat: Text.PlainText; text: s.progressText; color: pal.dim; font.pixelSize: 14 }
        Bar { Layout.fillWidth: true; value: s.progress; Accessible.name: s.progressText }
        Text { textFormat: Text.PlainText; text: s.title; color: pal.text; font.pixelSize: 32; font.bold: true; wrapMode: Text.WordWrap
               Layout.fillWidth: true; Accessible.role: Accessible.Heading }
        Text { textFormat: Text.PlainText; text: s.whatLabel + ": " + s.what; color: pal.dim; font.pixelSize: 16; wrapMode: Text.WordWrap
               Layout.fillWidth: true }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6   // short info lines sit close together so more of the list below fits on a small screen
            Repeater {
                model: s.facts
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 12
                    Text { textFormat: Text.PlainText; text: parent.modelData.text; color: pal.text; font.pixelSize: 16; wrapMode: Text.WordWrap
                           Layout.fillWidth: true }
                    Text { textFormat: Text.PlainText; visible: parent.modelData.badge !== ""; text: parent.modelData.badge; color: pal.accent
                           font.pixelSize: 14; font.bold: true }
                }
            }
        }
        Repeater { model: s.lines; Text { textFormat: Text.PlainText; text: modelData; color: pal.text; font.pixelSize: 18 } }

        Item {
            id: listArea
            Layout.fillWidth: true
            Layout.preferredHeight: sv.contentHeight
            Layout.fillHeight: true
            Layout.minimumHeight: Math.min(96, sv.contentHeight)
            readonly property bool overflows: sv.contentHeight > sv.height + 1
            readonly property bool moreBelow: overflows && sv.ScrollBar.vertical.position + sv.ScrollBar.vertical.size < 0.995
        ScrollView {
            id: sv
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; right: parent.right
                      rightMargin: listArea.overflows ? 14 : 0 }
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff   // drawn below: the stock bar shows on hover only
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
                        Text { textFormat: Text.PlainText; visible: text !== ""; text: q.modelData.title; color: pal.accent; font.pixelSize: 16; font.bold: true }
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
                                onClicked: {
                                    if (q.modelData.kind !== "multi") wizard.choose(modelData.path, modelData.value)
                                    else if (modelData.path === "hardware") wizard.toggleHardware(modelData.value)
                                    else wizard.toggleAddon(modelData.value)
                                }
                                contentItem: ColumnLayout {
                                    RowLayout {
                                        spacing: 10
                                        // a square box with a tick for "several can be ticked", a round dot for "choose one"
                                        Rectangle {
                                            readonly property bool multi: q.modelData.kind === "multi"
                                            implicitWidth: 20; implicitHeight: 20
                                            radius: multi ? 4 : 10
                                            color: multi && opt.modelData.selected ? pal.accent : "transparent"
                                            border.width: 2; border.color: opt.modelData.selected ? pal.accent : pal.dim
                                            Rectangle {   // round: the inner dot
                                                visible: !parent.multi && opt.modelData.selected
                                                anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: pal.accent
                                            }
                                            Item {   // square: the tick, two bars
                                                visible: parent.multi && opt.modelData.selected
                                                anchors.fill: parent
                                                Rectangle { x: 3; y: 9; width: 7; height: 2.5; radius: 1; rotation: 45; color: pal.textOnAccent }
                                                Rectangle { x: 6; y: 8; width: 11; height: 2.5; radius: 1; rotation: -50; color: pal.textOnAccent }
                                            }
                                        }
                                        Text { textFormat: Text.PlainText; text: opt.modelData.label; color: pal.text; font.pixelSize: 18
                                               Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                    }
                                    Text { textFormat: Text.PlainText; visible: opt.modelData.hint !== ""; text: opt.modelData.hint; color: pal.dim
                                           font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.leftMargin: 30 }
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
            // scroll bar: only when the list is longer than the window
            Rectangle {
                id: track
                visible: listArea.overflows
                anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                width: 6; radius: 3; color: pal.button
                Rectangle {
                    width: parent.width; radius: 3; color: pal.accent
                    y: sv.ScrollBar.vertical.position * track.height
                    height: Math.max(24, sv.ScrollBar.vertical.size * track.height)
                }
            }
            // fade at the bottom edge while more of the list is hidden below
            Rectangle {
                anchors { left: parent.left; right: track.left; bottom: parent.bottom }
                height: 36
                visible: listArea.moreBelow
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 1.0; color: pal.window }
                }
            }
        }

        Text { textFormat: Text.PlainText; visible: s.isApplying; text: s.job.step; color: pal.accent; font.pixelSize: 16; font.bold: true
               wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Bar { visible: s.isRunning; indeterminate: true; Layout.fillWidth: true; Accessible.name: s.job.step }
        Text { textFormat: Text.PlainText; visible: s.isApplying; text: s.job.log.join("\n"); color: pal.dim; font.family: "JetBrains Mono"
               font.pixelSize: 12; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; elide: Text.ElideNone }

        Text { textFormat: Text.PlainText; visible: s.note !== ""; text: s.note; color: pal.dim; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Text { textFormat: Text.PlainText; visible: s.error !== ""; text: s.error; color: "#E06C64"; wrapMode: Text.WordWrap; Layout.fillWidth: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Btn { text: s.labels.back; visible: s.canBack; onClicked: wizard.back() }
            Btn { text: s.labels.skip_all; visible: s.isFirst; onClicked: wizard.skipAll() }
            Item { Layout.fillWidth: true }
            Btn { text: s.labels.skip; visible: s.canSkip; onClicked: wizard.skip() }
            Btn { text: s.labels.save_later; visible: s.canSaveLater; primary: !s.canApply; onClicked: wizard.saveLater() }
            Btn { text: s.labels.retry; visible: s.canRetry; primary: true; onClicked: wizard.retry() }
            Btn { text: s.labels.apply; visible: s.canApply; primary: true; onClicked: wizard.apply() }
            Btn { text: s.isFirst ? s.labels.start : s.labels.next; visible: !s.isSummary && !s.isDone && !s.isApplying; primary: true
                  onClicked: wizard.next() }
            Btn { text: s.labels.close; visible: s.isDone; primary: true; onClicked: Qt.quit() }
        }
    }
}
