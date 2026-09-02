import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Item {
  id: root

  property var shell: null
  property bool closingFromHost: false
  property int step: 1
  property string selectedAgent: ""
  property string statusText: ""
  property bool busy: false
  property string productName: ""
  property string productTagline: ""
  property bool hermesDesktopAvailable: false

  readonly property color foreground: Color.foreground
  readonly property color background: Color.background
  readonly property color accent: Color.accent
  readonly property color urgent: Color.urgent
  readonly property string fontFamily: "Manrope"

  function launchMode(agent) {
    switch (agent) {
      case "codex": return "codex:--approve-for-me"
      case "claude": return "claude:--permission-mode=auto"
      case "hermes": return "hermes:--yolo"
    }
    return ""
  }

  function open(payloadJson) {
    closingFromHost = false
    window.visible = true
    stateProc.command = ["omarchy-setup-ai-state", "open"]
    stateProc.running = true
    productProc.running = true
    hermesDesktopProc.running = true
    Qt.callLater(function() { window.requestActivate() })
  }

  function close() {
    closingFromHost = true
    window.visible = false
    closingFromHost = false
  }

  function requestClose() {
    if (shell && typeof shell.hide === "function") shell.hide("maslow.ai-setup")
    else window.visible = false
  }

  function saveStep(next) {
    step = next
    stateWriteProc.command = ["omarchy-setup-ai-state", "step", String(next)]
    stateWriteProc.running = true
  }

  function chooseAgent(agent) {
    selectedAgent = agent
    step = 3
    stateWriteProc.command = ["omarchy-setup-ai-state", "select", agent]
    stateWriteProc.running = true
  }

  function beginInstall() {
    busy = true
    statusText = "Opening the installer…"
    actionProc.actionKind = "install"
    actionProc.command = ["omarchy-launch-floating-terminal-with-presentation", "omarchy-agent-install", selectedAgent]
    actionProc.running = true
  }

  function completeWithoutAgent() {
    stateWriteProc.closeAfterWrite = true
    stateWriteProc.command = ["omarchy-setup-ai-state", "complete"]
    stateWriteProc.running = true
  }

  function deferSetup() {
    stateWriteProc.closeAfterWrite = true
    stateWriteProc.command = ["omarchy-setup-ai-state", "defer"]
    stateWriteProc.running = true
  }

  function finishAndLaunch() {
    busy = true
    statusText = "Setting " + agentName(selectedAgent) + " as your default…"
    actionProc.actionKind = "default"
    actionProc.command = ["omarchy-agent-default-set", selectedAgent]
    actionProc.running = true
  }

  function finishOnly() {
    stateWriteProc.closeAfterWrite = true
    stateWriteProc.command = ["omarchy-setup-ai-state", "complete"]
    stateWriteProc.running = true
  }

  function agentName(agent) {
    if (agent === "codex") return "Codex"
    if (agent === "claude") return "Claude Code"
    if (agent === "hermes") return "Hermes"
    return "AI agent"
  }

  Process {
    id: productProc
    command: ["omarchy-branding-product", "--json"]
    stdout: StdioCollector { id: productOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) return
      try {
        var manifest = JSON.parse(productOutput.text)
        root.productName = String(manifest.product.name)
        root.productTagline = String(manifest.product.tagline)
      } catch (e) {
        root.statusText = "Maslow OS product information could not be read."
      }
    }
  }

  Process {
    id: hermesDesktopProc
    command: ["omarchy-pkg-available", "hermes-desktop"]
    onExited: function(exitCode) { root.hermesDesktopAvailable = exitCode === 0 }
  }

  Process {
    id: stateProc
    stdout: StdioCollector {
      id: stateOutput
      waitForEnd: true
    }
    stderr: StdioCollector { id: stateError; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        statusText = stateError.text.trim() || "AI setup state needs attention."
        return
      }
      try {
        var state = JSON.parse(stateOutput.text)
        step = Number(state.currentStep || 1)
        selectedAgent = String(state.selectedAgent || "")
      } catch (e) {
        statusText = "AI setup state could not be read."
      }
    }
  }

  Process {
    id: stateWriteProc
    property bool closeAfterWrite: false
    stderr: StdioCollector { id: stateWriteError; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        statusText = stateWriteError.text.trim() || "Could not save AI setup progress."
        closeAfterWrite = false
        return
      }
      if (closeAfterWrite) {
        closeAfterWrite = false
        root.requestClose()
      }
    }
  }

  Process {
    id: actionProc
    property string actionKind: ""
    stderr: StdioCollector { id: actionError; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode === 130) {
        root.busy = false
        root.statusText = "Canceled. Nothing was selected or launched."
        return
      }
      if (exitCode !== 0) {
        root.busy = false
        root.statusText = actionError.text.trim() || "This step needs attention. You can retry."
        return
      }
      if (actionKind === "install") {
        actionKind = "trust"
        root.statusText = "Saving your permission choice…"
        command = ["omarchy-agent-trust", "confirm", root.selectedAgent, root.launchMode(root.selectedAgent), "--yes"]
        running = true
      } else if (actionKind === "trust") {
        root.busy = false
        root.statusText = ""
        root.saveStep(4)
      } else if (actionKind === "default") {
        root.statusText = "Opening the provider sign-in flow…"
        actionKind = "launch"
        stateWriteProc.command = ["omarchy-setup-ai-state", "complete"]
        stateWriteProc.running = true
        command = ["omarchy-agent", "--agent", root.selectedAgent]
        running = true
      } else if (actionKind === "launch") {
        root.busy = false
        root.requestClose()
      }
    }
  }

  Process {
    id: utilityProc
    onExited: root.requestClose()
  }

  FloatingWindow {
    id: window
    title: (root.productName || "Maslow OS") + " AI Setup"
    color: root.background
    implicitWidth: 720
    implicitHeight: 620
    minimumSize: Qt.size(560, 500)

    onVisibleChanged: {
      if (!visible && !root.closingFromHost && root.shell && typeof root.shell.hide === "function")
        root.shell.hide("maslow.ai-setup")
    }

    FocusScope {
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: root.requestClose()

      Column {
        anchors.fill: parent
        anchors.margins: Style.space(24)
        spacing: Style.space(18)

        Row {
          width: parent.width
          spacing: Style.space(12)

          Text {
            text: ""
            color: root.accent
            font.family: "omarchy"
            font.pixelSize: 38
            Accessible.role: Accessible.Graphic
            Accessible.name: "Maslow mark"
          }
          Column {
            anchors.verticalCenter: parent.verticalCenter
            Text {
              text: root.productName
              textFormat: Text.PlainText
              color: root.foreground
              font.family: root.fontFamily
              font.weight: Font.DemiBold
              font.pixelSize: 24
            }
            Text {
              text: root.productTagline
              textFormat: Text.PlainText
              color: Qt.darker(root.foreground, 1.3)
              font.family: root.fontFamily
              font.pixelSize: 14
            }
          }
        }

        Row {
          width: parent.width
          spacing: Style.space(8)
          Repeater {
            model: 4
            Rectangle {
              required property int index
              width: (parent.width - Style.space(24)) / 4
              height: 4
              radius: 2
              color: index + 1 <= root.step ? root.accent : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.18)
            }
          }
        }

        StackLayout {
          width: parent.width
          height: parent.height - 160
          currentIndex: root.step - 1

          Column {
            spacing: Style.space(18)
            Text {
              text: "Welcome to " + root.productName
              textFormat: Text.PlainText
              color: root.foreground
              font.family: root.fontFamily
              font.weight: Font.DemiBold
              font.pixelSize: 28
            }
            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: "Choose one AI agent now, or finish setup without one. You can return anytime from Setup → AI."
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: 16
            }
            Item { width: 1; height: Style.space(12) }
            Button {
              text: "Continue"
              focusable: true
              Accessible.name: "Continue to choose an AI agent"
              onClicked: root.saveStep(2)
            }
            Button {
              text: "Not now"
              focusable: true
              Accessible.name: "Stop opening AI setup automatically"
              onClicked: root.deferSetup()
            }
            Button {
              text: "Finish without an agent"
              focusable: true
              Accessible.name: "Complete setup without installing an AI agent"
              onClicked: root.completeWithoutAgent()
            }
          }

          Column {
            spacing: Style.space(14)
            Text {
              text: "Choose an AI agent"
              color: root.foreground
              font.family: root.fontFamily
              font.weight: Font.DemiBold
              font.pixelSize: 28
            }
            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: "These are command-line agents. They open in a terminal and use their provider’s own authentication flow."
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: 15
            }
            Button { text: "Codex — OpenAI"; focusable: true; Accessible.name: "Choose Codex command-line agent"; onClicked: root.chooseAgent("codex") }
            Button { text: "Claude Code — Anthropic"; focusable: true; Accessible.name: "Choose Claude Code command-line agent"; onClicked: root.chooseAgent("claude") }
            Button { text: "Hermes — Nous Research"; focusable: true; Accessible.name: "Choose Hermes command-line agent"; onClicked: root.chooseAgent("hermes") }
            Button {
              visible: root.hermesDesktopAvailable
              text: "Hermes Desktop — graphical app"
              focusable: true
              Accessible.name: "Install the Hermes Desktop graphical application"
              onClicked: {
                utilityProc.command = ["omarchy-launch-floating-terminal-with-presentation", "omarchy-install-ai-hermes"]
                utilityProc.running = true
              }
            }
            Button {
              text: "More agents"
              focusable: true
              Accessible.name: "Open the complete AI agent list"
              onClicked: {
                utilityProc.command = ["omarchy-menu", "setup.default.agent"]
                utilityProc.running = true
              }
            }
            Button { text: "Back"; focusable: true; onClicked: root.saveStep(1) }
          }

          Column {
            spacing: Style.space(16)
            Text {
              text: "Review permissions"
              color: root.foreground
              font.family: root.fontFamily
              font.weight: Font.DemiBold
              font.pixelSize: 28
            }
            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: root.agentName(root.selectedAgent) + " will launch in autonomous mode (“" + root.launchMode(root.selectedAgent) + "”). It may run commands, modify or delete files, install software, and access data available to your account."
              textFormat: Text.PlainText
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: 16
            }
            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: "Maslow OS never reads or stores provider credentials. After installation, authentication continues in the provider’s terminal or browser flow. Opening that flow does not mean authentication succeeded."
              color: Qt.darker(root.foreground, 1.2)
              font.family: root.fontFamily
              font.pixelSize: 14
            }
            Button {
              text: root.busy ? "Working…" : "I understand — install and continue"
              focusable: true
              enabled: !root.busy
              Accessible.name: "Confirm permissions and install " + root.agentName(root.selectedAgent)
              onClicked: root.beginInstall()
            }
            Button { text: "Back"; focusable: true; enabled: !root.busy; onClicked: root.saveStep(2) }
          }

          Column {
            spacing: Style.space(16)
            Text {
              text: "Ready"
              color: root.foreground
              font.family: root.fontFamily
              font.weight: Font.DemiBold
              font.pixelSize: 28
            }
            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: root.agentName(root.selectedAgent) + " is installed. Make it your default and continue to the provider’s authentication flow, or finish here."
              textFormat: Text.PlainText
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: 16
            }
            Button {
              text: root.busy ? "Opening…" : "Make default and open"
              focusable: true
              enabled: !root.busy
              Accessible.name: "Make " + root.agentName(root.selectedAgent) + " the default and open provider authentication"
              onClicked: root.finishAndLaunch()
            }
            Button { text: "Finish for now"; focusable: true; enabled: !root.busy; onClicked: root.finishOnly() }
            Text {
              text: "Recommended setup"
              color: root.foreground
              font.family: root.fontFamily
              font.weight: Font.DemiBold
              font.pixelSize: 17
            }
            Row {
              spacing: Style.space(10)
              Button {
                text: "Fingerprint"
                focusable: true
                Accessible.name: "Set up fingerprint authentication"
                onClicked: {
                  utilityProc.command = ["omarchy-menu", "setup.security.fingerprint"]
                  utilityProc.running = true
                }
              }
              Button {
                text: "Dictation"
                focusable: true
                Accessible.name: "Set up voice dictation"
                onClicked: {
                  utilityProc.command = ["omarchy-menu", "install.ai.dictation"]
                  utilityProc.running = true
                }
              }
            }
          }
        }

        Text {
          width: parent.width
          visible: root.statusText !== ""
          wrapMode: Text.WordWrap
          text: root.statusText
          textFormat: Text.PlainText
          color: root.statusText.indexOf("attention") >= 0 ? root.urgent : root.foreground
          font.family: root.fontFamily
          font.pixelSize: 14
          Accessible.role: Accessible.AlertMessage
          Accessible.name: root.statusText
        }
      }
    }
  }
}
