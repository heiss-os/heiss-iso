/* Heiss OS users page: ONE centered page with three groups stacked
 *   1. full name + login name   2. computer name   3. password + repeat
 * No in-page buttons: the main Calamares Back/Next buttons are used. The Next button
 * follows config.ready (UsersQmlViewStep::isNextEnabled), i.e. it is enabled when
 * everything is valid. Calamares 3.4.2 gives QML no way to step between sub-pages with
 * the main buttons (ViewManager.next() leaves the whole module), hence one page.
 *
 * Texts: simple dictionary below. The language is the one selected in the installer:
 * Global storage key localeConf.LANG (written by the welcome module when the user picks a
 * language), re-read on every Global.changed(). Fallback: Qt.locale(), then en. (en, ru).
 * To add a language: copy the "en" block in `dict`, change the key to the two-letter code
 * (e.g. "de") and translate the values. Messages that come from the users module itself
 * (login/computer name errors, password quality) are translated by Calamares.
 *
 * Uses only QtQuick.Controls (Kirigami is not shipped in the live image).
 *
 * Switches: useStepTitleAccent (false = plain label font for the title),
 *           useDictionary (false = always English), showLogoRing (false = plain background),
 *           animated (false = old static logo; true = "line drawing" logo, see LogoDraw.qml).
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
    readonly property bool useDictionary: true
    readonly property bool showLogoRing: true
    readonly property bool animated: true
    // ------------------

    // Heiss Dark palette
    readonly property color cText: "#ECEAE5"
    readonly property color cMuted: "#A9A7A1"
    readonly property color cAccent: "#C9B28A"
    readonly property color cField: "#34373B"
    readonly property color cPanel: "#1E1F21"
    readonly property color cError: "#E08A7A"

    // ---- translations ----
    readonly property var dict: ({
        "en": {
            title: "Create your account",
            name: "What is your name?", namePh: "Full name",
            login: "What name do you want to use to log in?", loginPh: "Login name",
            host: "What is the name of this computer?", hostPh: "Computer name",
            pass: "Choose a password", passPh: "Password",
            pass2: "Repeat password", pass2Ph: "Repeat password",
            mismatch: "The passwords do not match."
        },
        "ru": {
            title: "Создайте учётную запись",
            name: "Как вас зовут?", namePh: "Имя и фамилия",
            login: "Какое имя использовать для входа в систему?", loginPh: "Имя для входа",
            host: "Как назвать этот компьютер?", hostPh: "Имя компьютера",
            pass: "Придумайте пароль", passPh: "Пароль",
            pass2: "Повторите пароль", pass2Ph: "Повторите пароль",
            mismatch: "Пароли не совпадают."
        }
    })
    // Source of truth: Global storage localeConf.LANG ("ru", "ru_RU", ...), set by the welcome
    // module in Config::setLocaleIndex() together with QLocale::setDefault(). Qt.locale() is
    // not bound to anything, so it is only the fallback.
    property string lang: "en"
    function selectedLocaleName() {
        var conf = Global.value("localeConf")
        if (conf && conf.LANG && String(conf.LANG).length > 0)
            return String(conf.LANG)
        return Qt.locale().name
    }
    function refreshLang() {
        var l = useDictionary ? selectedLocaleName().substring(0, 2).toLowerCase() : "en"
        lang = dict[l] ? l : "en"
    }
    function tr(key) { return dict[lang][key] }
    Component.onCompleted: refreshLang()
    onVisibleChanged: if (visible) { refreshLang(); logoDraw.restart() }
    Connections {
        target: Global
        function onChanged() { page.refreshLang() }
    }

    readonly property bool passwordsMatch: config.userPassword.length > 0
                                           && config.userPassword === config.userPasswordSecondary

    // Dark background (a QML page is white by default) with the same faint logo ring
    // as the widget pages (see stylesheet.qss, logo-background).
    Rectangle { anchors.fill: parent; color: page.cPanel }
    Image {
        visible: page.showLogoRing && !page.animated
        anchors.fill: parent
        source: Qt.resolvedUrl("logo-bg.png")
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignHCenter
        verticalAlignment: Image.AlignVCenter
    }
    // Animated variant: same size/position as logo-bg.png (800x520 canvas, scale 4.2, centered).
    LogoDraw {
        id: logoDraw
        visible: page.showLogoRing && page.animated
        running: visible && page.visible
        anchors.centerIn: parent
        // logo-bg.png centers the path point (51.25, 51.5); the item is centered on the viewBox (51, 54)
        anchors.horizontalCenterOffset: -0.25 * logoScale
        anchors.verticalCenterOffset: 2.5 * logoScale
        logoScale: 4.2 * Math.min(page.width / 800, page.height / 520)
    }
    // start a new cycle whenever the user arrives on a page (cheap, harmless on other pages)
    Connections {
        target: ViewManager
        function onCurrentStepChanged() { logoDraw.restart() }
    }

    // ---- reusable pieces ----
    component Field: TextField {
        id: f
        property bool bad: false
        Layout.fillWidth: true
        implicitHeight: 38
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

    // ---- centered content ----
    ColumnLayout {
        id: content
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 420)
        spacing: 4

        Label {
            Layout.fillWidth: true
            Layout.bottomMargin: 8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: page.cText
            text: page.tr("title")
            font.family: page.useStepTitleAccent ? "Inter Display" : "Inter"
            font.weight: page.useStepTitleAccent ? Font.ExtraBold : Font.Medium
            font.italic: page.useStepTitleAccent
            font.pixelSize: 26
        }

        // ---- group 1: name + login ----
        FieldLabel { text: page.tr("name") }
        Field {
            id: nameField
            placeholderText: page.tr("namePh")
            text: config.fullName
            onTextEdited: config.setFullName(text)
            onAccepted: loginField.forceActiveFocus()
            Component.onCompleted: forceActiveFocus()
        }

        FieldLabel { Layout.topMargin: 6; text: page.tr("login") }
        Field {
            id: loginField
            placeholderText: page.tr("loginPh")
            text: config.loginName
            bad: text.length > 0 && config.loginNameStatus.length > 0
            onTextEdited: config.setLoginName(text)
            onAccepted: hostField.forceActiveFocus()
            inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
        }
        Msg { visible: loginField.text.length > 0 && config.loginNameStatus.length > 0
              text: config.loginNameStatus }

        // ---- group 2: computer name ----
        FieldLabel { Layout.topMargin: 6; text: page.tr("host") }
        Field {
            id: hostField
            placeholderText: page.tr("hostPh")
            text: config.hostname
            bad: text.length > 0 && config.hostnameStatus.length > 0
            onTextEdited: config.setHostName(text)
            onAccepted: passField.forceActiveFocus()
            inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
        }
        Msg { visible: hostField.text.length > 0 && config.hostnameStatus.length > 0
              text: config.hostnameStatus }

        // ---- group 3: password + repeat ----
        FieldLabel { Layout.topMargin: 6; text: page.tr("pass") }
        Field {
            id: passField
            placeholderText: page.tr("passPh")
            echoMode: TextInput.Password
            passwordMaskDelay: 300
            text: config.userPassword
            onTextEdited: config.setUserPassword(text)
            onAccepted: pass2Field.forceActiveFocus()
            inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhSensitiveData
        }
        Field {
            id: pass2Field
            Layout.topMargin: 4
            placeholderText: page.tr("pass2Ph")
            echoMode: TextInput.Password
            passwordMaskDelay: 300
            text: config.userPasswordSecondary
            bad: text.length > 0 && !page.passwordsMatch
            onTextEdited: config.setUserPasswordSecondary(text)
            inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhSensitiveData
        }
        Msg { visible: pass2Field.text.length > 0 && !page.passwordsMatch
              text: page.tr("mismatch") }
        Msg { visible: page.passwordsMatch && config.userPasswordValidity !== 0
                       && config.userPasswordMessage.length > 0
              color: config.requireStrongPasswords ? page.cError : page.cAccent
              text: config.userPasswordMessage }
    }
}
