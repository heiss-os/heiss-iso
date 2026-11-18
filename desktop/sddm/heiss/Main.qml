// Heiss OS login screen for SDDM. Plain QtQuick (Qt6), no Plasma or KDE import.
// Colors and fonts come from theme.conf (generated from the design tokens); SDDM exposes them as `config`.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1280
    height: 800
    color: config.window
    focus: true

    property int sessionIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0

    Image {
        anchors.fill: parent
        source: config.background
        fillMode: Image.PreserveAspectCrop
        visible: status === Image.Ready
    }
    Rectangle { anchors.fill: parent; color: config.view; opacity: 0.55 }

    Connections {
        target: sddm
        function onLoginFailed() {
            message.text = qsTr("Wrong user name or password")
            password.text = ""
            password.forceActiveFocus()
        }
        function onLoginSucceeded() { message.text = "" }
    }

    Rectangle {
        id: card
        width: 380
        height: column.implicitHeight + 64
        anchors.centerIn: parent
        radius: 12
        color: config.panel
        border.color: config.border
        border.width: 1

        ColumnLayout {
            id: column
            anchors.fill: parent
            anchors.margins: 32
            spacing: 14

            Image {
                Layout.alignment: Qt.AlignHCenter
                source: config.logo
                sourceSize.height: 72
                fillMode: Image.PreserveAspectFit
                visible: status === Image.Ready
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Heiß OS"
                color: config.accent
                font.family: config.font
                font.pixelSize: 26
                font.weight: Font.ExtraBold
                font.italic: true
            }
            Text {
                id: clock
                Layout.alignment: Qt.AlignHCenter
                color: config.text_secondary
                font.family: config.font
                font.pixelSize: 14
                text: Qt.formatDateTime(new Date(), "dddd, d MMMM  HH:mm")
                Timer { interval: 30000; running: true; repeat: true; onTriggered: clock.text = Qt.formatDateTime(new Date(), "dddd, d MMMM  HH:mm") }
            }

            TextField {
                id: user
                Layout.fillWidth: true
                text: userModel.lastUser
                placeholderText: qsTr("User name")
                color: config.text
                placeholderTextColor: config.text_secondary
                font.family: config.font
                font.pixelSize: 15
                background: Rectangle { radius: 8; color: config.button; border.width: user.activeFocus ? 2 : 0; border.color: config.accent }
                onAccepted: password.forceActiveFocus()
            }
            TextField {
                id: password
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: qsTr("Password")
                color: config.text
                placeholderTextColor: config.text_secondary
                font.family: config.font
                font.pixelSize: 15
                focus: true
                background: Rectangle { radius: 8; color: config.button; border.width: password.activeFocus ? 2 : 0; border.color: config.accent }
                onAccepted: sddm.login(user.text, password.text, root.sessionIndex)
            }
            Text {
                id: message
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                color: config.negative
                font.family: config.font
                font.pixelSize: 13
                text: ""
                wrapMode: Text.WordWrap
            }
            Button {
                Layout.fillWidth: true
                text: qsTr("Log in")
                font.family: config.font
                font.pixelSize: 15
                contentItem: Text { text: parent.text; color: config.on_accent; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 8; color: parent.down ? config.accent_alt : config.accent }
                onClicked: sddm.login(user.text, password.text, root.sessionIndex)
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 20
        spacing: 12
        Button {
            text: qsTr("Restart")
            visible: sddm.canReboot
            onClicked: sddm.reboot()
            font.family: config.font
        }
        Button {
            text: qsTr("Shut down")
            visible: sddm.canPowerOff
            onClicked: sddm.powerOff()
            font.family: config.font
        }
    }

    Component.onCompleted: { if (user.text !== "") password.forceActiveFocus(); else user.forceActiveFocus() }
}
