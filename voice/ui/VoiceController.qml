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
    settings: { mode: "offline", server_kind: "ollama", server_url: "", model: "", execution_model: "", default_coder: "", reduced_motion: false, fixed_position: false, orb_position: null, display: "" },
    tasks: [], session: { id: "", transcript: [] }, readiness: { ready: false, checks: [], models: [] }
  })
  // Keep long-lived snapshot branches stable while the 20 Hz voice meter
  // changes. QML repeaters treat a replacement JavaScript array as a new
  // model, even when every task inside it has the same content.
  property var voice: snapshot.voice
  property var settings: snapshot.settings
  property var tasks: snapshot.tasks
  property var visibleTasks: snapshot.tasks
  property var session: snapshot.session
  property var readiness: snapshot.readiness
  property string transportError: ""
  property var lastResponse: ({})
  property bool watching: watchProcess.running
  property bool watchingRequested: false
  signal responseReceived(var response)

  function setFixture(next) {
    stop()
    fixtureMode = true
    applySnapshot(next)
    transportError = ""
  }

  function semanticEqual(left, right) {
    if (left === right) return true
    if (left === null || right === null || typeof left !== typeof right) return false
    if (typeof left !== "object") return false
    var leftArray = Array.isArray(left)
    if (leftArray !== Array.isArray(right)) return false
    if (leftArray) {
      if (left.length !== right.length) return false
      for (var index = 0; index < left.length; index++)
        if (!semanticEqual(left[index], right[index])) return false
      return true
    }
    var leftKeys = Object.keys(left)
    var rightKeys = Object.keys(right)
    if (leftKeys.length !== rightKeys.length) return false
    for (var keyIndex = 0; keyIndex < leftKeys.length; keyIndex++) {
      var key = leftKeys[keyIndex]
      if (!Object.prototype.hasOwnProperty.call(right, key) || !semanticEqual(left[key], right[key])) return false
    }
    return true
  }

  function reuseUnchanged(previous, incoming) {
    return semanticEqual(previous, incoming) ? previous : incoming
  }

  function reconcileTasks(previous, incoming) {
    if (!Array.isArray(previous) || !Array.isArray(incoming)) return incoming
    var previousById = Object.create(null)
    for (var previousIndex = 0; previousIndex < previous.length; previousIndex++) {
      var previousTask = previous[previousIndex]
      if (previousTask && previousTask.id !== undefined)
        previousById[String(previousTask.id)] = previousTask
    }
    var next = []
    var arrayUnchanged = previous.length === incoming.length
    for (var incomingIndex = 0; incomingIndex < incoming.length; incomingIndex++) {
      var incomingTask = incoming[incomingIndex]
      var previousTask = incomingTask && incomingTask.id !== undefined ? previousById[String(incomingTask.id)] : undefined
      var task = previousTask && semanticEqual(previousTask, incomingTask) ? previousTask : incomingTask
      next.push(task)
      if (previous[incomingIndex] !== task) arrayUnchanged = false
    }
    return arrayUnchanged ? previous : next
  }

  function visibleTaskList(tasks) {
    return tasks.filter(function(task) { return task.dismissed !== true })
  }

  function applySnapshot(value) {
    var nextVoice = reuseUnchanged(voice, value.voice)
    var nextSettings = reuseUnchanged(settings, value.settings)
    var nextTasks = reconcileTasks(tasks, Array.isArray(value.tasks) ? value.tasks : [])
    var nextSession = reuseUnchanged(session, value.session)
    var nextReadiness = reuseUnchanged(readiness, value.readiness)
    if (voice !== nextVoice) voice = nextVoice
    if (settings !== nextSettings) settings = nextSettings
    if (tasks !== nextTasks) {
      tasks = nextTasks
      visibleTasks = visibleTaskList(nextTasks)
    }
    if (session !== nextSession) session = nextSession
    if (readiness !== nextReadiness) readiness = nextReadiness
    snapshot = {
      schemaVersion: value.schemaVersion,
      voice: voice,
      settings: settings,
      tasks: tasks,
      session: session,
      readiness: readiness
    }
  }

  function start() {
    if (fixtureMode) return
    watchingRequested = true
    if (!watchProcess.running) watchProcess.running = true
  }

  function stop() {
    watchingRequested = false
    reconnectTimer.stop()
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
        applySnapshot(value)
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

  Timer {
    id: reconnectTimer
    interval: 2000
    onTriggered: if (root.watchingRequested && !root.fixtureMode) root.start()
  }

  Process {
    id: watchProcess
    command: ["omarchy-voice-control", "--watch"]
    running: false
    stdinEnabled: true
    onStarted: { reconnectTimer.stop(); root.request({ action: "status" }) }
    onExited: function(exitCode) {
      if (!root.fixtureMode && root.watchingRequested) {
        root.transportError = "Voice is reconnecting."
        reconnectTimer.restart()
      }
    }
    stdout: SplitParser { onRead: function(line) { root.applyLine(line) } }
    stderr: SplitParser { onRead: function(line) { if (String(line).trim() !== "") root.transportError = "Voice control needs attention." } }
  }
}
