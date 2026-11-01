/* Heiss OS users page: three centered steps inside one Calamares module.
 *   1. name + login name   2. computer name   3. password
 * The in-page Back/Continue buttons move between the steps; the Calamares Next
 * button becomes active when config.ready is true (everything valid, step 3).
 *
 * Uses only QtQuick.Controls (Kirigami is not shipped in the live image).
 * Fonts: Inter Display ExtraBold Italic for the step title, Medium for labels,
 * Regular for fields and hints, SemiBold for buttons (see branding/fonts/README.txt).
 *
 * Switch: set useStepTitleAccent to false to use the plain label font for titles.
 */
import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: page

    // ---- switches ----
    readonly property bool useStepTitleAccent: true
    // ------------------

    // Heiss Dark palette
    readonly property color cText: "#ECEAE5"
    readonly property color cMuted: "#A9A7A1"
    readonly property color cAccent: "#C9B28A"
    readonly property color cField: "#34373B"
    readonly property color cPanel: "#1E1F21"
    readonly property color cError: "#E08A7A"

    property int step: 0   // 0 = name, 1 = computer, 2 = password

    readonly property bool step0Ok: config.fullName.length > 0
                                    && config.loginName.length > 0
                                    && config.loginNameStatus.length === 0
    readonly property bool step1Ok: config.hostname.length > 0
                                    && config.hostnameStatus.length === 0
    readonly property bool passwordsMatch: config.userPassword.length > 0
                                           && config.userPassword === config.userPasswordSecondary
    readonly property bool stepOk: step === 0 ? step0Ok : (step === 1 ? step1Ok : config.ready)

    function goNext() { if (step < 2 && stepOk) step++ }
    function goBack() { if (step > 0) step-- }

    // ---- reusable pieces ----
    component Field: TextField {
        id: f
        property bool bad: false
        Layout.fillWidth: true
        implicitHeight: 40
        color: page.cText
        placeholderTextColor: page.cMuted
        selectionColor: page.cAccent
        selectedTextColor: page.cPanel
        font.family: "Inter"; font.weight: Font.Normal; font.pixelSize: 14
        leftPadding: 12; rightPadding: 12
        background: Rectangle {
            radius: 6
            color: page.cField
            border.width: f.activeFocus || f.bad ? 1 : 0
            border.color: f.bad ? page.cError : page.cAccent
        }
    }

    component FieldLabel: Label {
        color: page.cText
        font.family: "Inter"; font.weight: Font.Medium; font.pixelSize: 13
    }

    component Hint: Label {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: page.cMuted
        font.family: "Inter"; font.weight: Font.Normal; font.pixelSize: 12
    }

    component Msg: Label {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: page.cError
        font.family: "Inter"; font.weight: Font.Medium; font.pixelSize: 12
    }

    component Btn: Button {
        id: b
        property bool primary: false
        implicitHeight: 38
        implicitWidth: 120
        font.family: "Inter"; font.weight: Font.DemiBold; font.pixelSize: 14
        contentItem: Text {
            text: b.text; font: b.font
            color: !b.enabled ? page.cMuted : (b.primary ? page.cPanel : page.cText)
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: b.primary ? (b.enabled ? page.cAccent : page.cField) : page.cField
            opacity: b.down ? 0.8 : 1.0
        }
    }

    // ---- centered content ----
    ColumnLayout {
        id: content
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 420)
        spacing: 12

        // step indicator: three short bars
        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: 6
            Repeater {
                model: 3
                Rectangle {
                    width: 28; height: 3; radius: 2
                    color: index === page.step ? page.cAccent : page.cMuted
                    opacity: index === page.step ? 1.0 : 0.35
                }
            }
        }

        Label {
            Layout.fillWidth: true
            Layout.topMargin: 8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: page.cText
            text: page.step === 0 ? qsTr("What is your name?")
                : page.step === 1 ? qsTr("Name this computer")
                : qsTr("Choose a password")
            font.family: page.useStepTitleAccent ? "Inter Display" : "Inter"
            font.weight: page.useStepTitleAccent ? Font.ExtraBold : Font.Medium
            font.italic: page.useStepTitleAccent
            font.pixelSize: 30
        }

        // ---- step 1 ----
        ColumnLayout {
            visible: page.step === 0
            Layout.fillWidth: true
            spacing: 6

            FieldLabel { text: qsTr("Your name") }
            Field {
                id: nameField
                placeholderText: qsTr("Full name")
                text: config.fullName
                onTextEdited: config.setFullName(text)
                onAccepted: loginField.forceActiveFocus()
                Component.onCompleted: if (page.step === 0) forceActiveFocus()
            }

            FieldLabel { Layout.topMargin: 8; text: qsTr("What name do you want to use to log in?") }
            Field {
                id: loginField
                placeholderText: qsTr("Login name")
                text: config.loginName
                bad: text.length > 0 && config.loginNameStatus.length > 0
                onTextEdited: config.setLoginName(text)
                onAccepted: page.goNext()
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
            }
            Msg { visible: loginField.text.length > 0 && config.loginNameStatus.length > 0
                  text: config.loginNameStatus }
            Hint { text: qsTr("If more than one person will use this computer, you can create more accounts after installation.") }
        }

        // ---- step 2 ----
        ColumnLayout {
            visible: page.step === 1
            Layout.fillWidth: true
            spacing: 6

            FieldLabel { text: qsTr("What is the name of this computer?") }
            Field {
                id: hostField
                placeholderText: qsTr("Computer name")
                text: config.hostname
                bad: text.length > 0 && config.hostnameStatus.length > 0
                onTextEdited: config.setHostName(text)
                onAccepted: page.goNext()
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
            }
            Msg { visible: hostField.text.length > 0 && config.hostnameStatus.length > 0
                  text: config.hostnameStatus }
            Hint { text: qsTr("This name is used if you make the computer visible to others on a network.") }
        }

        // ---- step 3 ----
        ColumnLayout {
            visible: page.step === 2
            Layout.fillWidth: true
            spacing: 6

            FieldLabel { text: qsTr("Password") }
            Field {
                id: passField
                placeholderText: qsTr("Password")
                echoMode: TextInput.Password
                passwordMaskDelay: 300
                text: config.userPassword
                onTextEdited: config.setUserPassword(text)
                onAccepted: pass2Field.forceActiveFocus()
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhSensitiveData
            }

            FieldLabel { Layout.topMargin: 8; text: qsTr("Repeat password") }
            Field {
                id: pass2Field
                placeholderText: qsTr("Repeat password")
                echoMode: TextInput.Password
                passwordMaskDelay: 300
                text: config.userPasswordSecondary
                bad: text.length > 0 && !page.passwordsMatch
                onTextEdited: config.setUserPasswordSecondary(text)
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhSensitiveData
            }
            Msg { visible: pass2Field.text.length > 0 && !page.passwordsMatch
                  text: qsTr("The passwords do not match.") }
            Msg { visible: page.passwordsMatch && config.userPasswordValidity !== 0
                           && config.userPasswordMessage.length > 0
                  color: config.requireStrongPasswords ? page.cError : page.cAccent
                  text: config.userPasswordMessage }
            Hint { text: qsTr("A good password mixes letters, numbers and punctuation and is at least eight characters long.") }
        }

        // ---- in-page navigation ----
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 16
            spacing: 12

            Btn {
                text: qsTr("Back")
                visible: page.step > 0
                onClicked: page.goBack()
            }
            Item { Layout.fillWidth: true }
            Btn {
                text: qsTr("Continue")
                primary: true
                visible: page.step < 2
                enabled: page.stepOk
                onClicked: page.goNext()
            }
        }
    }
}
