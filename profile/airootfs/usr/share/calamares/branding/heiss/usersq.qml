/* Heiss OS users page: ONE centered page with three groups stacked
 *   1. full name + login name   2. computer name   3. password + repeat
 * No in-page buttons: the main Calamares Back/Next buttons are used. The Next button
 * follows config.ready (UsersQmlViewStep::isNextEnabled), i.e. it is enabled when
 * everything is valid. Calamares 3.4.2 gives QML no way to step between sub-pages with
 * the main buttons (ViewManager.next() leaves the whole module), hence one page.
 *
 * Texts: dictionary `dict` below (en, ru), fallback en.
 *   Language source of truth: Qt.locale().name. The welcome module calls QLocale::setDefault()
 *   in Config::setLocaleIndex() every time the user picks a language, so this is exactly the
 *   installer UI language. A Timer re-reads it every 500 ms while the page is shown (no
 *   signals), so a change is visible within about 1 s.
 *   NOT used as primary: Global "localeConf".LANG. The welcome module writes it, but the locale
 *   module then OVERWRITES the whole localeConf (updateGSLocale) with the locale of the
 *   *target system* (depends on the chosen location), so it can say en_US while the UI is
 *   Russian. It is read only as a fallback when Qt.locale() is "C" (no default set).
 *   NEVER connect to Global.changed(): GlobalStorage emits it with its mutex held (deadlock).
 * To add a language: copy the "en" block in `dict`, change the key to the two-letter code
 * (e.g. "de") and translate all values. Nothing else to change. Messages that come from the
 * users module itself (login/computer name errors, password quality) are translated by
 * Calamares.
 *
 * Uses only QtQuick.Controls (Kirigami is not shipped in the live image).
 *
 * Switches: followInstallerLanguage (false = always Qt.locale(), no Global access),
 *           useStepTitleAccent (false = plain label font for the title),
 *           useDictionary (false = always English), showLogoRing (false = plain background),
 *           animated (false = static background logo; true = slow "breathing", see below).
 */
import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: page

    // ---- switches ----
    // false = Qt.locale() only, no Global access at all
    readonly property bool followInstallerLanguage: true
    readonly property bool useStepTitleAccent: true
    readonly property bool useDictionary: true
    readonly property bool showLogoRing: true
    readonly property bool animated: true
    // breathing of the background logo (only used when animated)
    readonly property int  breathMs: 4600        // full cycle
    readonly property real breathScale: 1.035    // 1.0 -> breathScale -> 1.0
    readonly property real breathOpacityMin: 0.65 // x the base opacity; max is 1.0x
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
            host: "Как называется этот компьютер?", hostPh: "Имя компьютера",
            pass: "Придумайте пароль", passPh: "Пароль",
            pass2: "Повторите пароль", pass2Ph: "Повторите пароль",
            mismatch: "Пароли не совпадают."
        }
    })
    property string lang: "en"
    // true only while the page is really on screen (the QML window is hidden by Calamares when
    // another step is shown, but Item.visible alone does not reflect that)
    readonly property bool pageActive: page.visible && (!page.Window.window || page.Window.window.visible)
    function selectedLocaleName() {
        var n = Qt.locale().name
        if (followInstallerLanguage && (!n || n === "C")) {
            var conf = Global.value("localeConf")   // fallback only, see header
            if (conf && conf.LANG && String(conf.LANG).length > 0) return String(conf.LANG)
        }
        return n
    }
    function refreshLang() {
        var l = useDictionary ? selectedLocaleName().substring(0, 2).toLowerCase() : "en"
        var n = dict[l] ? l : "en"
        if (n !== lang) lang = n   // update only on a real change
    }
    function tr(key) { var d = dict[lang]; return (d && d[key] !== undefined) ? d[key] : dict["en"][key] }
    Component.onCompleted: refreshLang()
    // Timer, not signals: runs on the GUI thread between events, never inside a GlobalStorage write
    Timer {
        interval: 500
        repeat: true
        running: page.pageActive
        triggeredOnStart: true
        onTriggered: page.refreshLang()
    }

    readonly property bool passwordsMatch: config.userPassword.length > 0
                                           && config.userPassword === config.userPasswordSecondary

    Rectangle { anchors.fill: parent; color: page.cPanel }
    // Big faint logo (same file/size/position as the widget pages, see stylesheet.qss).
    // The holder breathes: scale 1.0 -> breathScale -> 1.0 while opacity goes
    // breathOpacityMin -> 1.0 -> breathOpacityMin (x the faint base opacity), InOutSine.
    Item {
        id: logoHolder
        anchors.fill: parent
        visible: page.showLogoRing
        transformOrigin: Item.Center
        readonly property bool breathing: page.animated && page.pageActive
        onBreathingChanged: {
            // new cycle every time the page becomes active; rest state when it is not
            breathe.stop()
            scale = 1.0
            opacity = page.animated ? page.breathOpacityMin : 1.0
            if (breathing) breathe.start()
        }
        Component.onCompleted: opacity = page.animated ? page.breathOpacityMin : 1.0

        Image {
            anchors.fill: parent
            source: Qt.resolvedUrl("logo-bg.png")
            fillMode: Image.PreserveAspectFit
            horizontalAlignment: Image.AlignHCenter
            verticalAlignment: Image.AlignVCenter
        }

        SequentialAnimation {
            id: breathe
            loops: Animation.Infinite
            ParallelAnimation {
                NumberAnimation { target: logoHolder; property: "scale"
                                  from: 1.0; to: page.breathScale
                                  duration: page.breathMs / 2; easing.type: Easing.InOutSine }
                NumberAnimation { target: logoHolder; property: "opacity"
                                  from: page.breathOpacityMin; to: 1.0
                                  duration: page.breathMs / 2; easing.type: Easing.InOutSine }
            }
            ParallelAnimation {
                NumberAnimation { target: logoHolder; property: "scale"
                                  from: page.breathScale; to: 1.0
                                  duration: page.breathMs / 2; easing.type: Easing.InOutSine }
                NumberAnimation { target: logoHolder; property: "opacity"
                                  from: 1.0; to: page.breathOpacityMin
                                  duration: page.breathMs / 2; easing.type: Easing.InOutSine }
            }
        }
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
        font.family: "Inter"; font.weight: Font.DemiBold; font.pixelSize: 13
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
