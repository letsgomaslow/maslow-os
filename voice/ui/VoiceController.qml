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
    tasks: [], session: { id: "", transcript: [] }, readiness: { ready: false, checks: [], models: [] }, task_view_request: null
  })
  // Keep long-lived snapshot branches stable while the 20 Hz voice meter
  // changes. QML repeaters treat a replacement JavaScript array as a new
  // model, even when every task inside it has the same content.
  property var voicePreview: snapshot.voice_preview || ({ state: "idle", voice: "", error: "" })
  property var voice: snapshot.voice
  property var settings: snapshot.settings
  property var tasks: snapshot.tasks
  property var visibleTasks: snapshot.tasks
  property var session: snapshot.session
  property var readiness: snapshot.readiness
  // A monotonically sequenced request lets the daemon bring the matching task
  // into view without reopening the panel for every status snapshot.
  property var taskViewRequest: snapshot.task_view_request || null
  property string transportError: ""
  property bool connectionLost: false
  property var lastResponse: ({})
  property bool watching: watchProcess.running
  property bool watchingRequested: false
  property bool transportReady: false
  property var pendingRequests: []
  signal responseReceived(var response)

  function setFixture(next) {
    stop()
    fixtureMode = true
    applySnapshot(next)
    transportError = ""
    connectionLost = false
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
    voicePreview = reuseUnchanged(voicePreview, value.voice_preview || ({ state: "idle", voice: "", error: "" }))
    var nextVoice = reuseUnchanged(voice, value.voice)
    var nextSettings = reuseUnchanged(settings, value.settings)
    var nextTasks = reconcileTasks(tasks, Array.isArray(value.tasks) ? value.tasks : [])
    var nextSession = reuseUnchanged(session, value.session)
    var nextReadiness = reuseUnchanged(readiness, value.readiness)
    var nextTaskViewRequest = reuseUnchanged(taskViewRequest, value.task_view_request || null)
    if (voice !== nextVoice) voice = nextVoice
    if (settings !== nextSettings) settings = nextSettings
    if (tasks !== nextTasks) {
      tasks = nextTasks
      visibleTasks = visibleTaskList(nextTasks)
    }
    if (session !== nextSession) session = nextSession
    if (readiness !== nextReadiness) readiness = nextReadiness
    if (taskViewRequest !== nextTaskViewRequest) taskViewRequest = nextTaskViewRequest
    snapshot = {
      schemaVersion: value.schemaVersion,
      voice: voice,
      settings: settings,
      tasks: tasks,
      session: session,
      readiness: readiness,
      voice_preview: voicePreview,
      task_view_request: taskViewRequest
    }
  }

  function start() {
    if (fixtureMode) return
    watchingRequested = true
    if (!watchProcess.running) watchProcess.running = true
  }

  function stop() {
    watchingRequested = false
    transportReady = false
    pendingRequests = []
    reconnectTimer.stop()
    if (watchProcess.running) watchProcess.signal(15)
  }

  function request(value) {
    if (fixtureMode) { fixtureRequests = fixtureRequests.concat([value]); return }
    if (transportReady) {
      watchProcess.write(JSON.stringify(value) + "\n")
    } else {
      if (pendingRequests.length >= 32) { transportError = "Wait for Voice to reconnect before trying again."; return }
      pendingRequests = pendingRequests.concat([value])
      start()
    }
  }

  function flushRequests() {
    transportReady = true
    watchProcess.write(JSON.stringify({ action: "status" }) + "\n")
    var requests = pendingRequests
    pendingRequests = []
    for (var index = 0; index < requests.length; index++) watchProcess.write(JSON.stringify(requests[index]) + "\n")
  }

  function applyLine(line) {
    try {
      var value = JSON.parse(String(line || ""))
      if (value && value.schemaVersion === 1 && value.voice && value.settings) {
        applySnapshot(value)
        transportError = ""
        connectionLost = false
      } else if (value && typeof value.ok === "boolean") {
        lastResponse = value
        if (value.ok === false && value.error)
          transportError = String(value.error.message || "Voice control needs attention.")
        responseReceived(value)
      }
    } catch (error) {
      transportError = "Voice control returned an unreadable response."
      connectionLost = true
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
    onStarted: { reconnectTimer.stop(); root.flushRequests() }
    onExited: function(exitCode) {
      root.transportReady = false
      root.pendingRequests = [] // Never replay audio activation after a failed controller start.
      if (!root.fixtureMode && root.watchingRequested) {
        root.transportError = "Voice is reconnecting."
        root.connectionLost = true
        reconnectTimer.restart()
      }
    }
    stdout: SplitParser { onRead: function(line) { root.applyLine(line) } }
    stderr: SplitParser { onRead: function(line) { if (String(line).trim() !== "") root.transportError = "Voice control needs attention." } }
  }
}
