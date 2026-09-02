import QtQuick
import QtQuick.Controls
import QtTextToSpeech
import SddmComponents 2.0

Rectangle {
  id: root
  width: 1280
  height: 720
  color: highContrast ? "#000000" : "#121D35"
  focus: true

  property bool loginFailed: false
  property bool signingIn: false
  readonly property bool capsLockOn: keyboard.capsLock
  property bool speechEnabled: config.boolValue("SpeechEnabled")
  property string pendingSpeech: ""
  readonly property bool highContrast: config.boolValue("HighContrast")
  readonly property bool largeText: config.boolValue("LargeText")
  readonly property real textScale: largeText ? 1.25 : 1
  readonly property color foreground: "#FFFFFF"
  readonly property color secondary: highContrast ? "#FFFFFF" : "#D9DEE8"
  readonly property color accent: "#6DC4AD"
  readonly property color urgent: "#FF9BAD"
  readonly property int sessionIndex: {
    for (var i = 0; i < sessionModel.rowCount(); i++) {
      var name = (sessionModel.data(sessionModel.index(i, 0), Qt.DisplayRole) || "").toString()
      if (name.indexOf("uwsm") !== -1)
        return i
    }
    return sessionModel.lastIndex
  }

  function announce(message) {
    if (!speechEnabled || !message)
      return
    if (speech.state === TextToSpeech.Ready) {
      pendingSpeech = ""
      speech.say(message)
    } else {
      pendingSpeech = message
    }
  }

  function toggleSpeech() {
    if (speechEnabled) {
      if (speech.state === TextToSpeech.Ready)
        speech.say("Spoken login disabled.")
      speechEnabled = false
      pendingSpeech = ""
    } else {
      speechEnabled = true
      announce("Spoken login enabled.")
    }
  }

  function submit() {
    if (signingIn)
      return
    if (!username.text.trim()) {
      statusText.text = "Enter your username."
      username.forceActiveFocus()
      announce(statusText.text)
      return
    }
    if (!password.text) {
      statusText.text = "Enter your password."
      password.forceActiveFocus()
      announce(statusText.text)
      return
    }
    loginFailed = false
    signingIn = true
    statusText.text = "Signing in…"
    announce("Signing in.")
    sddm.login(username.text.trim(), password.text, sessionIndex)
  }

  function clearForm() {
    password.text = ""
    loginFailed = false
    signingIn = false
    statusText.text = ""
    password.forceActiveFocus()
    announce("Password cleared.")
  }

  function handleKey(event) {
    if (event.key === Qt.Key_F5) {
      toggleSpeech()
      event.accepted = true
    } else if (event.key === Qt.Key_Escape) {
      clearForm()
      event.accepted = true
    }
  }

  TextToSpeech {
    id: speech
    onStateChanged: {
      if (state === TextToSpeech.Ready && root.speechEnabled && root.pendingSpeech) {
        var message = root.pendingSpeech
        root.pendingSpeech = ""
        say(message)
      }
    }
  }

  Connections {
    target: sddm
    function onLoginFailed() {
      root.signingIn = false
      root.loginFailed = true
      password.text = ""
      statusText.text = "That username or password did not work. Try again."
      password.forceActiveFocus()
      root.announce(statusText.text)
    }
    function onLoginSucceeded() {
      root.loginFailed = false
      root.signingIn = false
      statusText.text = "Welcome to Maslow OS."
      root.announce(statusText.text)
    }
  }

  Keys.onPressed: event => handleKey(event)

  Column {
    anchors.centerIn: parent
    width: Math.min(520, root.width - 48)
    spacing: 28

    Image {
      source: "logo.png"
      width: Math.min(440, parent.width)
      height: sourceSize.width > 0 ? Math.round(width * sourceSize.height / sourceSize.width) : 112
      fillMode: Image.PreserveAspectFit
      anchors.horizontalCenter: parent.horizontalCenter
      Accessible.role: Accessible.Graphic
      Accessible.name: "Maslow OS"
    }

    Text {
      text: "Welcome back"
      color: root.foreground
      font.family: "Manrope"
      font.pixelSize: 28 * root.textScale
      font.weight: Font.DemiBold
      anchors.horizontalCenter: parent.horizontalCenter
    }

    Column {
      width: parent.width
      spacing: 8

      Label {
        text: "Username"
        color: root.secondary
        font.family: "Manrope"
        font.pixelSize: 14 * root.textScale
        font.weight: Font.DemiBold
      }

      TextField {
        id: username
        width: parent.width
        height: 52 * root.textScale
        text: userModel.lastUser
        selectByMouse: true
        enabled: !root.signingIn
        color: root.foreground
        placeholderText: "maslow"
        placeholderTextColor: "#8C95A8"
        font.family: "Manrope"
        font.pixelSize: 17 * root.textScale
        background: Rectangle {
          radius: 8
          color: "#1A2948"
          border.width: username.activeFocus ? 3 : 1
          border.color: username.activeFocus ? root.accent : "#8C95A8"
        }
        KeyNavigation.tab: password
        Keys.onPressed: event => {
          root.handleKey(event)
          if (!event.accepted && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) {
            root.submit()
            event.accepted = true
          }
        }
        onActiveFocusChanged: if (activeFocus) root.announce("Username.")
        Accessible.role: Accessible.EditableText
        Accessible.name: "Username"
        Accessible.description: "Your Maslow OS account username"
        Accessible.focusable: true
        Accessible.focused: activeFocus
      }
    }

    Column {
      width: parent.width
      spacing: 8

      Label {
        text: "Password"
        color: root.secondary
        font.family: "Manrope"
        font.pixelSize: 14 * root.textScale
        font.weight: Font.DemiBold
      }

      TextField {
        id: password
        width: parent.width
        height: 52 * root.textScale
        echoMode: TextInput.Password
        passwordCharacter: "\u2022"
        enabled: !root.signingIn
        color: root.foreground
        placeholderText: "Enter your password"
        placeholderTextColor: "#8C95A8"
        font.family: "Manrope"
        font.pixelSize: 17 * root.textScale
        background: Rectangle {
          radius: 8
          color: "#1A2948"
          border.width: password.activeFocus ? 3 : 1
          border.color: root.loginFailed ? root.urgent : (password.activeFocus ? root.accent : "#8C95A8")
        }
        KeyNavigation.tab: signInButton
        Keys.onPressed: event => {
          root.handleKey(event)
          if (!event.accepted && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) {
            root.submit()
            event.accepted = true
          }
        }
        onActiveFocusChanged: if (activeFocus) root.announce("Password. Your password will not be spoken.")
        Accessible.role: Accessible.EditableText
        Accessible.name: "Password"
        Accessible.description: "Your password is hidden and is never spoken"
        Accessible.passwordEdit: true
        Accessible.focusable: true
        Accessible.focused: activeFocus
      }

      Text {
        visible: root.capsLockOn
        text: "Caps Lock is on"
        color: root.urgent
        font.family: "Manrope"
        font.pixelSize: 14 * root.textScale
        Accessible.role: Accessible.AlertMessage
        Accessible.name: text
      }
    }

    Button {
      id: signInButton
      width: parent.width
      height: 52 * root.textScale
      enabled: !root.signingIn
      text: root.signingIn ? "Signing in…" : "Sign in"
      font.family: "Manrope"
      font.pixelSize: 16 * root.textScale
      font.weight: Font.DemiBold
      KeyNavigation.tab: username
      Keys.onPressed: event => root.handleKey(event)
      onClicked: root.submit()
      Accessible.role: Accessible.Button
      Accessible.name: text
      Accessible.focusable: true
      Accessible.focused: activeFocus
      background: Rectangle {
        radius: 8
        color: signInButton.pressed ? "#8AD7C1" : root.accent
        border.width: signInButton.activeFocus ? 3 : 0
        border.color: "#FFFFFF"
      }
      contentItem: Text {
        text: signInButton.text
        color: "#121D35"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font: signInButton.font
      }
    }

    Text {
      id: statusText
      width: parent.width
      text: ""
      color: root.loginFailed ? root.urgent : root.secondary
      font.family: "Manrope"
      font.pixelSize: 14 * root.textScale
      horizontalAlignment: Text.AlignHCenter
      wrapMode: Text.Wrap
      Accessible.role: Accessible.AlertMessage
      Accessible.name: text
    }

    Text {
      width: parent.width
      text: "F5 Spoken login  •  Esc Clear"
      color: root.secondary
      font.family: "Manrope"
      font.pixelSize: 13 * root.textScale
      horizontalAlignment: Text.AlignHCenter
    }
  }

  Component.onCompleted: {
    if (username.text)
      password.forceActiveFocus()
    else
      username.forceActiveFocus()
    announce("Maslow OS login. Press F5 to toggle spoken login.")
  }
}
