import QtQuick
import Quickshell.Io

Item {
  id: root
  visible: false

  // Preview mode is deliberately local to the QML fixture. It never launches
  // the production controller or accepts a real request.
  property bool fixtureMode: false
  property var fixtureRequests: []
  property var snapshot: ({
    schemaVersion: 1,
    voice: { enabled: false, state: "disabled", microphone: "muted", speaking: false, level: 0, error: "" },
    settings: { mode: "offline", server_kind: "ollama", server_url: "", model: "", execution_model: "", default_coder: "", reduced_motion: false, fixed_position: false, display: "" },
    tasks: [], session: { id: "", transcript: [] }, readiness: { ready: false, checks: [], models: [] }
  })
  property string transportError: ""
  property var lastResponse: ({})
  property bool watching: watchProcess.running
  signal responseReceived(var response)

  function setFixture(next) {
    fixtureMode = true
    snapshot = next
    transportError = ""
  }

  function start() {
    if (!fixtureMode && !watchProcess.running) watchProcess.running = true
  }

  function stop() {
    if (watchProcess.running) watchProcess.signal(15)
  }

  function request(value) {
    if (fixtureMode) { fixtureRequests = fixtureRequests.concat([value]); return }
    start()
    if (watchProcess.running) watchProcess.write(JSON.stringify(value) + "\n")
  }

  function applyLine(line) {
    try {
      var value = JSON.parse(String(line || ""))
      if (value && value.schemaVersion === 1 && value.voice && value.settings) {
        snapshot = value
        transportError = ""
      } else if (value && typeof value.ok === "boolean") {
        lastResponse = value
        if (value.ok === false && value.error)
          transportError = String(value.error.message || "Voice control needs attention.")
        responseReceived(value)
      }
    } catch (error) {
      transportError = "Voice control returned an unreadable response."
    }
  }

  Process {
    id: watchProcess
    command: ["omarchy-voice-control", "--watch"]
    running: false
    stdinEnabled: true
    onStarted: root.request({ action: "status" })
    onExited: function(exitCode) {
      if (!root.fixtureMode && exitCode !== 0)
        root.transportError = "Voice control is not available. Open settings to check local readiness."
    }
    stdout: SplitParser { onRead: function(line) { root.applyLine(line) } }
    stderr: SplitParser { onRead: function(line) { if (String(line).trim() !== "") root.transportError = "Voice control needs attention." } }
  }
}
