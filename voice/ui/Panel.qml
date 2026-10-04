import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.Commons

Item {
  id: root
  // Live shell roles preserve theme and user surface overrides on every update.
  readonly property color surfaceColor: Qt.rgba(Color.popups.background.r, Color.popups.background.g, Color.popups.background.b, 1)
  readonly property color textColor: readableColor(Color.popups.text, controlColor)
  readonly property color secondaryTextColor: readableColor(mixColor(textColor, surfaceColor, 0.72), controlColor)
  readonly property color controlColor: mixColor(Color.popups.text, surfaceColor, 0.07)
  readonly property color popupBorderColor: Color.popups.border
  readonly property color borderColor: mixColor(textColor, surfaceColor, 0.4)
  readonly property color accentTextColor: readableColor(Color.accent, controlColor)
  readonly property color alertTextColor: readableColor(Color.urgent, controlColor)
  readonly property color selectionTextColor: contrastingText(Color.accent)

  function mixColor(first, second, amount) {
    return Qt.rgba(first.r * amount + second.r * (1 - amount), first.g * amount + second.g * (1 - amount), first.b * amount + second.b * (1 - amount), 1)
  }
  function luminance(color) {
    function linear(value) { return value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4) }
    return 0.2126 * linear(color.r) + 0.7152 * linear(color.g) + 0.0722 * linear(color.b)
  }
  function contrastRatio(first, second) {
    var firstLight = luminance(first)
    var secondLight = luminance(second)
    return (Math.max(firstLight, secondLight) + 0.05) / (Math.min(firstLight, secondLight) + 0.05)
  }
  function contrastingText(background) {
    var black = Qt.rgba(0, 0, 0, 1)
    var white = Qt.rgba(1, 1, 1, 1)
    return contrastRatio(black, background) >= contrastRatio(white, background) ? black : white
  }
  function readableColor(color, background) {
    if (contrastRatio(color, background) >= 4.5) return color
    var target = contrastingText(background)
    for (var step = 1; step <= 20; step++) {
      var candidate = mixColor(target, color, step / 20)
      if (contrastRatio(candidate, background) >= 4.5) return candidate
    }
    return target
  }
  property var omarchyPath: null
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null
  property bool closingFromHost: false
  property bool nativePreviewFixtureMode: false
  property string page: "type"
  property bool settingsOpen: false
  readonly property string defaultGeminiPrompt: "You are Maslow's concise voice assistant. Answer conversation directly."
  property string draft: ""
  property string selectedProject: ""
  property string explicitContext: ""
  property string feedback: ""
  property string credentialName: "openai"
  property string credentialValue: ""
  property bool livekitSetupSaving: false
  property bool livekitSetupSucceeded: false
  property string livekitSetupStatus: ""
  property bool geminiLiveSetupSaving: false
  property bool geminiLiveSetupSucceeded: false
  property string geminiLiveSetupStatus: ""
  property bool advancedTaskSettingsOpen: false
  property bool advancedRequestOptionsOpen: false
  property bool projectRepairOpen: false
  property bool captionsOpen: false
  property bool advancedVoiceSettingsOpen: false
  property bool orbLongPress: false
  property bool voiceStartPending: false
  property string handledTaskErrorSignature: ""
  property string setupFocusMessage: ""
  property bool focusedOrb: false
  property bool uiTestInstrumentation: false
  property int taskDelegateCreations: 0
  property int transcriptDelegateCreations: 0
  property string selectedTaskId: ""
  property int handledTaskViewSequence: -1
  property int taskInputFocusRequest: 0
  property int taskInputFocusGeneration: 0
  property string taskInputFocusTaskId: ""
  property string focusedTaskInputId: ""
  property string pendingTaskInputRestoreId: ""
  property string focusedTaskActionTaskId: ""
  property string focusedTaskActionName: ""
  property string pendingTaskActionRestoreTaskId: ""
  property string pendingTaskActionRestoreName: ""
  property int taskActionFocusRequest: 0
  property var taskInstructionDrafts: ({})
  property var taskInstructionSelections: ({})
  readonly property bool messageInputFocused: textDraft.activeFocus
  property alias voiceController: controller

  readonly property var lockService: shell && typeof shell.serviceFor === "function" ? shell.serviceFor("omarchy.lock") : null
  readonly property bool sessionLocked: lockService ? lockService.locked === true : false
  onSessionLockedChanged: if (sessionLocked) { close(); send("end_voice") }

  readonly property var voicePreview: controller.voicePreview || ({})
  readonly property bool previewBusy: ["connecting", "playing"].indexOf(String(voicePreview.state || "")) >= 0
  readonly property var voice: controller.voice || ({})
  readonly property var taskError: voice.task_error || ({})
  readonly property var settings: controller.settings || ({})
  readonly property var readiness: controller.readiness || ({})
  readonly property var transcript: (controller.session || {}).transcript || []
  readonly property var tasks: controller.visibleTasks || []
  readonly property var taskViewRequest: controller.taskViewRequest || null
  readonly property var displayedTasks: selectedTask ? [selectedTask].concat(tasks.filter(function(task) { return String(task.id) !== selectedTaskId })) : tasks
  readonly property var selectedTask: tasks.find(function(task) { return String(task.id || "") === selectedTaskId }) || null
  readonly property bool reducedMotion: settings.reduced_motion === true
  readonly property bool fixedPosition: settings.fixed_position === true
  readonly property bool automaticWorkspaces: String(settings.mode || "") === "gemini_live"
  readonly property bool offlineMode: String(settings.mode || "") === "offline"
  readonly property bool conversationReady: root.conversationReadiness().ready === true
  readonly property bool disabled: voice.enabled !== true && !conversationReady
  // Agents flick between listening, thinking and speaking within a turn.
  // The orb and status text show a conversation state only once it has held
  // for a moment; every other state, such as connecting or an error, shows at once.
  readonly property var settlingStates: ["listening", "thinking", "speaking", "talking"]
  property string settledState: String(voice.state || "idle")
  readonly property string liveState: String(voice.state || "idle")
  onLiveStateChanged: {
    if (settlingStates.indexOf(liveState) >= 0 && settlingStates.indexOf(settledState) >= 0) {
      stateSettle.restart()
    } else {
      stateSettle.stop()
      settledState = liveState
    }
  }
  Timer { id: stateSettle; interval: 250; onTriggered: root.settledState = root.liveState }
  readonly property string orbState: voice.error || controller.connectionLost ? "error" : voice.paused === true ? "paused" : (settledState === "listening" && voice.microphone !== true ? "muted" : settledState)
  property bool controllerOpen: false
  readonly property int heldDiameter: conversation ? 88 : 56
  property bool localOrbPositionActive: false
  property real localOrbPositionX: 1
  property real localOrbPositionY: 1
  readonly property var configuredOrbPosition: settings.orb_position && isFinite(Number(settings.orb_position.x)) && isFinite(Number(settings.orb_position.y)) ? settings.orb_position : null
  readonly property var effectiveOrbPosition: localOrbPositionActive ? ({ x: localOrbPositionX, y: localOrbPositionY }) : configuredOrbPosition
  readonly property bool orbManuallyPositioned: effectiveOrbPosition !== null
  readonly property bool conversation: voice.paused === true || ["connecting", "thinking", "listening", "speaking", "talking", "conversation", "paused"].indexOf(String(voice.state || "")) >= 0
  readonly property bool supportsPause: ["gemini_live", "livekit", "openai"].indexOf(String(settings.mode || "")) >= 0
  readonly property var taskBadge: badgeForTasks(tasks)
  property int completionSequence: 0
  property var previousTaskStates: ({})
  readonly property bool working: tasks.some(function(task) {
    return ["queued", "submitting", "accepted", "running", "waiting_input", "awaiting_approval", "stopping"].indexOf(String(task.state || "")) >= 0
  })

  onTasksChanged: {
    var nextStates = {}
    var completed = false
    for (var taskIndex = 0; taskIndex < tasks.length; taskIndex++) {
      var task = tasks[taskIndex]
      var previous = previousTaskStates[String(task.id)]
      if (task.state === "completed" && previous !== undefined && previous !== "completed") completed = true
      nextStates[String(task.id)] = task.state
    }
    previousTaskStates = nextStates
    if (completed) completionSequence += 1
    var restoreTaskId = focusedTaskInputId
    var restoreActionTaskId = focusedTaskActionTaskId
    var restoreActionName = focusedTaskActionName
    if (selectedTaskId !== "" && !selectedTask) selectedTaskId = ""
    if (selectedTaskId === "" && tasks.length > 0) selectedTaskId = String(tasks[0].id || "")
    if (restoreActionTaskId !== "" && restoreActionTaskId === selectedTaskId)
      restoreTaskActionFocusAfterRefresh(restoreActionTaskId, restoreActionName)
    else if (restoreTaskId !== "" && restoreTaskId === selectedTaskId)
      restoreTaskInstructionFocusAfterRefresh(restoreTaskId)
  }
  onTaskViewRequestChanged: {
    var request = taskViewRequest || ({})
    var sequence = Number(request.sequence)
    var taskId = String(request.task_id || "")
    if (taskId === "" || !isFinite(sequence) || sequence <= handledTaskViewSequence) return
    handledTaskViewSequence = sequence
    selectedTaskId = taskId
    page = "tasks"
    controllerOpen = true
    Qt.callLater(function() { focusSelectedTaskInstruction() })
  }

  onTaskErrorChanged: {
    if (shouldHandleTaskError(taskError) && taskError.code === "PROJECT_REQUIRED") {
      feedback = String(taskError.message || "This work needs an existing project folder. Add one in Advanced request options.")
    }
  }

  function shouldHandleTaskError(error) {
    var signature = String((error || {}).code || "") + "\n" + String((error || {}).message || "")
    if (signature === "\n") {
      handledTaskErrorSignature = ""
      return false
    }
    if (signature === handledTaskErrorSignature) return false
    handledTaskErrorSignature = signature
    return true
  }

  function conversationReadiness() {
    return readiness.conversation || ({ ready: readiness.ready === true, checks: readiness.checks || [] })
  }
  function taskReadiness() {
    return readiness.tasks || ({ ready: readiness.ready === true, checks: readiness.checks || [] })
  }
  function openSettings(message) {
    setupFocusMessage = String(message || "")
    advancedVoiceSettingsOpen = message === "Connect Voice"
    page = "settings"
    settingsOpen = true
    controllerOpen = true
    controller.start()
    Qt.callLater(function() { controlsFocus.forceActiveFocus() })
  }
  function fixtureGeometry() {
    if (!uiTestInstrumentation) return ({})
    return { width: panelWindow.width, height: panelWindow.height,
      card: { x: card.x, y: card.y, width: card.width, height: card.height },
      orb: { x: orbButton.x, y: orbButton.y, width: orbButton.width, height: orbButton.height },
      status: { x: statusButton.x, y: statusButton.y, width: statusButton.width, height: statusButton.height },
      badge: { x: taskBadgeButton.x, y: taskBadgeButton.y, width: taskBadgeButton.width, height: taskBadgeButton.height, visible: taskBadgeButton.visible } }
  }
  function openDetails() {
    open(JSON.stringify({ page: "type" }))
  }
  function startFromOrb() {
    if (!conversationReady && !conversation && !voice.error && !controller.connectionLost) {
      feedback = "Connect Voice to start a conversation."
      return
    }
    if (conversation && voice.enabled !== true && voice.state !== "connecting") {
      requestVoiceStart()
    } else if (supportsPause) {
      send("toggle_voice", { extended: voice.extended === true, project: selectedProject, context: explicitContext })
    } else if (conversation) {
      send("end_voice")
    } else requestVoiceStart()
  }
  function badgeForTasks(items) {
    var ranks = { awaiting_approval: 0, waiting_input: 1, failed: 2, interrupted: 2, cancelled: 2, completed: 3, proposed: 4, queued: 4, submitting: 4, accepted: 4, running: 4, stopping: 4 }
    var labels = { awaiting_approval: "! Review approval", waiting_input: "? Input needed", failed: "! Work failed", interrupted: "! Work interrupted", cancelled: "■ Work stopped", completed: "✓ Result ready", proposed: "▷ Review task" }
    var chosen = null
    var rank = 99
    for (var index = 0; index < items.length; index++) {
      var task = items[index]
      var state = needsApproval(task) ? "awaiting_approval" : task.state
      var nextRank = ranks[state]
      if (nextRank !== undefined && nextRank < rank) {
        rank = nextRank
        chosen = { id: String(task.id), state: state, text: labels[state] || "⋯ Working", rank: rank }
      }
    }
    return chosen
  }
  function openBadgeTask() {
    if (!taskBadge) return
    selectedTaskId = taskBadge.id
    taskAction({ id: taskBadge.id }, "select")
    open(JSON.stringify({ page: "tasks" }))
    Qt.callLater(function() { focusSelectedTaskInstruction() })
  }
  function requestVoiceStart() {
    voiceStartPending = true
    send("start_voice", { project: selectedProject, context: explicitContext })
  }
  function openProjectRepair() {
    if (automaticWorkspaces) {
      page = "settings"
      settingsOpen = true
      advancedVoiceSettingsOpen = true
      advancedRequestOptionsOpen = true
    } else {
      page = "type"
      settingsOpen = false
      projectRepairOpen = true
    }
    controllerOpen = true
    Qt.callLater(function() {
      if (automaticWorkspaces) projectOverrideField.forceActiveFocus()
      else projectRepairField.forceActiveFocus()
    })
  }
  function boundedOrbCoordinate(value) {
    return Math.max(0, Math.min(1, Number(value)))
  }
  function orbPixel(normalized, extent, size) {
    var margin = 16
    var available = Math.max(0, extent - size - margin * 2)
    return margin + boundedOrbCoordinate(normalized) * available
  }
  function orbNormalized(pixel, extent, size) {
    var margin = 16
    var available = Math.max(0, extent - size - margin * 2)
    return available > 0 ? boundedOrbCoordinate((pixel - margin) / available) : 0.5
  }
  function setOrbPixelPosition(x, y) {
    localOrbPositionActive = true
    localOrbPositionX = orbNormalized(x, panelWindow.width, orbButton.width)
    localOrbPositionY = orbNormalized(y, panelWindow.height, orbButton.height)
  }
  function persistOrbPosition() {
    var changes = { orb_position: { x: localOrbPositionX, y: localOrbPositionY } }
    if (fixedPosition) changes.fixed_position = false
    send("configure", { settings: changes })
  }
  function clearOrbPosition() {
    localOrbPositionActive = false
    configure("orb_position", null)
  }
  function setFixedPosition(value) {
    if (value) {
      localOrbPositionActive = false
      send("configure", { settings: { fixed_position: true, orb_position: null } })
    } else {
      configure("fixed_position", false)
    }
  }
  function attachedPanelY(itemHeight) {
    var margin = 16
    var gap = 12
    var above = orbButton.y - itemHeight - gap
    if (above >= margin) return above
    return Math.max(margin, Math.min(panelWindow.height - itemHeight - margin, orbButton.y + orbButton.height + gap))
  }

  function stateText() {
    if (voice.error || controller.connectionLost) return "Connection lost · click to retry"
    if (voice.paused === true) return "Paused · click to resume"
    if (voice.action_caption) return voice.action_caption
    if (disabled) return "Connect Voice"
    if (voice.state === "connecting") return "Connecting · click to cancel"
    if (settledState === "thinking") return "Thinking"
    if (settledState === "speaking" || settledState === "talking") return "Speaking"
    if (settledState === "listening") return voice.extended === true ? "Listening · extended" : "Listening"
    return "Ready · click to talk"
  }
  function send(action, extra) {
    var request = { action: action }
    if (extra) for (var key in extra) request[key] = extra[key]
    controller.request(request)
  }
  function submitText() {
    var text = draft.trim()
    if (text === "") return
    send("submit_text", { text: text, project: selectedProject, context: explicitContext })
    draft = ""
  }
  function taskAction(task, operation, text) {
    var request = operation === "start"
      ? { task_id: String(task.id), operation: operation, text: String(text || "") }
      : { id: String(task.id), operation: operation, text: String(text || "") }
    if (operation === "approve" || operation === "deny") {
      var approval = task.approval || ({})
      request.approval_id = String(approval.request_id || task.approval_request_id || "")
      if (request.approval_id === "") {
        feedback = "This approval request is stale. Refresh the task before deciding."
        return
      }
    }
    if (operation === "export") {
      var review = task.export_review || ({})
      request.review_id = String(review.digest || "")
      request.paths = (review.changes || []).map(function(change) { return change.path })
    }
    send("task_action", request)
  }
  function selectTask(task) {
    selectedTaskId = String((task || {}).id || "")
    taskAction(task, "select")
    Qt.callLater(function() { focusSelectedTaskInstruction() })
  }
  function focusSelectedTaskInstruction() {
    if (selectedTaskId === "") return
    taskInputFocusTaskId = selectedTaskId
    taskInputFocusGeneration += 1
    taskInputFocusRequest += 1
  }
  function taskInstructionDraft(taskId) {
    var id = String(taskId || "")
    return id === "" ? "" : String(taskInstructionDrafts[id] || "")
  }
  function setTaskInstructionDraft(taskId, text) {
    var id = String(taskId || "")
    if (id === "") return
    var value = String(text || "")
    if (taskInstructionDraft(id) === value) return
    var next = {}
    for (var key in taskInstructionDrafts) next[key] = taskInstructionDrafts[key]
    if (value === "") delete next[id]
    else next[id] = value
    taskInstructionDrafts = next
  }
  function taskInstructionSelection(taskId) {
    var id = String(taskId || "")
    return taskInstructionSelections[id] || ({ cursorPosition: 0, selectionStart: 0, selectionEnd: 0 })
  }
  function setTaskInstructionSelection(taskId, cursorPosition, selectionStart, selectionEnd) {
    var id = String(taskId || "")
    if (id === "") return
    var nextValue = { cursorPosition: Number(cursorPosition), selectionStart: Number(selectionStart), selectionEnd: Number(selectionEnd) }
    var previous = taskInstructionSelection(id)
    if (previous.cursorPosition === nextValue.cursorPosition && previous.selectionStart === nextValue.selectionStart && previous.selectionEnd === nextValue.selectionEnd) return
    var next = {}
    for (var key in taskInstructionSelections) next[key] = taskInstructionSelections[key]
    next[id] = nextValue
    taskInstructionSelections = next
  }
  function restoreTaskInstructionSelection(taskId, input) {
    var selection = taskInstructionSelection(taskId)
    var length = String(input.text || "").length
    var start = Math.max(0, Math.min(length, Number(selection.selectionStart)))
    var end = Math.max(0, Math.min(length, Number(selection.selectionEnd)))
    if (start !== end) {
      if (Number(selection.cursorPosition) === start) input.select(end, start)
      else input.select(start, end)
    }
    else input.cursorPosition = Math.max(0, Math.min(length, Number(selection.cursorPosition)))
  }
  function clearPendingTaskInputRestore() {
    pendingTaskInputRestoreId = ""
    taskInputFocusGeneration += 1
  }
  function clearTaskActionFocus() {
    focusedTaskActionTaskId = ""
    focusedTaskActionName = ""
    pendingTaskActionRestoreTaskId = ""
    pendingTaskActionRestoreName = ""
  }
  function setTaskActionFocus(taskId, action) {
    focusedTaskActionTaskId = String(taskId || "")
    focusedTaskActionName = String(action || "")
    pendingTaskActionRestoreTaskId = ""
    pendingTaskActionRestoreName = ""
    clearPendingTaskInputRestore()
  }
  function restoreTaskInstructionFocusAfterRefresh(taskId) {
    var id = String(taskId || "")
    if (id === "") return
    pendingTaskInputRestoreId = id
    Qt.callLater(function() {
      if (pendingTaskInputRestoreId !== id) return
      pendingTaskInputRestoreId = ""
      if (!controllerOpen || page !== "tasks" || selectedTaskId !== id) return
      taskInputFocusTaskId = id
      taskInputFocusGeneration += 1
      taskInputFocusRequest += 1
    })
  }
  function restoreTaskActionFocusAfterRefresh(taskId, action) {
    var id = String(taskId || "")
    var name = String(action || "")
    if (id === "" || name === "") return
    pendingTaskActionRestoreTaskId = id
    pendingTaskActionRestoreName = name
    Qt.callLater(function() {
      if (pendingTaskActionRestoreTaskId !== id || pendingTaskActionRestoreName !== name) return
      pendingTaskActionRestoreTaskId = ""
      pendingTaskActionRestoreName = ""
      if (!controllerOpen || page !== "tasks" || selectedTaskId !== id) return
      taskActionFocusRequest += 1
    })
  }
  function taskCapability(task, capability) {
    var capabilities = (task || {}).capabilities
    if (capabilities && Object.prototype.hasOwnProperty.call(capabilities, capability))
      return capabilities[capability] === true
    // Codex is intentionally opt-in for its new session controls. Existing
    // Hermes and Claude records retain their established controls until their
    // adapters publish a capability map.
    return String((task || {}).selected_agent || "") !== "codex"
  }
  function taskHasCodexSetupError(task) {
    var code = String((((task || {}).error || {}).code) || "")
    return String((task || {}).selected_agent || "") === "codex" && ["CODEX_MISSING", "CODEX_UPDATE_REQUIRED", "CODEX_AUTH_REQUIRED", "AGENT_UNAVAILABLE"].indexOf(code) >= 0
  }
  function artifactVerificationText(artifact) {
    var verification = (artifact || {}).verification
    if (verification === "exists") return "File exists; behavior not verified"
    if (verification === "missing") return "File not found"
    if (verification === true) return "Maslow verified"
    if (verification === false) return "Verification pending"
    if (typeof verification === "string" && verification !== "") return verification
    return (artifact || {}).exists === true ? "File exists; verification pending" : "Unavailable"
  }
  function taskSessionIdentity(task) {
    var current = task || ({})
    var thread = current.thread_id || current.threadId || ""
    var turn = current.turn_id || current.turnId || ""
    var children = current.children || []
    for (var index = children.length - 1; index >= 0 && (!thread || !turn); index--) {
      var child = children[index] || ({})
      if (!thread) thread = child.thread_id || child.threadId || ""
      if (!turn) turn = child.turn_id || child.turnId || ""
    }
    var identity = []
    if (thread) identity.push("Thread " + String(thread))
    if (turn) identity.push("Turn " + String(turn))
    return identity.join(" · ")
  }
  function taskSummaryText(task) {
    var current = task || ({})
    var error = String((current.error || ({})).message || "")
    if (error !== "") return error
    if (String(current.state || "") === "completed")
      return String(current.result || "") !== "" ? "Agent finished. Review the agent report below." : "Agent finished. Review the task details below."
    return String(current.summary || "")
  }
  function needsApproval(task) {
    var approval = task ? task.approval : null
    return !!(approval === true || approval === "required" || (approval && typeof approval === "object" && String(approval.request_id || "") !== ""))
  }
  function approvalSummary(task) {
    var approval = task ? task.approval || ({}) : ({})
    var details = []
    if (String(approval.message || "") !== "") details.push(String(approval.message))
    else if (String(approval.detail || "") !== "") details.push(String(approval.detail))
    else if (String(approval.action || "") !== "") details.push(String(approval.action))
    if (String(approval.action || "") !== "" && String(approval.action) !== String(approval.message || "") && String(approval.action) !== String(approval.detail || "")) details.push("Action: " + String(approval.action))
    if (String(approval.destination || "") !== "") details.push("Destination: " + String(approval.destination))
    if (String(approval.tool_name || "") !== "") details.push("Tool: " + String(approval.tool_name))
    return details.length > 0 ? details.join("\n") : "Review this request before continuing."
  }
  function configure(key, value) {
    var next = {}
    next[key] = value
    send("configure", { settings: next })
  }
  function submitCredential() {
    if (credentialName === "" || credentialValue === "") return
    send("credential", { name: credentialName, value: credentialValue })
    credentialValue = ""
    feedback = "Credential sent to the local controller."
  }
  function submitLiveKitSetup(url, apiKey, apiSecret) {
    livekitSetupSucceeded = false
    if (url.trim() === "") {
      livekitSetupStatus = "Enter your LiveKit project URL before saving."
      return
    }
    livekitSetupSaving = true
    livekitSetupSucceeded = false
    livekitSetupStatus = "Saving LiveKit setup…"
    send("configure_livekit", { url: url.trim(), api_key: apiKey, api_secret: apiSecret })
  }
  function submitGeminiLiveSetup(url, apiKey, apiSecret, googleApiKey) {
    geminiLiveSetupSucceeded = false
    geminiLiveSetupSaving = true
    geminiLiveSetupStatus = "Saving Maslow Voice setup…"
    send("configure_gemini_live", { url: url.trim(), api_key: apiKey, api_secret: apiSecret, google_api_key: googleApiKey })
  }
  function microphoneText() {
    if (voice.paused === true) return "Paused — microphone and speaker off"
    if (voice.state === "connecting") return "Connecting — requesting microphone access"
    if (voice.state === "listening") return voice.microphone === true ? (voice.extended === true ? "Extended conversation — microphone on; no inactivity timeout" : "Listening — microphone on") : "Listening — microphone off"
    return voice.microphone === true ? "Microphone on" : "Microphone off"
  }
  function handleControlResponse(response) {
    if (voiceStartPending && response.ok === false) {
      voiceStartPending = false
      feedback = String((response.error || {}).message || "Connection lost · click to retry")
      return
    }
    if (voiceStartPending && response.ok === true) voiceStartPending = false
    if (livekitSetupSaving && response.ok === true && response.livekit_saved === true) {
      livekitSetupSaving = false
      livekitSetupSucceeded = true
      livekitApiKeyField.text = ""
      livekitApiSecretField.text = ""
      livekitSetupStatus = "LiveKit setup saved on this computer. Start talking to request microphone access."
      return
    }
    if (livekitSetupSaving && response.ok === false) {
      livekitSetupSaving = false
      livekitSetupSucceeded = false
      livekitSetupStatus = String((response.error || {}).message || "LiveKit setup could not be saved. Check the fields and try again.")
    }
    if (geminiLiveSetupSaving && response.ok === true && response.gemini_live_saved === true) {
      geminiLiveSetupSaving = false
      geminiLiveSetupSucceeded = true
      geminiLiveGoogleApiKeyField.text = ""
      geminiLiveApiKeyField.text = ""
      geminiLiveApiSecretField.text = ""
      geminiLiveSetupStatus = "Maslow Voice setup saved on this computer. Start talking to request microphone access."
      return
    }
    if (geminiLiveSetupSaving && response.ok === false) {
      geminiLiveSetupSaving = false
      geminiLiveSetupSucceeded = false
      geminiLiveSetupStatus = String((response.error || {}).message || "Maslow Voice setup could not be saved. Check the fields and try again.")
    }
  }
  function handleTransportError(message) {
    var safeMessage = String(message || "Voice control needs attention.")
    if (voiceStartPending) {
      voiceStartPending = false
      feedback = safeMessage
    }
    if (livekitSetupSaving) {
      livekitSetupSaving = false
      livekitSetupSucceeded = false
      livekitSetupStatus = safeMessage
    }
    if (geminiLiveSetupSaving) {
      geminiLiveSetupSaving = false
      geminiLiveSetupSucceeded = false
      geminiLiveSetupStatus = safeMessage
    }
  }
  function open(payloadJson) {
    var payload = {}
    try { payload = JSON.parse(String(payloadJson || "{}")) } catch (error) {}
    if (["talk", "type", "tasks", "settings"].indexOf(String(payload.page || "")) >= 0)
      page = payload.page === "talk" ? "type" : String(payload.page)
    settingsOpen = page === "settings"
    closingFromHost = false
    controllerOpen = true
    controller.start()
    Qt.callLater(function() {
      if (root.page === "type") textDraft.forceActiveFocus()
      else if (root.page === "settings") controlsFocus.forceActiveFocus()
      else controlsFocus.forceActiveFocus()
    })
  }
  function close() {
    closingFromHost = true
    controllerOpen = false
    Qt.callLater(function() { if (!root.sessionLocked) orbButton.forceActiveFocus(Qt.OtherFocusReason) })
  }

  VoiceController {
    id: controller
    fixtureMode: root.nativePreviewFixtureMode
    onResponseReceived: function(response) { root.handleControlResponse(response) }
    onTransportErrorChanged: if (transportError !== "") root.handleTransportError(transportError)
  }
  Component.onCompleted: Qt.callLater(function() { controller.start() })

  component VoiceField: TextField {
    implicitHeight: 44
    color: root.textColor
    placeholderTextColor: root.secondaryTextColor
    selectionColor: Color.accent
    selectedTextColor: root.selectionTextColor
    font.family: "Manrope"
    font.pixelSize: 14
    leftPadding: 12
    onActiveFocusChanged: if (activeFocus) { root.clearPendingTaskInputRestore(); root.clearTaskActionFocus() }
    background: Rectangle { radius: 8; color: root.controlColor; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? root.accentTextColor : root.borderColor }
  }
  component VoiceArea: TextArea {
    Keys.priority: Keys.BeforeItem
    Keys.onTabPressed: function(event) { nextItemInFocusChain(true).forceActiveFocus(Qt.TabFocusReason); event.accepted = true }
    Keys.onBacktabPressed: function(event) { nextItemInFocusChain(false).forceActiveFocus(Qt.BacktabFocusReason); event.accepted = true }
    color: root.textColor
    placeholderTextColor: root.secondaryTextColor
    selectionColor: Color.accent
    selectedTextColor: root.selectionTextColor
    font.family: "Manrope"
    font.pixelSize: 14
    padding: 12
    onActiveFocusChanged: if (activeFocus) { root.clearPendingTaskInputRestore(); root.clearTaskActionFocus() }
    background: Rectangle { radius: 8; color: root.controlColor; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? root.accentTextColor : root.borderColor }
  }
  component VoiceSelect: ComboBox {
    id: select
    implicitHeight: 44
    Layout.fillWidth: true
    font.family: "Manrope"
    font.pixelSize: 14
    leftPadding: 12
    rightPadding: 36
    onActiveFocusChanged: if (activeFocus) { root.clearPendingTaskInputRestore(); root.clearTaskActionFocus() }
    palette.text: root.textColor
    palette.buttonText: root.textColor
    palette.highlightedText: root.selectionTextColor
    palette.highlight: Color.accent
    background: Rectangle {
      radius: 8
      color: root.controlColor
      border.width: select.activeFocus ? 2 : 1
      border.color: select.activeFocus ? root.accentTextColor : root.borderColor
    }
    contentItem: Text {
      text: select.displayText
      color: select.enabled ? root.textColor : root.secondaryTextColor
      font: select.font
      elide: Text.ElideRight
      verticalAlignment: Text.AlignVCenter
    }
    indicator: Text {
      x: select.width - width - 12
      y: (select.height - height) / 2
      text: "\u25BE"
      color: select.enabled ? root.textColor : root.secondaryTextColor
      font.pixelSize: 18
      Accessible.ignored: true
    }
    delegate: ItemDelegate {
      id: option
      required property int index
      width: select.popup.width - 12
      implicitHeight: 44
      text: select.textAt(index)
      highlighted: select.highlightedIndex === index
      contentItem: Text {
        text: option.text
        color: option.highlighted ? root.selectionTextColor : root.textColor
        font: select.font
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
      }
      background: Rectangle {
        radius: 6
        color: option.highlighted ? Color.accent : root.controlColor
        border.width: option.activeFocus ? 2 : 0
        border.color: root.textColor
      }
    }
    popup: Popup {
      width: select.width
      padding: 6
      implicitHeight: Math.min(contentItem.implicitHeight + 12, 264, card.height - 40)
      // Keep every option inside the controller's input region.
      y: select.mapToItem(card, 0, select.height).y + implicitHeight + 6 > card.height - 20 ? -implicitHeight - 6 : select.height + 6
      background: Rectangle { color: root.controlColor; radius: 8; border.color: root.accentTextColor; border.width: 1 }
      contentItem: ListView {
        clip: true
        implicitHeight: contentHeight
        model: select.popup.visible ? select.delegateModel : null
        currentIndex: select.highlightedIndex
        ScrollIndicator.vertical: ScrollIndicator {}
      }
    }
  }
  component VoiceCheck: CheckBox {
    palette.window: root.surfaceColor
    palette.base: root.controlColor
    palette.text: root.textColor
    palette.button: root.controlColor
    palette.buttonText: root.textColor
    palette.highlight: Color.accent
    palette.highlightedText: root.selectionTextColor
    implicitHeight: 44
    onActiveFocusChanged: if (activeFocus) { root.clearPendingTaskInputRestore(); root.clearTaskActionFocus() }
    contentItem: Text { text: parent.text; leftPadding: parent.indicator.width + parent.spacing; color: root.textColor; font.family: "Manrope"; verticalAlignment: Text.AlignVCenter }
    background: Rectangle { color: "transparent"; radius: 6; border.width: parent.activeFocus ? 2 : 0; border.color: root.accentTextColor }
  }

  component VoiceButton: Button {
    id: action
    readonly property color fillColor: down ? root.mixColor(Color.accent, root.surfaceColor, 0.8) : (hovered ? root.mixColor(Color.accent, root.textColor, 0.8) : Color.accent)
    focusPolicy: Qt.StrongFocus
    onActiveFocusChanged: if (activeFocus) { root.clearPendingTaskInputRestore(); root.clearTaskActionFocus() }
    implicitHeight: 44
    horizontalPadding: 14
    Accessible.role: Accessible.Button
    Accessible.name: text
    background: Rectangle {
      radius: 8
      opacity: parent.enabled ? 1 : 0.55
      color: action.fillColor
      border.color: parent.activeFocus ? root.alertTextColor : root.surfaceColor
      border.width: parent.activeFocus ? 3 : 1
    }
    contentItem: Text {
      text: parent.text
      color: root.contrastingText(action.fillColor)
      font.family: "Manrope"
      font.weight: Font.DemiBold
      font.pixelSize: 14
      horizontalAlignment: Text.AlignHCenter
      verticalAlignment: Text.AlignVCenter
    }
  }

  PanelWindow {
    id: panelWindow
    visible: !root.sessionLocked
    screen: Quickshell.screens.find(function(display) { return display.name === String(root.settings.display || "") }) || Quickshell.screens[0]
    anchors { top: true; bottom: true; left: true; right: true }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "maslow-voice"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: root.controllerOpen ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.OnDemand
    color: "transparent"
    mask: Region {
      item: orbButton
      Region { item: statusButton; intersection: Intersection.Combine }
      Region { item: taskBadgeButton.visible ? taskBadgeButton : null; intersection: Intersection.Combine }
      Region { item: root.controllerOpen ? card : null; intersection: Intersection.Combine }
    }

    Button {
      id: orbButton
      padding: 8
      width: root.heldDiameter + 16
      height: width
      x: root.orbManuallyPositioned ? root.orbPixel(root.effectiveOrbPosition.x, panelWindow.width, width) : parent.width - width - 20
      y: root.orbManuallyPositioned ? root.orbPixel(root.effectiveOrbPosition.y, panelWindow.height, height) : parent.height - height - 20
      focusPolicy: Qt.StrongFocus
      Accessible.name: "Maslow Voice, " + root.stateText()
      Accessible.description: "Drag to move the Voice Orb. Space or Enter starts, pauses or resumes. Right-click, hold, or Shift+F10 opens details."
      Keys.onPressed: function(event) {
        if (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier)) { root.openDetails(); event.accepted = true }
        else if (event.key === Qt.Key_Escape) { root.close(); event.accepted = true }
      }
      background: Item {}
      contentItem: VoiceOrb {
        width: orbButton.width - 16; height: width
        accentColor: Color.accent
        backgroundColor: Color.background
        voiceState: root.orbState
        audioLevel: root.voice.input_level || root.voice.level || 0
        playbackLevel: root.voice.playback_level || 0
        microphoneActive: root.voice.microphone === true && !controller.connectionLost
        interruptionSequence: root.voice.interruption_sequence || 0
        completionSequence: root.completionSequence
        disabled: root.disabled
        reducedMotion: root.reducedMotion
        interactive: orbPointer.containsMouse || orbPointer.pressed || orbButton.activeFocus
        gpuShaderAvailable: Quickshell.env("MASLOW_VOICE_GPU_SHADER") !== "0"
      }
      onClicked: root.startFromOrb()

      MouseArea {
        id: orbPointer
        anchors.fill: parent
        enabled: !root.controllerOpen && !root.sessionLocked
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        cursorShape: dragging ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        pressAndHoldInterval: 650
        property bool dragging: false
        property bool suppressClick: false
        property real pressSceneX: 0
        property real pressSceneY: 0
        property real startOrbX: 0
        property real startOrbY: 0
        property bool startLocalPositionActive: false
        property real startLocalPositionX: 0.5
        property real startLocalPositionY: 0.5
        readonly property real dragThreshold: 6

        onPressed: function(mouse) {
          var point = mapToItem(orbButton.parent, Qt.point(mouse.x, mouse.y))
          orbButton.forceActiveFocus(Qt.MouseFocusReason)
          dragging = false
          suppressClick = false
          root.orbLongPress = false
          pressSceneX = point.x
          pressSceneY = point.y
          startOrbX = orbButton.x
          startOrbY = orbButton.y
          startLocalPositionActive = root.localOrbPositionActive
          startLocalPositionX = root.localOrbPositionX
          startLocalPositionY = root.localOrbPositionY
        }
        onPositionChanged: function(mouse) {
          if (!(mouse.buttons & Qt.LeftButton)) return
          var point = mapToItem(orbButton.parent, Qt.point(mouse.x, mouse.y))
          var deltaX = point.x - pressSceneX
          var deltaY = point.y - pressSceneY
          if (!dragging && Math.abs(deltaX) + Math.abs(deltaY) < dragThreshold) return
          dragging = true
          root.orbLongPress = false
          root.setOrbPixelPosition(startOrbX + deltaX, startOrbY + deltaY)
        }
        onReleased: function(mouse) {
          if (!dragging) return
          dragging = false
          suppressClick = true
          root.persistOrbPosition()
          mouse.accepted = true
        }
        onPressAndHold: function(mouse) {
          if (dragging) return
          root.orbLongPress = true
          suppressClick = true
          root.openDetails()
          mouse.accepted = true
        }
        onCanceled: {
          dragging = false
          suppressClick = false
          root.localOrbPositionActive = startLocalPositionActive
          root.localOrbPositionX = startLocalPositionX
          root.localOrbPositionY = startLocalPositionY
        }
        onClicked: function(mouse) {
          if (suppressClick || root.orbLongPress) {
            suppressClick = false
            root.orbLongPress = false
            mouse.accepted = true
            return
          }
          if (mouse.button === Qt.RightButton) root.openDetails()
          else root.startFromOrb()
          mouse.accepted = true
        }
      }
    }

    readonly property bool labelsAbove: orbButton.y >= (taskBadgeButton.visible ? 68 : 34) + 16
    Button {
      id: statusButton
      text: (root.nativePreviewFixtureMode ? "UI preview · " : "") + root.stateText()
      width: Math.min(280, panelWindow.width - 32)
      height: 30
      x: Math.max(16, Math.min(panelWindow.width - width - 16, orbButton.x + orbButton.width / 2 - width / 2))
      y: panelWindow.labelsAbove ? orbButton.y - height - 4 : Math.min(panelWindow.height - height - 16, orbButton.y + orbButton.height + 4)
      focusPolicy: Qt.StrongFocus
      Accessible.name: text
      background: Rectangle { color: root.surfaceColor; radius: 12; border.width: parent.activeFocus ? 2 : 0; border.color: root.accentTextColor }
      contentItem: Text { text: parent.text; color: root.textColor; font.pixelSize: 12; elide: Text.ElideRight; leftPadding: 10; rightPadding: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
      onClicked: {
        if (!root.conversationReady && !root.conversation && !root.voice.error && !controller.connectionLost) root.openSettings("Connect Voice")
        else root.startFromOrb()
      }
    }
    Button {
      id: taskBadgeButton
      visible: root.taskBadge !== null
      text: root.taskBadge ? root.taskBadge.text : ""
      width: Math.min(180, panelWindow.width - 32)
      height: 30
      x: Math.max(16, Math.min(panelWindow.width - width - 16, orbButton.x + orbButton.width / 2 - width / 2))
      y: panelWindow.labelsAbove ? statusButton.y - height - 4 : Math.min(panelWindow.height - height - 16, statusButton.y + statusButton.height + 4)
      focusPolicy: Qt.StrongFocus
      Accessible.name: text + ". Open Work details"
      background: Rectangle { color: root.surfaceColor; radius: 12; border.width: 1; border.color: parent.activeFocus ? root.textColor : (root.taskBadge && root.taskBadge.rank < 3 ? root.alertTextColor : root.accentTextColor) }
      contentItem: Text { text: parent.text; color: root.textColor; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
      onClicked: root.openBadgeTask()
    }

    Rectangle {
      id: card
      visible: root.controllerOpen
      width: Math.min(600, panelWindow.width - 32)
      height: Math.min(720, panelWindow.height - 32)
      x: Math.max(16, Math.min(panelWindow.width - width - 16, orbButton.x + orbButton.width / 2 - width / 2))
      y: Math.max(16, Math.min(panelWindow.height - height - 16, root.attachedPanelY(height)))
      color: root.surfaceColor
      radius: 17
      border.color: root.popupBorderColor
      border.width: 1
      FocusScope {
        id: controlsFocus
        anchors.fill: parent
        focus: true
        Keys.onEscapePressed: root.close()
        Keys.onPressed: function(event) {
          if (event.key === Qt.Key_PageDown || event.key === Qt.Key_PageUp) {
            var viewport = root.page === "tasks" ? tasksScroll : (root.page === "settings" ? settingsScroll : typeScroll)
            var nextY = viewport.contentItem.contentY + (event.key === Qt.Key_PageDown ? 1 : -1) * viewport.availableHeight * 0.75
            viewport.contentItem.contentY = Math.max(0, Math.min(viewport.contentHeight - viewport.availableHeight, nextY))
            event.accepted = true
          }
        }
        ColumnLayout {
          anchors.fill: parent
          anchors.margins: 20
          spacing: 14
          RowLayout {
            Layout.fillWidth: true
            Text { text: root.nativePreviewFixtureMode ? "VOICE UI PREVIEW" : "MASLOW VOICE"; color: root.textColor; font.family: "Manrope"; font.weight: Font.Bold; font.pixelSize: 18; Accessible.role: Accessible.Heading; Accessible.name: "Maslow Voice" }
            Item { Layout.fillWidth: true }
            Text { text: root.stateText(); color: root.disabled ? root.secondaryTextColor : root.accentTextColor; font.family: "Manrope"; font.pixelSize: 14; Accessible.role: Accessible.StatusBar; Accessible.name: text }
            VoiceButton { text: "Close"; onClicked: root.close() }
          }
          RowLayout {
            Layout.fillWidth: true
            Repeater {
              model: [{ id: "type", label: "Conversation" }, { id: "tasks", label: "Work" }, { id: "settings", label: "Settings" }]
              delegate: VoiceButton {
                required property var modelData
                text: modelData.label
                Accessible.name: text + (root.page === modelData.id ? ", current section" : "")
                onClicked: {
                  root.page = modelData.id
                  root.settingsOpen = modelData.id === "settings"
                  if (modelData.id === "type") Qt.callLater(function() { textDraft.forceActiveFocus() })
                }
              }
            }
          }
          Rectangle { Layout.fillWidth: true; height: 1; color: root.borderColor }
          Text { visible: root.feedback !== "" || controller.transportError !== ""; text: controller.transportError || root.feedback; color: root.alertTextColor; Layout.fillWidth: true; wrapMode: Text.Wrap; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
          StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: ["type", "tasks", "settings"].indexOf(root.page)
            ScrollView {
              id: typeScroll
              clip: true
              ScrollBar.vertical.policy: ScrollBar.AlwaysOn
              ColumnLayout {
                width: typeScroll.availableWidth - 14
                spacing: 12
                Text { text: "Conversation"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 22; Accessible.role: Accessible.Heading }
                Text { text: root.microphoneText(); color: root.accentTextColor; Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.StatusBar; Accessible.name: text }
                Text { visible: root.voice.extended === true; text: "Extended conversation · no inactivity timeout · 30-minute maximum"; color: root.accentTextColor; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Flow {
                  Layout.fillWidth: true; spacing: 8
                  VoiceButton { id: talkAction; text: root.voice.state === "connecting" ? "Cancel connection" : root.voice.enabled === true ? (root.voice.paused === true ? "Resume" : root.supportsPause ? "Pause" : "End conversation") : "Start talking"; onClicked: root.startFromOrb() }
                  VoiceButton { text: "End conversation"; visible: root.conversation; onClicked: root.send("end_voice") }
                  VoiceCheck { text: "Captions"; checked: root.captionsOpen; onToggled: root.captionsOpen = checked }
                }
                Text { visible: root.captionsOpen && root.transcript.length > 0; text: root.transcript.length > 0 ? String(root.transcript[root.transcript.length - 1].text || "") : ""; color: root.accentTextColor; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Text { visible: String(root.taskError.message || "") !== ""; text: String(root.taskError.message || ""); color: root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
                VoiceArea { Layout.fillWidth: true; id: textDraft; placeholderText: root.automaticWorkspaces ? "Type a message" : "Describe the work to coordinate"; text: root.draft; onTextChanged: root.draft = text; Accessible.name: "Message"; implicitHeight: 110; wrapMode: TextEdit.Wrap }
                ColumnLayout {
                  visible: root.offlineMode || root.projectRepairOpen
                  Layout.fillWidth: true
                  spacing: 8
                  Text { text: root.offlineMode ? "Offline work needs an existing project folder before it can run." : "Choose the existing folder for this work."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  VoiceField { id: projectRepairField; Layout.fillWidth: true; placeholderText: "Project folder (required)"; text: root.selectedProject; onTextEdited: root.selectedProject = text; Accessible.name: "Project folder" }
                  VoiceArea { Layout.fillWidth: true; visible: root.offlineMode; placeholderText: "Context you choose to share (optional)"; text: root.explicitContext; onTextChanged: root.explicitContext = text; Accessible.name: "Explicit context"; implicitHeight: 76; wrapMode: TextEdit.Wrap }
                }
                VoiceButton { text: root.automaticWorkspaces ? "Send message" : "Send request"; enabled: root.draft.trim() !== ""; onClicked: root.submitText() }
                Repeater { model: root.transcript; delegate: Text { required property var modelData; Component.onCompleted: if (root.uiTestInstrumentation) root.transcriptDelegateCreations += 1; Layout.fillWidth: true; text: (modelData.role === "user" ? "You: " : "Maslow: ") + String(modelData.text || ""); color: root.textColor; font.family: "Manrope"; wrapMode: Text.WordWrap } }
              }
            }
            ScrollView {
              id: tasksScroll
              clip: true
              ScrollBar.vertical.policy: ScrollBar.AlwaysOn
              ColumnLayout {
                width: tasksScroll.availableWidth - 14
                spacing: 12
                Text { text: "Coordinated tasks"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 22; Accessible.role: Accessible.Heading }
                Text { visible: root.tasks.length === 0; text: "No tasks are being coordinated yet."; color: root.secondaryTextColor; font.family: "Manrope" }
                Repeater {
                  model: root.displayedTasks
                  delegate: Rectangle {
                    required property var modelData
                    Component.onCompleted: if (root.uiTestInstrumentation) root.taskDelegateCreations += 1
                    Layout.fillWidth: true
                    implicitHeight: taskColumn.implicitHeight + 20
                    radius: 8; color: root.controlColor; border.color: root.borderColor
                    ColumnLayout {
                      id: taskColumn; anchors.fill: parent; anchors.margins: 10; spacing: 7
                      property var task: modelData
                      readonly property bool selected: root.selectedTaskId === String(modelData.id || "")
                      property bool technicalDetailsOpen: false
                      property bool reportOpen: false
                      function focusInstructionIfRequested() {
                        if (!selected || root.taskInputFocusTaskId !== String(modelData.id || "")) return
                        var taskId = String(modelData.id || "")
                        var generation = root.taskInputFocusGeneration
                        root.taskInputFocusTaskId = ""
                        Qt.callLater(function() {
                          if (root.taskInputFocusGeneration === generation && root.focusedTaskActionTaskId === "" && root.controllerOpen && root.page === "tasks" && root.selectedTaskId === taskId) {
                            root.restoreTaskInstructionSelection(taskId, taskInstruction)
                            taskInstruction.forceActiveFocus()
                          }
                        })
                      }
                      function focusActionIfRequested() {
                        if (!selected || root.focusedTaskActionTaskId !== String(modelData.id || "")) return
                        var buttons = {
                          approve: approveButton, deny: denyButton, steer: steerButton, start: startButton,
                          cancel: cancelButton, continueTask: continueButton, openFolder: openFolderButton,
                          setup: setupButton, review: reviewButton, exportTask: exportButton, dismiss: dismissButton
                        }
                        var button = buttons[root.focusedTaskActionName]
                        var taskId = String(modelData.id || "")
                        var action = root.focusedTaskActionName
                        var request = root.taskActionFocusRequest
                        if (button && button.visible && button.enabled) Qt.callLater(function() {
                          if (root.taskActionFocusRequest === request && root.focusedTaskActionTaskId === taskId && root.focusedTaskActionName === action && button.visible && button.enabled)
                            button.forceActiveFocus()
                        })
                      }
                      onSelectedChanged: {
                        focusInstructionIfRequested()
                      }
                      Connections {
                        target: root
                        function onTaskInputFocusRequestChanged() {
                          taskColumn.focusInstructionIfRequested()
                        }
                        function onTaskActionFocusRequestChanged() {
                          taskColumn.focusActionIfRequested()
                        }
                      }
                      Text { text: String(modelData.title || "Task") + (taskColumn.selected ? " · selected" : ""); color: root.textColor; font.family: "Manrope"; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                      Text { text: String(modelData.state || "unknown").replace(/_/g, " ") + " · " + root.taskSummaryText(modelData); color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                      VoiceButton { visible: !taskColumn.selected; text: "View task"; onClicked: root.selectTask(modelData) }
                      ScrollView {
                        id: approvalScroll
                        visible: taskColumn.selected && root.needsApproval(modelData)
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        Layout.maximumHeight: 112
                        clip: true
                        onActiveFocusChanged: if (activeFocus) { root.clearPendingTaskInputRestore(); root.clearTaskActionFocus() }
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        Text { width: approvalScroll.availableWidth; text: "Approval needed:\n" + root.approvalSummary(modelData); wrapMode: Text.Wrap; color: root.alertTextColor; font.family: "Manrope"; Accessible.role: Accessible.AlertMessage }
                      }
                      Text { visible: taskColumn.selected && root.taskHasCodexSetupError(modelData); text: String((modelData.error || {}).message || "Codex needs setup before this task can run."); color: root.alertTextColor; font.family: "Manrope"; wrapMode: Text.Wrap; Layout.fillWidth: true; Accessible.role: Accessible.AlertMessage }
                      VoiceArea { id: taskInstruction; visible: taskColumn.selected; Layout.fillWidth: true; placeholderText: "Tell the agent what to change or do next"; text: root.taskInstructionDraft(modelData.id); onTextChanged: root.setTaskInstructionDraft(modelData.id, text); onCursorPositionChanged: if (activeFocus) root.setTaskInstructionSelection(modelData.id, cursorPosition, selectionStart, selectionEnd); onSelectionStartChanged: if (activeFocus) root.setTaskInstructionSelection(modelData.id, cursorPosition, selectionStart, selectionEnd); onSelectionEndChanged: if (activeFocus) root.setTaskInstructionSelection(modelData.id, cursorPosition, selectionStart, selectionEnd); wrapMode: TextEdit.Wrap; Accessible.name: "Instructions for " + String(modelData.title || "task"); onActiveFocusChanged: { if (activeFocus) { root.focusedTaskInputId = String(modelData.id || ""); root.setTaskInstructionSelection(modelData.id, cursorPosition, selectionStart, selectionEnd); root.clearTaskActionFocus(); root.clearPendingTaskInputRestore() } else if (root.focusedTaskInputId === String(modelData.id || "")) root.focusedTaskInputId = "" } }
                      Flow { visible: taskColumn.selected; Layout.fillWidth: true; spacing: 8
                        VoiceButton { id: approveButton; text: "Approve"; visible: taskColumn.selected && root.needsApproval(modelData); enabled: !!((modelData.approval || ({})).request_id || modelData.approval_request_id); onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "approve"); onClicked: root.taskAction(modelData, "approve") }
                        VoiceButton { id: denyButton; text: "Deny"; visible: taskColumn.selected && root.needsApproval(modelData); enabled: !!((modelData.approval || ({})).request_id || modelData.approval_request_id); onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "deny"); onClicked: root.taskAction(modelData, "deny") }
                        VoiceButton { id: steerButton; text: "Send update"; visible: taskColumn.selected && root.taskCapability(modelData, "steer") && ["accepted", "running", "waiting_input", "awaiting_approval"].indexOf(modelData.state) >= 0; enabled: taskInstruction.text.trim() !== ""; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "steer"); onClicked: root.taskAction(modelData, "steer", taskInstruction.text) }
                        VoiceButton { id: startButton; text: "Start"; visible: taskColumn.selected && modelData.state === "proposed"; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "start"); onClicked: root.taskAction(modelData, "start") }
                        VoiceButton { id: cancelButton; text: "Stop"; visible: taskColumn.selected && ["completed", "failed", "cancelled", "interrupted"].indexOf(modelData.state) < 0; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "cancel"); onClicked: root.taskAction(modelData, "cancel") }
                        VoiceButton { id: continueButton; text: "Continue"; visible: taskColumn.selected && root.taskCapability(modelData, "continue") && ["completed", "failed", "cancelled", "interrupted", "waiting_input"].indexOf(modelData.state) >= 0; enabled: taskInstruction.text.trim() !== ""; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "continueTask"); onClicked: root.taskAction(modelData, "continue", taskInstruction.text) }
                        VoiceButton { id: openFolderButton; text: "Open folder"; visible: taskColumn.selected && String(modelData.project || "") !== ""; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "openFolder"); onClicked: root.taskAction(modelData, "open_folder") }
                        VoiceButton { id: setupButton; text: "Open Codex setup"; visible: taskColumn.selected && root.taskHasCodexSetupError(modelData); onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "setup"); onClicked: root.send("desktop_action", { application: "hub" }) }
                        VoiceButton { id: reviewButton; text: "Review changes"; visible: taskColumn.selected && modelData.mode === "offline" && ["completed", "failed", "cancelled", "interrupted"].indexOf(modelData.state) >= 0; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "review"); onClicked: root.taskAction(modelData, "review") }
                        VoiceButton { id: exportButton; text: "Export reviewed changes"; visible: taskColumn.selected && !!(modelData.export_review || ({})).digest; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "exportTask"); onClicked: root.taskAction(modelData, "export") }
                        VoiceButton { id: dismissButton; text: "Dismiss"; visible: taskColumn.selected && ["completed", "failed", "cancelled", "interrupted"].indexOf(modelData.state) >= 0; onActiveFocusChanged: if (activeFocus) root.setTaskActionFocus(modelData.id, "dismiss"); onClicked: root.taskAction(modelData, "dismiss") }
                      }
                      VoiceButton { visible: taskColumn.selected && String(modelData.result || "") !== ""; text: taskColumn.reportOpen ? "Hide agent report" : "Show agent report"; onClicked: taskColumn.reportOpen = !taskColumn.reportOpen }
                      ScrollView {
                        id: reportScroll
                        visible: taskColumn.selected && taskColumn.reportOpen && String(modelData.result || "") !== ""
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        Layout.maximumHeight: 112
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        Text { width: reportScroll.availableWidth; text: String(modelData.result || ""); color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.Wrap }
                      }
                      ColumnLayout {
                        visible: taskColumn.selected && ((modelData.artifacts || []).length > 0)
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Artifacts"; color: root.textColor; font.family: "Manrope"; font.weight: Font.DemiBold; Accessible.role: Accessible.Heading }
                        Repeater {
                          model: modelData.artifacts || []
                          delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Text { text: String(modelData.path || "") + " · " + root.artifactVerificationText(modelData); color: modelData.exists === true ? root.textColor : root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            VoiceButton { text: "Open"; visible: modelData.exists === true; onClicked: root.taskAction(taskColumn.task, "open_artifact", String(modelData.path || "")) }
                          }
                        }
                      }
                      ColumnLayout {
                        visible: taskColumn.selected && ((modelData.activity || []).length > 0)
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Live activity"; color: root.textColor; font.family: "Manrope"; font.weight: Font.DemiBold; Accessible.role: Accessible.Heading }
                        ScrollView {
                          id: activityScroll
                          Layout.fillWidth: true
                          Layout.preferredHeight: 112
                          Layout.maximumHeight: 112
                          clip: true
                          ScrollBar.vertical.policy: ScrollBar.AsNeeded
                          Column {
                            width: activityScroll.availableWidth
                            spacing: 4
                            Repeater {
                              model: (modelData.activity || []).slice(Math.max(0, (modelData.activity || []).length - 8))
                              delegate: Text { required property var modelData; text: String(modelData.kind || "Activity") + ": " + String(modelData.text || ""); color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.Wrap; width: parent.width }
                            }
                          }
                        }
                      }
                      VoiceButton { visible: taskColumn.selected; text: taskColumn.technicalDetailsOpen ? "Hide technical details" : "Technical details"; onClicked: taskColumn.technicalDetailsOpen = !taskColumn.technicalDetailsOpen }
                      ColumnLayout {
                        visible: taskColumn.selected && taskColumn.technicalDetailsOpen
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Task ID: " + String(modelData.id || ""); color: root.secondaryTextColor; font.family: "Manrope"; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Text { visible: String(modelData.project || "") !== ""; text: "Workspace: " + String(modelData.project || ""); color: root.secondaryTextColor; font.family: "Manrope"; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Text { visible: root.taskSessionIdentity(modelData) !== ""; text: root.taskSessionIdentity(modelData); color: root.secondaryTextColor; font.family: "Manrope"; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Text { visible: root.needsApproval(modelData); text: "Approval request ID: " + String((modelData.approval || ({})).request_id || modelData.approval_request_id || ""); color: root.secondaryTextColor; font.family: "Manrope"; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Text { visible: root.needsApproval(modelData); text: "Approval payload:\n" + JSON.stringify(modelData.approval || ({}), null, 2); color: root.secondaryTextColor; font.family: "Manrope"; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                      }
                      Repeater { visible: taskColumn.selected; model: (modelData.export_review || ({})).changes || []; delegate: Text { required property var modelData; text: String(modelData.action) + ": " + String(modelData.path); color: root.textColor; Layout.fillWidth: true; wrapMode: Text.Wrap } }
                    }
                  }
                }
              }
            }
            ScrollView {
              id: settingsScroll
              clip: true
              ScrollBar.vertical.policy: ScrollBar.AlwaysOn
              ColumnLayout {
                width: settingsScroll.availableWidth - 14
                spacing: 12
                Text { text: "Voice settings"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 22; Accessible.role: Accessible.Heading }
                Text { visible: root.setupFocusMessage !== ""; text: root.setupFocusMessage; color: root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
                VoiceButton { text: root.advancedVoiceSettingsOpen ? "Hide advanced settings" : "Advanced Voice settings"; onClicked: root.advancedVoiceSettingsOpen = !root.advancedVoiceSettingsOpen }
                ColumnLayout {
                  visible: root.advancedVoiceSettingsOpen
                  Layout.fillWidth: true
                  spacing: 12
                  VoiceSelect { id: connectionMode; Layout.fillWidth: true; model: ["Maslow Voice", "Offline on this computer", "Your model server", "OpenAI Realtime", "GPT-Live cloud", "LiveKit Expressive"]; currentIndex: ["gemini_live", "offline", "server", "openai", "gpt_live", "livekit"].indexOf(root.settings.mode || "gemini_live"); Accessible.name: "Voice connection"; onActivated: root.configure("mode", ["gemini_live", "offline", "server", "openai", "gpt_live", "livekit"][currentIndex]) }
                  ColumnLayout { visible: ["offline", "server"].indexOf(root.settings.mode) >= 0; Layout.fillWidth: true
                    VoiceSelect { visible: root.settings.mode === "server"; model: ["Ollama", "LM Studio"]; currentIndex: root.settings.server_kind === "lmstudio" ? 1 : 0; Accessible.name: "Model server type"; onActivated: root.configure("server_kind", currentIndex === 1 ? "lmstudio" : "ollama") }
                  Text { visible: root.settings.mode === "server"; text: "Model server address"; color: root.secondaryTextColor; font.family: "Manrope" }
                    VoiceField { visible: root.settings.mode === "server"; Layout.fillWidth: true; placeholderText: "Model server address (local or remote)"; text: String(root.settings.server_url || ""); Accessible.name: "Model server address"; onEditingFinished: root.configure("server_url", text) }
                  Text { visible: root.settings.mode === "offline"; text: "Ollama models folder"; color: root.secondaryTextColor; font.family: "Manrope" }
                    VoiceField { visible: root.settings.mode === "offline"; Layout.fillWidth: true; placeholderText: "Ollama models folder"; text: String(root.settings.ollama_models || ""); Accessible.name: "Ollama models folder"; onEditingFinished: root.configure("ollama_models", text) }
                  Text { visible: true; text: "Speech models folder"; color: root.secondaryTextColor; font.family: "Manrope" }
                    VoiceField { Layout.fillWidth: true; placeholderText: "Speech models folder"; text: String(root.settings.speech_directory || ""); Accessible.name: "Speech models folder"; onEditingFinished: root.configure("speech_directory", text) }
                    RowLayout { Layout.fillWidth: true
                      VoiceSelect { Layout.fillWidth: true; model: root.readiness.models || []; textRole: "label"; valueRole: "id"; currentIndex: (root.readiness.models || []).findIndex(function(model) { return model.id === root.settings.model }); Accessible.name: "Available model"; onActivated: root.configure("model", currentValue) }
                      VoiceButton { text: "Find models"; onClicked: root.send("models") }
                    }
                    VoiceField { Layout.fillWidth: true; placeholderText: "Selected model"; text: String(root.settings.model || ""); Accessible.name: "Selected model"; onEditingFinished: root.configure("model", text) }
                    VoiceButton { text: "Download speech models"; onClicked: root.send("download_speech") }
                  }
                  ColumnLayout {
                    visible: root.settings.mode === "gemini_live"
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "Voice and conversation"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                    Text { text: "Voice"; color: root.textColor; font.family: "Manrope" }
                    VoiceSelect {
                      id: geminiVoice
                      enabled: !root.conversation && !root.working && !root.previewBusy
                      model: ["Puck", "Zephyr", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"]
                      currentIndex: model.indexOf(String(root.settings.gemini_live_voice || "Puck"))
                      displayText: currentIndex >= 0 ? currentText : String(root.settings.gemini_live_voice || "Puck")
                      Accessible.name: "Gemini voice"

                    }
                    RowLayout {
                      VoiceButton {
                        text: root.previewBusy ? "Stop preview" : "Play preview"
                        enabled: root.previewBusy || (!root.conversation && !root.working && geminiVoice.currentIndex >= 0)
                        onClicked: root.previewBusy ? root.send("stop_gemini_voice_preview") : root.send("preview_gemini_voice", { voice: geminiVoice.currentText })
                      }
                      VoiceButton { text: "Use this voice"; enabled: !root.conversation && !root.working && !root.previewBusy && geminiVoice.currentIndex >= 0; onClicked: root.configure("gemini_live_voice", geminiVoice.currentText) }
                    }
                    Text {
                      text: root.voicePreview.state === "error" ? String(root.voicePreview.error || "Preview failed.") : (root.previewBusy ? (root.voicePreview.state === "connecting" ? "Connecting preview…" : "Playing preview…") : "Saved voice: " + String(root.settings.gemini_live_voice || "Puck") + ". Preview uses your Google account. Microphone stays off.")
                      color: root.voicePreview.state === "error" ? root.alertTextColor : root.secondaryTextColor
                      font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true
                      Accessible.role: Accessible.StatusBar; Accessible.name: text
                    }
                    Text { text: "Conversation prompt"; color: root.textColor; font.family: "Manrope" }
                    Text { text: "Describe how Maslow should respond: tone, pace and level of detail. App and task controls remain available."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    ScrollView {
                      Layout.fillWidth: true
                      Layout.preferredHeight: 130
                      clip: true
                      VoiceArea {
                        id: geminiPrompt
                        wrapMode: TextEdit.Wrap
                        text: String(root.settings.gemini_live_prompt || root.defaultGeminiPrompt)
                        enabled: !root.conversation && !root.working && !root.previewBusy
                        Accessible.name: "Gemini conversation prompt"
                      }
                    }
                    RowLayout {
                      VoiceButton { text: "Save prompt"; enabled: !root.conversation && !root.working && !root.previewBusy && geminiPrompt.text.length <= 4096; onClicked: root.configure("gemini_live_prompt", geminiPrompt.text.trim() || root.defaultGeminiPrompt) }
                      VoiceButton { text: "Reset default"; enabled: !root.conversation && !root.working && !root.previewBusy; onClicked: { geminiPrompt.text = root.defaultGeminiPrompt; root.configure("gemini_live_prompt", root.defaultGeminiPrompt) } }
                    }
                    Text { text: geminiPrompt.text.length > 4096 ? "Keep the prompt within 4,096 characters." : (root.conversation || root.working ? "End the conversation and finish or stop active work before changing these settings." : "Choose Use this voice to save your choice. Save your prompt, then start a conversation to try it."); color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Text { text: "Maslow Voice setup"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                    Text { text: "Maslow Voice uses Gemini Live with Google AI Studio. LiveKit details save optional Expressive mode setup. Credentials stay in this computer's keyring."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Text { text: "LiveKit project URL (optional Expressive mode)"; color: root.textColor; font.family: "Manrope" }
                    VoiceField { id: geminiLiveUrlField; Layout.fillWidth: true; placeholderText: "wss://your-project.livekit.cloud (optional)"; text: String(root.settings.livekit_url || ""); Accessible.name: "Maslow Voice optional LiveKit project URL" }
                    Text { text: "LiveKit API credentials"; color: root.textColor; font.family: "Manrope" }
                    RowLayout { Layout.fillWidth: true; spacing: 8
                      VoiceField { id: geminiLiveApiKeyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API key"; Accessible.name: "Maslow Voice LiveKit API key" }
                      VoiceField { id: geminiLiveApiSecretField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API secret"; Accessible.name: "Maslow Voice LiveKit API secret" }
                    }
                    Text { text: "Google AI Studio API key"; color: root.textColor; font.family: "Manrope" }
                    VoiceField { id: geminiLiveGoogleApiKeyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "Google AI Studio API key"; Accessible.name: "Google AI Studio API key" }
                    Text { text: "LiveKit fields are optional and blank fields keep saved values. Add a Google key for first-time setup; leave it blank to keep a saved key."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    VoiceButton { text: root.geminiLiveSetupSaving ? "Saving Maslow Voice setup…" : "Save Maslow Voice setup"; enabled: !root.geminiLiveSetupSaving; onClicked: root.submitGeminiLiveSetup(geminiLiveUrlField.text, geminiLiveApiKeyField.text, geminiLiveApiSecretField.text, geminiLiveGoogleApiKeyField.text) }
                    Text { visible: root.geminiLiveSetupStatus !== ""; text: root.geminiLiveSetupStatus; color: root.geminiLiveSetupSucceeded ? root.accentTextColor : root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: root.geminiLiveSetupSucceeded ? Accessible.StatusBar : Accessible.AlertMessage; Accessible.name: text }
                    Text { visible: root.conversation; text: "End the conversation before changing Maslow Voice settings."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  }
                  ColumnLayout {
                    visible: root.settings.mode === "livekit"
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "LiveKit setup"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                    Text { text: "Enter your project URL and API credentials."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Text { text: "Project URL"; color: root.textColor; font.family: "Manrope" }
                    VoiceField { id: livekitUrlField; Layout.fillWidth: true; placeholderText: "wss://your-project.livekit.cloud"; text: String(root.settings.livekit_url || ""); Accessible.name: "LiveKit project URL" }
                    Text { text: "API credentials"; color: root.textColor; font.family: "Manrope" }
                    RowLayout { Layout.fillWidth: true; spacing: 8
                      VoiceField { id: livekitApiKeyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API key"; Accessible.name: "LiveKit API key" }
                      VoiceField { id: livekitApiSecretField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API secret"; Accessible.name: "LiveKit API secret" }
                    }
                    Text { text: "Blank fields keep saved values."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    VoiceButton { text: root.livekitSetupSaving ? "Saving LiveKit setup…" : "Save LiveKit setup"; enabled: !root.livekitSetupSaving; onClicked: root.submitLiveKitSetup(livekitUrlField.text, livekitApiKeyField.text, livekitApiSecretField.text) }
                    Text { visible: root.livekitSetupStatus !== ""; text: root.livekitSetupStatus; color: root.livekitSetupSucceeded ? root.accentTextColor : root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: root.livekitSetupSucceeded ? Accessible.StatusBar : Accessible.AlertMessage; Accessible.name: text }
                    RowLayout { Layout.fillWidth: true; spacing: 10
                      Text { text: "Voice"; color: root.textColor; font.family: "Manrope" }
                      VoiceSelect { Layout.fillWidth: true; enabled: !root.conversation; model: ["Ashley", "Edward", "Olivia", "Alex", "Dennis"]; currentIndex: model.indexOf(String(root.settings.livekit_voice || "Ashley")); Accessible.name: "LiveKit voice"; onActivated: root.configure("livekit_voice", currentText) }
                    }
                    Text { visible: root.conversation; text: "End the conversation before choosing a different voice."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  }
                  ColumnLayout {
                    visible: root.settings.mode === "gpt_live"
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "GPT-Live cloud"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                    Text { text: "Talk naturally, even while Maslow is speaking. It uses your saved OpenAI API key."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Text { text: "Voice"; color: root.textColor; font.family: "Manrope" }
                    VoiceSelect { Layout.fillWidth: true; enabled: !root.conversation; model: ["cedar", "marin", "alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse", "quartz", "ripple", "vesper", "willow", "stone", "gleam", "meridian", "bossa", "tempo", "beacon", "delta", "cinder"]; currentIndex: model.indexOf(String(root.settings.live_voice || "marin")); Accessible.name: "GPT-Live voice"; onActivated: root.configure("live_voice", currentText) }
                    Text { visible: root.conversation; text: "End the conversation before choosing a different voice."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  }
                  Text { visible: root.settings.mode === "openai"; text: "OpenAI voice model"; color: root.secondaryTextColor; font.family: "Manrope" }
                  VoiceField { visible: root.settings.mode === "openai"; Layout.fillWidth: true; placeholderText: "OpenAI voice model"; text: String(root.settings.realtime_model || ""); Accessible.name: "OpenAI voice model"; onEditingFinished: root.configure("realtime_model", text) }
                  Text { visible: root.settings.mode === "openai"; text: "Voice"; color: root.textColor; font.family: "Manrope" }
                  VoiceSelect { visible: root.settings.mode === "openai"; enabled: !root.conversation; model: ["cedar", "marin", "alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"]; currentIndex: model.indexOf(String(root.settings.realtime_voice || "cedar")); Accessible.name: "OpenAI Realtime voice"; onActivated: root.configure("realtime_voice", currentText) }
                  Text { visible: root.settings.mode === "openai" && root.conversation; text: "End the conversation before choosing a different voice."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  Text { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; text: "Credentials are stored privately on this computer."; color: root.secondaryTextColor; font.family: "Manrope" }
                  VoiceSelect { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; model: ["OpenAI API key", "Model server token", "Anthropic API key"]; Accessible.name: "Credential type"; onActivated: root.credentialName = ["openai", "server_token", "anthropic"][currentIndex] }
                  VoiceField { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "Paste credential"; text: root.credentialValue; onTextEdited: root.credentialValue = text; Accessible.name: "Credential" }
                  VoiceButton { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; text: "Save credential"; enabled: root.credentialValue !== ""; onClicked: root.submitCredential() }
                  VoiceSelect { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; model: ["Automatic routing", "Codex", "Claude Code", "Hermes"]; currentIndex: ["auto", "codex", "claude", "hermes"].indexOf(root.settings.default_coder || "auto"); Accessible.name: "Default coding agent"; onActivated: root.configure("default_coder", ["auto", "codex", "claude", "hermes"][currentIndex]) }
                  Text { visible: root.settings.mode === "gpt_live"; text: "Set up Hermes in Hub before sending tasks. Codex and Claude also need their own connections when selected."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  VoiceField { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0 && (["offline", "server"].indexOf(root.settings.mode) >= 0 || root.settings.default_coder === "claude"); Layout.fillWidth: true; placeholderText: "Task model (optional)"; text: String(root.settings.execution_model || ""); Accessible.name: "Task model"; onEditingFinished: root.configure("execution_model", text) }
                  VoiceButton { visible: root.settings.mode === "gemini_live"; text: root.advancedRequestOptionsOpen ? "Hide request overrides" : "Request overrides"; onClicked: root.advancedRequestOptionsOpen = !root.advancedRequestOptionsOpen }
                  ColumnLayout {
                    visible: root.settings.mode === "gemini_live" && root.advancedRequestOptionsOpen
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "Request overrides"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                    Text { text: "Use these only when a message needs an existing folder or extra context."; color: root.secondaryTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    VoiceField { id: projectOverrideField; Layout.fillWidth: true; placeholderText: "Existing project folder (optional)"; text: root.selectedProject; onTextEdited: root.selectedProject = text; Accessible.name: "Existing project folder" }
                    VoiceArea { Layout.fillWidth: true; placeholderText: "Extra context (optional)"; text: root.explicitContext; onTextChanged: root.explicitContext = text; Accessible.name: "Extra context"; implicitHeight: 76; wrapMode: TextEdit.Wrap }
                  }
                  VoiceButton { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) >= 0; text: root.advancedTaskSettingsOpen ? "Hide task settings" : "Task settings"; onClicked: root.advancedTaskSettingsOpen = !root.advancedTaskSettingsOpen }
                  ColumnLayout { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) >= 0 && root.advancedTaskSettingsOpen; Layout.fillWidth: true; spacing: 8
                    Text { text: "Task settings"; color: root.textColor; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                    VoiceSelect { model: ["Automatic routing", "Codex", "Claude Code", "Hermes"]; currentIndex: ["auto", "codex", "claude", "hermes"].indexOf(root.settings.default_coder || "auto"); Accessible.name: "Default coding agent"; onActivated: root.configure("default_coder", ["auto", "codex", "claude", "hermes"][currentIndex]) }
                    VoiceSelect { visible: root.settings.mode === "gemini_live"; model: ["Start explicit tasks in Voice Lab", "Review task before starting"]; currentIndex: root.settings.task_policy === "review" ? 1 : 0; Accessible.name: "Task start policy"; onActivated: root.configure("task_policy", currentIndex === 1 ? "review" : "lab_auto") }
                    VoiceField { visible: root.settings.default_coder === "claude"; Layout.fillWidth: true; placeholderText: "Task model (optional)"; text: String(root.settings.execution_model || ""); Accessible.name: "Task model"; onEditingFinished: root.configure("execution_model", text) }
                  }
                  VoiceButton { text: root.settings.mode === "openai" ? "Check setup" : "Check connection and readiness"; onClicked: root.send("test") }
                  VoiceCheck { text: "Reduce voice motion"; checked: root.reducedMotion; onToggled: root.configure("reduced_motion", checked); Accessible.name: text }
                  VoiceCheck { text: "Keep orb at bottom right"; checked: root.fixedPosition; onToggled: root.setFixedPosition(checked); Accessible.name: text }
                  VoiceButton { visible: root.orbManuallyPositioned; text: "Reset orb position"; onClicked: root.clearOrbPosition() }
                  VoiceField { Layout.fillWidth: true; placeholderText: "Display name or connector"; text: String(settings.display || ""); Accessible.name: "Voice display"; onEditingFinished: root.configure("display", text) }
                }
                Text { text: "Conversation readiness: " + (root.conversationReadiness().ready === true ? "Ready" : "Needs attention"); color: root.conversationReadiness().ready === true ? root.accentTextColor : root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.StatusBar; Accessible.name: text }
                Repeater { model: root.conversationReadiness().checks || []; delegate: Text { required property var modelData; text: (modelData.ok === true ? "Ready: " : "Needs attention: ") + String(modelData.name || "Check") + " — " + String(modelData.message || ""); color: modelData.ok === true ? root.accentTextColor : root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true } }
                Text { text: "Task readiness: " + (root.taskReadiness().ready === true ? "Ready" : "Needs attention"); color: root.taskReadiness().ready === true ? root.accentTextColor : root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.StatusBar; Accessible.name: text }
                Repeater { model: root.taskReadiness().checks || []; delegate: Text { required property var modelData; text: (modelData.ok === true ? "Ready: " : "Needs attention: ") + String(modelData.name || "Check") + " — " + String(modelData.message || ""); color: modelData.ok === true ? root.accentTextColor : root.alertTextColor; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true } }
              }
            }
          }
        }
      }
    }
  }
}
