// One row of every choice list in the wizard (language, appearance, profile, level, add-ons, hardware proposals,
// privacy level, software). A selected or ticked row looks like any other row: only the marker changes, a round
// marker for "choose one" and a square box with a tick for "several can be ticked". Keyboard focus draws a thin
// outline, hover is a faint tint. Colours come from the window's palette object, never literals.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ItemDelegate {
    id: row
    required property var colors           // the window palette (Main.qml `pal`)
    property string label: ""
    property string hint: ""
    property bool selected: false
    property bool multi: false             // true: square check box; false: round marker

    Layout.fillWidth: true
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.name: label + (hint ? ". " + hint : "")
    Accessible.role: multi ? Accessible.CheckBox : Accessible.RadioButton
    Accessible.checkable: true
    Accessible.checked: selected

    contentItem: ColumnLayout {
        spacing: 2
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Rectangle {
                id: marker
                implicitWidth: 20; implicitHeight: 20
                radius: row.multi ? 4 : 10
                color: row.multi && row.selected ? row.colors.accent : "transparent"
                border.width: 2
                border.color: row.selected ? row.colors.accent : row.colors.dim
                Rectangle {    // round marker: the inner dot
                    visible: !row.multi && row.selected
                    anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: row.colors.accent
                }
                Item {         // square marker: the tick, two bars
                    visible: row.multi && row.selected
                    anchors.fill: parent
                    Rectangle { x: 3; y: 9; width: 7; height: 2.5; radius: 1; rotation: 45; color: row.colors.textOnAccent }
                    Rectangle { x: 6; y: 8; width: 11; height: 2.5; radius: 1; rotation: -50; color: row.colors.textOnAccent }
                }
            }
            Text { textFormat: Text.PlainText; text: row.label; color: row.colors.text; font.pixelSize: 18
                   Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
        Text { textFormat: Text.PlainText; visible: row.hint !== ""; text: row.hint; color: row.colors.dim
               font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.leftMargin: 30 }
    }
    // the same calm background selected or not; hover only tints it slightly
    background: Rectangle {
        radius: 8
        color: row.hovered ? Qt.tint(row.colors.panel, Qt.rgba(row.colors.text.r, row.colors.text.g, row.colors.text.b, 0.07)) : row.colors.panel
        border.width: row.activeFocus ? 2 : 0
        border.color: row.colors.text
    }
}
