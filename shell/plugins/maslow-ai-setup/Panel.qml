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
  property bool closingQueued: false
  property int step: 1
  property string statusText: ""
  property bool busy: false
  property bool stateCatalogLoaded: false
  property bool stateLoaded: false
  property bool adapterCatalogLoaded: false
  property var stateWriteQueue: []
  property var stateWriteCurrent: null
  property var statusQueue: []
  property string statusTool: ""
  property string activeTool: ""
  property string activeAction: ""
  property string accountChoice: ""
  property string hermesChoice: "recommended"
  property string memoryChoice: "builtin"
  property bool memoryConfirmed: true
  property bool memoryExpanded: false
  property string desktopChoice: "none"
  property string accountAuthentication: "unknown"
  property string hermesOperational: "unverified"
  property string hermesOwner: "none"
  property bool hermesCheckAvailable: false
  property bool reducedMotion: false
  property bool introVisible: false
  property int runGeneration: 0
  property int statusProcessGeneration: 0
  property int checkProcessGeneration: 0
  property int actionProcessGeneration: 0
  property string productName: "Maslow OS"
  property string productTagline: "A clear beginning for useful AI"
  property var codexChoiceButton: null
  property var desktopHermesChoiceButton: null

  readonly property color foreground: Color.foreground
  readonly property color background: Color.background
  readonly property color accent: Color.accent
  readonly property color urgent: Color.urgent
  readonly property color subdued: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.74)
  readonly property color line: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.18)
  readonly property color softSurface: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.055)
  readonly property string fontFamily: "Manrope"
  readonly property real contentScale: Math.max(0.9, Math.min(1, window.width / 1120, window.height / 680))

  ListModel { id: toolModel }

  component EditorialButton: Button {
    id: control
    property bool quiet: false
    Accessible.role: Accessible.Button
    Accessible.name: text
    focusable: true
    implicitHeight: Style.space(44)
    horizontalPadding: Style.space(16)
    verticalPadding: Style.space(10)
    background: quiet ? "transparent" : root.foreground
    foreground: quiet ? root.foreground : root.background
    accent: root.accent
    bordered: quiet
    fontFamily: root.fontFamily
    fontSize: Math.max(Style.font.body, Math.round(14 * root.contentScale))
    color: quiet ? "transparent" : root.foreground
    opacity: enabled ? (hot ? 0.92 : 1) : 0.45
    onActiveFocusChanged: if (activeFocus) root.ensureVisible(control)
    borderSpec: Border.controlSpec(activeFocus ? "focus" : "normal", quiet ? root.foreground : root.background, root.accent)
  }

  function ensureVisible(control) {
    var viewport = step === 1 ? welcomeView : (step === 2 ? connectView : openView)
    Qt.callLater(function() {
      if (!window.visible || !control) return
      var ancestor = control.parent
      while (ancestor && ancestor !== viewport.contentItem) ancestor = ancestor.parent
      if (!ancestor) return
      var point = control.mapToItem(viewport.contentItem, 0, 0)
      if (point.y < viewport.contentY) viewport.contentY = Math.max(0, point.y - 8)
      else if (point.y + control.height > viewport.contentY + viewport.height) viewport.contentY = Math.min(Math.max(0, viewport.contentHeight - viewport.height), point.y + control.height - viewport.height + 8)
    })
  }

  function findTool(toolId) {
    for (var index = 0; index < toolModel.count; index++) if (toolModel.get(index).toolId === toolId) return index
    return -1
  }

  function tool(toolId) {
    var index = findTool(toolId)
    return index >= 0 ? toolModel.get(index) : null
  }

  function statusFor(toolId) {
    var item = tool(toolId)
    return item ? item : { toolName: toolId, available: false, installed: false, desktopInstalled: false, runtimeState: "none", authentication: "unknown", runtimeOwner: "none", checkAvailable: false, history: "not-started" }
  }

  function accountProofSufficient() { return (accountChoice === "codex" || accountChoice === "claude") && accountAuthentication === "signed-in" }
  function hermesProofSufficient() { return hermesChoice === "deferred" || hermesOperational === "ready" }
  function memoryChoiceValid() { return memoryChoice === "builtin" || memoryChoice === "deferred" || ((memoryChoice === "honcho" || memoryChoice === "hindsight") && memoryConfirmed) }
  function legacyProgressIncomplete() {
    for (var index = 0; index < toolModel.count; index++) {
      var history = String(toolModel.get(index).history || "not-started")
      if (history === "selected" || history === "in-progress" || history === "action-required" || history === "needs-attention") return true
    }
    return false
  }
  function desktopChoiceReady() { return desktopChoice === "none" || statusFor(desktopChoice).runtimeState === "ready" }
  function completionMessage() {
    if (legacyProgressIncomplete()) return "An earlier setup choice is unfinished. Finish for now, or start again."
    if (!accountProofSufficient()) return "Connect an account to finish setup."
    if (!hermesProofSufficient()) return "Hermes is not checked. You can choose Set up Hermes later."
    if (!memoryChoiceValid()) return "Confirm your memory setup, or choose built-in memory for now."
    if (!desktopChoiceReady()) return "Your desktop app still needs setup. Refresh its status, or choose no desktop app."
    return hermesChoice === "deferred" ? "Your account is connected. Hermes can be set up later." : "Your account is connected. You can finish setup."
  }
  function completeEligible() { return stateCatalogLoaded && stateLoaded && adapterCatalogLoaded && accountProofSufficient() && hermesProofSufficient() && memoryChoiceValid() && desktopChoiceReady() && !legacyProgressIncomplete() }

  function statusLabel(value) {
    if (value === "signed-in") return "Signed in"
    if (value === "signed-out") return "Sign-in needed"
    if (value === "ready") return "Operational check passed this session"
    if (value === "failed") return "Operational check needs attention"
    if (value === "unavailable") return "Check unavailable"
    return "Unable to verify"
  }

  function desktopStateLabel(item) {
    if (item.reasonCode === "status-unavailable") return "Unable to verify"
    if (item.runtimeState === "attention") return "Needs attention"
    if (item.desktopInstalled !== true) return "Ready to install"
    if (item.runtimeState === "preparing") return "Preparing desktop app"
    if (item.runtimeState === "ready") return "Ready to open"
    return "Desktop status unavailable"
  }

  function desktopActionLabel(item) {
    if (item.desktopInstalled !== true) return "Install & open"
    if (item.runtimeState === "preparing") return "Open setup"
    if (item.runtimeState === "attention") return "Open setup"
    if (item.runtimeState === "ready") return "Open " + item.toolName
    return "Check desktop"
  }

  function canRunToolAction(item, action) {
    if (action === "open" && item.desktopInstalled === true && (item.toolId === "hermes-desktop" || item.toolId === "chatgpt-desktop")) return true
    if (item.runtimeOwner === "foreign") return false
    if (action === "install") return item.available === true
    return item.installed === true || item.available === true
  }

  function choiceValue(key) {
    if (key === "account") return accountChoice
    if (key === "hermes") return hermesChoice
    if (key === "memory") return memoryChoice
    if (key === "desktop") return desktopChoice
    return ""
  }

  function saveChoice(key, value) {
    if (closingQueued || value === "") return
    if (key === "account") accountChoice = value
    if (key === "hermes") hermesChoice = value
    if (key === "memory") memoryChoice = value
    if (key === "desktop") desktopChoice = value
    queueStateWrite(["omarchy-setup-ai-state", "choice", key, value])
  }

  function applyState(state) {
    step = Math.max(1, Math.min(3, Number(state.currentStep || 1)))
    accountChoice = ""
    hermesChoice = "recommended"
    memoryChoice = "builtin"
    desktopChoice = "none"
    var choices = state.setupChoices || {}
    if (choices.account === "codex" || choices.account === "claude") accountChoice = choices.account
    if (choices.hermes === "recommended" || choices.hermes === "deferred") hermesChoice = choices.hermes
    if (choices.memory === "builtin" || choices.memory === "honcho" || choices.memory === "hindsight" || choices.memory === "deferred") memoryChoice = choices.memory
    if (choices.desktop === "hermes-desktop" || choices.desktop === "chatgpt-desktop" || choices.desktop === "none") desktopChoice = choices.desktop
    memoryConfirmed = memoryChoice === "builtin" || memoryChoice === "deferred"
    var savedTools = state.tools || {}
    for (var toolId in savedTools) {
      var index = findTool(toolId)
      if (index >= 0) toolModel.setProperty(index, "history", String(savedTools[toolId].status || "not-started"))
    }
  }

  function applyAdapterCatalog(catalog) {
    var entries = catalog.tools || []
    for (var i = 0; i < entries.length; i++) {
      var entry = entries[i]
      var toolId = String(entry.id || "")
      var index = findTool(toolId)
      if (index < 0 && (toolId === "hermes-desktop" || toolId === "chatgpt-desktop")) {
        toolModel.append({ toolId: toolId, toolName: String(entry.name || toolId), supported: false, available: false, installed: false, authentication: "unknown", runtimeOwner: "none", runtimeState: "none", desktopInstalled: false, checkAvailable: false, reasonCode: "", history: "not-started" })
        index = findTool(toolId)
      }
      if (index >= 0) toolModel.setProperty(index, "supported", entry.supported === true)
    }
    adapterCatalogLoaded = true
    startStatusChecks()
  }

  function startStatusChecks() {
    if (!stateCatalogLoaded || !adapterCatalogLoaded || statusProc.running || closingQueued) return
    var next = []
    var toolIds = ["codex", "claude", "hermes", "hermes-desktop", "chatgpt-desktop"]
    for (var index = 0; index < toolIds.length; index++) {
      var toolId = toolIds[index]
      if (tool(toolId) && tool(toolId).supported) next.push(toolId)
    }
    statusQueue = next
    checkNextStatus()
  }

  function checkNextStatus() {
    if (!window.visible || statusProc.running || closingQueued || statusQueue.length === 0) return
    var next = statusQueue.slice()
    statusTool = String(next.shift())
    statusQueue = next
    statusProcessGeneration = runGeneration
    statusProc.command = ["omarchy-setup-ai-tool", "status", statusTool]
    statusProc.running = true
  }

  function refreshStatus(toolIds) {
    if (closingQueued || statusProc.running) return
    statusQueue = toolIds.slice()
    checkNextStatus()
  }

  function applyToolStatus(result) {
    var index = findTool(String(result.id || ""))
    if (result.schemaVersion !== 1 || index < 0 || result.supported !== true || typeof result.available !== "boolean" || typeof result.installed !== "boolean") return false
    var oldOwner = String(toolModel.get(index).runtimeOwner || "none")
    var owner = String(result.runtimeOwner || "none")
    toolModel.setProperty(index, "available", result.available === true)
    toolModel.setProperty(index, "installed", result.installed === true)
    toolModel.setProperty(index, "authentication", ["signed-in", "signed-out", "unknown"].includes(result.authentication) ? result.authentication : "unknown")
    toolModel.setProperty(index, "runtimeOwner", owner)
    toolModel.setProperty(index, "runtimeState", String(result.runtimeState || "none"))
    toolModel.setProperty(index, "desktopInstalled", result.desktopInstalled === true)
    toolModel.setProperty(index, "checkAvailable", result.checkAvailable === true)
    toolModel.setProperty(index, "reasonCode", String(result.reasonCode || ""))
    if ((result.id === "codex" || result.id === "claude") && accountChoice === result.id) accountAuthentication = toolModel.get(index).authentication
    if (result.id === "hermes") {
      hermesCheckAvailable = result.checkAvailable === true
      hermesOwner = owner
      if (oldOwner !== owner || result.installed !== true || result.runtimeState !== "ready") hermesOperational = "unverified"
    }
    return true
  }

  function invalidateStatus(toolId) {
    var index = findTool(toolId)
    if (index >= 0) {
      toolModel.setProperty(index, "authentication", "unknown")
      toolModel.setProperty(index, "installed", false)
      toolModel.setProperty(index, "available", false)
      toolModel.setProperty(index, "runtimeState", "attention")
      toolModel.setProperty(index, "checkAvailable", false)
      toolModel.setProperty(index, "reasonCode", "status-unavailable")
    }
    if (accountChoice === toolId) accountAuthentication = "unknown"
    if (toolId === "hermes") hermesOperational = "unverified"
  }

  function selectAccount(toolId) {
    if (busy || closingQueued) return
    saveChoice("account", toolId)
    accountAuthentication = statusFor(toolId).authentication
    statusText = accountAuthentication === "signed-in" ? "This provider reports a signed-in session. Continue when you are ready." : "Open the provider’s normal sign-in flow, then refresh its status."
  }

  function selectHermes(value) {
    if (busy || closingQueued) return
    saveChoice("hermes", value)
    if (value === "deferred") statusText = "Hermes is deferred. You can open its normal guided setup whenever you want."
  }

  function selectMemory(value) {
    if (busy || closingQueued) return
    saveChoice("memory", value)
    memoryConfirmed = value === "builtin" || value === "deferred"
    memoryExpanded = value === "honcho" || value === "hindsight"
    if (value === "builtin") statusText = "Hermes built-in memory is the default. No provider configuration was checked."
    else if (value === "deferred") statusText = "External memory setup is deferred."
    else statusText = "Open Hermes’ official memory wizard to configure this optional provider."
  }

  function confirmMemorySetup() {
    if (memoryChoice !== "honcho" && memoryChoice !== "hindsight") return
    memoryConfirmed = true
    statusText = "Memory setup is user-confirmed. Maslow has not independently checked this provider."
  }

  function selectDesktop(value) {
    if (busy || closingQueued) return
    saveChoice("desktop", value)
    if (value === "none") statusText = "A desktop app is optional. Your chosen tools remain available from the normal launcher."
  }

  function queueStateWrite(command, closeAfterWrite, launchTool, launchAction) {
    if (closingQueued && closeAfterWrite !== true) return
    if (closeAfterWrite === true) closingQueued = true
    var pending = stateWriteQueue.slice()
    pending.push({ command: command, closeAfterWrite: closeAfterWrite === true, launchTool: String(launchTool || ""), launchAction: String(launchAction || "") })
    stateWriteQueue = pending
    startNextStateWrite()
  }

  function startNextStateWrite() {
    if (stateWriteProc.running || stateWriteCurrent !== null || stateWriteQueue.length === 0) return
    var pending = stateWriteQueue.slice()
    stateWriteCurrent = pending.shift()
    stateWriteQueue = pending
    stateWriteProc.command = stateWriteCurrent.command
    stateWriteProc.running = true
  }

  function runToolAction(toolId, action) {
    var item = statusFor(toolId)
    if (busy || closingQueued || (item.reasonCode === "path-shadow") || (!canRunToolAction(item, action) && toolId !== "honcho" && toolId !== "hindsight")) return
    busy = true
    activeTool = toolId
    activeAction = action
    statusText = action === "install" ? "The installer is open. Return here when it finishes." : "The sign-in or setup window is open. Return here when you are done."
    actionProcessGeneration = runGeneration
    var key = toolId === "codex" || toolId === "claude" ? "account" : (toolId.indexOf("desktop") >= 0 ? "desktop" : (toolId === "hermes" ? "hermes" : "memory"))
    var value = key === "hermes" ? hermesChoice : toolId
    queueStateWrite(["omarchy-setup-ai-state", "choice", key, value], false, toolId, action)
  }

  function openMemoryWizard() {
    if (memoryChoice === "honcho") runToolAction("honcho", "open")
    else if (memoryChoice === "hindsight") runToolAction("hindsight", "open")
  }

  function checkHermes() {
    if (busy || closingQueued) return
    if (!hermesCheckAvailable) {
      hermesOperational = "unavailable"
      statusText = "Check unavailable. Open Hermes’ guided setup, then try again when its safe bounded check is available."
      return
    }
    busy = true
    statusText = "Checking Hermes with one small request to the provider Hermes is already configured to use. No provider is selected here."
    checkProcessGeneration = runGeneration
    hermesCheckProc.command = ["omarchy-setup-ai-tool", "check", "hermes"]
    hermesCheckProc.running = true
  }

  function saveStep(next) { if (!closingQueued) { step = next; queueStateWrite(["omarchy-setup-ai-state", "step", String(next)]); focusCurrentStep() } }
  function finishForNow() { if (!closingQueued) queueStateWrite(["omarchy-setup-ai-state", "defer"], true) }
  function completeSetup() { if (completeEligible() && !closingQueued) queueStateWrite(["omarchy-setup-ai-state", "complete"], true) }

  function cancelReadOnlyChecks() {
    if (statusProc.running) statusProc.signal(15)
    if (hermesCheckProc.running) hermesCheckProc.signal(15)
    statusQueue = []
    actionRefresh.stop()
  }

  function resetSetup() {
    runGeneration += 1
    cancelReadOnlyChecks()
    step = 1
    focusCurrentStep()
    accountChoice = ""
    hermesChoice = "recommended"
    memoryChoice = "builtin"
    memoryConfirmed = true
    memoryExpanded = false
    desktopChoice = "none"
    accountAuthentication = "unknown"
    hermesOperational = "unverified"
    for (var index = 0; index < toolModel.count; index++) toolModel.setProperty(index, "history", "not-started")
    queueStateWrite(["omarchy-setup-ai-state", "reset"])
  }

  function requestClose() {
    cancelReadOnlyChecks()
    if (shell && typeof shell.hide === "function") shell.hide("maslow.ai-setup")
    else window.visible = false
  }

  function close() {
    closingFromHost = true
    runGeneration += 1
    cancelReadOnlyChecks()
    window.visible = false
    closingFromHost = false
  }

  function focusCurrentStep() {
    Qt.callLater(function() {
      if (!window.visible) return
      if (step === 1) welcomeContinue.forceActiveFocus()
      else if (step === 2 && accountChoice === "" && codexChoiceButton) codexChoiceButton.forceActiveFocus()
      else if (step === 2) hermesChoiceButton.forceActiveFocus()
      else if (desktopChoice === "none" && desktopHermesChoiceButton) desktopHermesChoiceButton.forceActiveFocus()
      else finishForNowButton.forceActiveFocus()
    })
  }

  function open(payloadJson) {
    cancelReadOnlyChecks()
    runGeneration += 1
    closingQueued = false
    busy = false
    stateCatalogLoaded = false
    stateLoaded = false
    adapterCatalogLoaded = false
    statusQueue = []
    statusText = ""
    accountAuthentication = "unknown"
    hermesOperational = "unverified"
    memoryConfirmed = memoryChoice === "builtin" || memoryChoice === "deferred"
    memoryExpanded = false
    introVisible = false
    window.visible = true
    Qt.callLater(function() { introVisible = true })
    stateCatalogProc.running = true
    adapterCatalogProc.running = true
    stateProc.command = ["omarchy-setup-ai-state", "open"]
    stateProc.running = true
    productProc.running = true
    focusCurrentStep()
  }

  Process {
    id: productProc
    command: ["omarchy-branding-product", "--json"]
    stdout: StdioCollector { id: productOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) return
      try { var product = JSON.parse(productOutput.text).product; root.productName = String(product.name || "Maslow OS"); root.productTagline = String(product.tagline || "A clear beginning for useful AI") } catch (error) {}
    }
  }

  Process {
    id: stateCatalogProc
    command: ["omarchy-setup-ai-state", "catalog"]
    stdout: StdioCollector { id: stateCatalogOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) { root.statusText = "The setup list could not be loaded."; return }
      try {
        var catalog = JSON.parse(stateCatalogOutput.text)
        toolModel.clear()
        for (var i = 0; i < catalog.tools.length; i++) {
          var entry = catalog.tools[i]
          toolModel.append({ toolId: String(entry.id), toolName: String(entry.name), supported: false, available: false, installed: false, authentication: "unknown", runtimeOwner: "none", runtimeState: "none", desktopInstalled: false, checkAvailable: false, reasonCode: "", history: "not-started" })
        }
        root.stateCatalogLoaded = true
        if (stateOutput.text) root.applyState(JSON.parse(stateOutput.text))
        if (adapterCatalogOutput.text) root.applyAdapterCatalog(JSON.parse(adapterCatalogOutput.text))
      } catch (error) { root.statusText = "The setup list could not be read." }
    }
  }

  Process {
    id: adapterCatalogProc
    command: ["omarchy-setup-ai-tool", "catalog"]
    stdout: StdioCollector { id: adapterCatalogOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) { root.statusText = "Tool actions are unavailable right now."; return }
      try { root.applyAdapterCatalog(JSON.parse(adapterCatalogOutput.text)) } catch (error) { root.statusText = "Tool actions are unavailable right now." }
    }
  }

  Process {
    id: stateProc
    stdout: StdioCollector { id: stateOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) { root.statusText = "AI setup progress needs attention."; return }
      try { root.stateLoaded = true; root.applyState(JSON.parse(stateOutput.text)) } catch (error) { root.statusText = "AI setup progress could not be read." }
    }
  }

  Process {
    id: statusProc
    stdout: StdioCollector { id: toolStatusOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (root.statusProcessGeneration !== root.runGeneration) { root.checkNextStatus(); return }
      if (exitCode === 0) {
        try {
          var result = JSON.parse(toolStatusOutput.text)
          if (result.id !== root.statusTool || !root.applyToolStatus(result)) throw new Error("invalid status")
        } catch (error) { root.invalidateStatus(root.statusTool); root.statusText = "One tool status could not be read. Refresh to try again." }
      } else if (!root.closingQueued) { root.invalidateStatus(root.statusTool); root.statusText = "One tool status could not be checked. Refresh to try again." }
      root.checkNextStatus()
    }
  }

  Process {
    id: hermesCheckProc
    stdout: StdioCollector { id: hermesCheckOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (root.checkProcessGeneration !== root.runGeneration) return
      root.busy = false
      try { var result = JSON.parse(hermesCheckOutput.text); if (result.schemaVersion !== 1 || result.id !== "hermes") throw new Error("invalid result"); root.hermesOperational = result.operational === "unavailable" ? "unavailable" : (exitCode === 0 && result.operational === "ready" ? "ready" : "failed") } catch (error) { root.hermesOperational = exitCode === 0 ? "failed" : "unavailable" }
      if (root.hermesOperational === "ready" && exitCode === 0) root.statusText = "Hermes returned the bounded readiness marker for this session."
      else if (root.hermesOperational === "unavailable") root.statusText = "Check unavailable. Hermes guided setup remains available."
      else root.statusText = "Hermes did not pass its operational check. Review its guided setup and try again."
    }
  }

  Process {
    id: stateWriteProc
    onExited: function(exitCode) {
      var completed = root.stateWriteCurrent
      root.stateWriteCurrent = null
      if (exitCode !== 0) {
        root.statusText = "Could not save this setup choice. The panel stays open so you can retry."
        root.busy = false
        root.closingQueued = false
        root.stateWriteQueue = []
        return
      }
      if (completed && completed.launchTool !== "") {
        root.activeTool = completed.launchTool
        root.activeAction = completed.launchAction
        actionProc.command = ["omarchy-setup-ai-tool", root.activeAction, root.activeTool]
        // External sign-in and package transactions outlive this on-demand panel.
        actionProc.startDetached()
        actionRefresh.restart()
        root.busy = false
        root.statusText = completed.launchAction === "install" ? "The installer runs in a separate window. Closing setup will not stop it. Refresh status when it finishes." : "Continue in the sign-in or setup window, then refresh status here."
      }
      if (completed && completed.closeAfterWrite) { root.requestClose(); return }
      root.startNextStateWrite()
    }
  }

  Process { id: actionProc }

  // Detached windows have no exit callback. Rediscover state without inference;
  // the explicit Refresh action remains available after longer installations.
  Timer {
    id: actionRefresh
    interval: 3000
    onTriggered: {
      if (!window.visible || root.closingQueued) return
      if (root.activeTool === "hermes-desktop") root.refreshStatus(["hermes-desktop", "hermes"])
      else if (root.activeTool === "chatgpt-desktop") root.refreshStatus(["chatgpt-desktop"])
      else if (root.activeTool === "codex" || root.activeTool === "claude" || root.activeTool === "hermes") root.refreshStatus([root.activeTool])
    }
  }

  FileView {
    id: reducedMotionFile
    path: Quickshell.env("HOME") + "/.local/state/omarchy/toggles/hypr/reduced-motion.lua"
    watchChanges: true
    printErrors: false
    onLoaded: root.reducedMotion = String(text() || "").trim().length > 0
    onFileChanged: reload()
    onLoadFailed: root.reducedMotion = false
  }

  FloatingWindow {
    id: window
    title: root.productName + " AI Setup"
    color: root.background
    implicitWidth: 1120
    implicitHeight: 680
    minimumSize: Qt.size(600, 480)
    onVisibleChanged: if (!visible && !root.closingFromHost && root.shell && typeof root.shell.hide === "function") root.shell.hide("maslow.ai-setup")

    FocusScope {
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: root.requestClose()
      ColumnLayout {
        anchors.fill: parent
        anchors.margins: Math.max(Style.space(20), Math.round(40 * root.contentScale))
        spacing: Math.max(Style.space(12), Math.round(18 * root.contentScale))
        opacity: root.introVisible ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 260; easing.type: Easing.OutCubic } }

        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(12)
          Text { textFormat: Text.PlainText; text: ""; color: root.accent; font.family: "omarchy"; font.pixelSize: Math.round(34 * root.contentScale); Accessible.role: Accessible.Graphic; Accessible.name: "Maslow mark" }
          ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Text { textFormat: Text.PlainText; text: root.productName; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.max(Style.font.heading, Math.round(18 * root.contentScale)) }
            Text { textFormat: Text.PlainText; Layout.fillWidth: true; elide: Text.ElideRight; text: "AI SETUP  /  " + root.productTagline; color: root.subdued; font.family: root.fontFamily; font.weight: Font.DemiBold; font.letterSpacing: 1.1; font.pixelSize: Math.max(Style.font.bodySmall, Math.round(10 * root.contentScale)) }
          }
          EditorialButton { text: "Start again"; quiet: true; enabled: !root.busy && !root.closingQueued; Accessible.name: "Reset setup choices"; onClicked: root.resetSetup() }
          EditorialButton { text: "Close"; quiet: true; enabled: !root.closingQueued; onClicked: root.requestClose() }
        }

        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(8)
          Repeater {
            model: ["01  Welcome", "02  Connect", "03  Open"]
            delegate: RowLayout {
              required property int index
              required property string modelData
              Layout.fillWidth: true
              spacing: Style.space(8)
              Rectangle { Layout.fillWidth: true; implicitHeight: 3; color: index + 1 <= root.step ? root.accent : root.line }
              Text { textFormat: Text.PlainText; text: modelData; color: index + 1 === root.step ? root.foreground : root.subdued; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.max(Style.font.bodySmall, Math.round(11 * root.contentScale)) }
            }
          }
        }

        StackLayout {
          Layout.fillWidth: true
          Layout.fillHeight: true
          Layout.maximumWidth: 1040
          Layout.alignment: Qt.AlignHCenter
          enabled: root.stateLoaded && root.stateCatalogLoaded && root.adapterCatalogLoaded
          currentIndex: root.step - 1

          ColumnLayout {
            spacing: Style.space(14)
            Flickable {
              id: welcomeView
              Layout.fillWidth: true
              Layout.fillHeight: true
              contentWidth: width
              contentHeight: Math.max(height, welcomeRow.implicitHeight)
              clip: true
              boundsBehavior: Flickable.StopAtBounds
              ScrollBar.vertical: ScrollBar {}
              RowLayout {
              id: welcomeRow
              width: welcomeView.width
              height: welcomeView.contentHeight
              spacing: Math.round(48 * root.contentScale)
              ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.maximumWidth: window.width >= 1000 ? 560 : 10000
                spacing: Style.space(18)
                Item { Layout.fillHeight: true; Layout.maximumHeight: Style.space(40) }
                Text { textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Your AI.\nReady to work."; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.round(54 * root.contentScale); lineHeight: 0.98 }
                Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: "Maslow brings your AI tools into one focused workspace. Connect an account, meet Hermes if you want an assistant with memory, then choose an optional desktop app."; wrapMode: Text.WordWrap; color: root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.heading, Math.round(18 * root.contentScale)); lineHeight: 1.35 }
                ColumnLayout {
                  spacing: Style.space(8)
                  Repeater {
                    model: ["Connect one provider you already use.", "Keep Hermes recommended or defer it for now.", "Choose built-in memory or an optional guided provider."]
                    delegate: RowLayout {
                      Text { textFormat: Text.PlainText; text: "0" + (index + 1); color: root.accent; font.family: root.fontFamily; font.weight: Font.Bold; font.pixelSize: Math.max(Style.font.body, Math.round(12 * root.contentScale)) }
                      Text { textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: modelData; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(14 * root.contentScale)) }
                    }
                  }
                }
                Item { Layout.fillHeight: true }
              }
              Item {
                visible: window.width >= 1000
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 340
                Accessible.role: Accessible.Graphic
                Accessible.name: "Maslow setup illustration"
                Rectangle { anchors.fill: parent; color: root.softSurface; border.color: root.line; border.width: 1; radius: Style.space(12) }
                Rectangle { width: parent.width * 0.60; height: parent.height * 0.20; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: Style.space(30); color: root.accent; radius: Style.space(8); rotation: -7 }
                Rectangle { width: parent.width * 0.48; height: parent.height * 0.48; anchors.centerIn: parent; color: root.foreground; radius: Style.space(8) }
                Rectangle { width: parent.width * 0.24; height: parent.height * 0.24; anchors.centerIn: parent; color: root.background; radius: width / 2; border.color: root.accent; border.width: 3 }
                Text { textFormat: Text.PlainText; anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: Style.space(24); text: "01 / 03\nREADY TO BEGIN"; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.max(Style.font.body, Math.round(12 * root.contentScale)); lineHeight: 1.5 }
              }
            }
            }
            RowLayout {
              spacing: Style.space(12)
              EditorialButton { id: welcomeContinue; text: "Connect your account  →"; enabled: !root.closingQueued; Accessible.name: "Continue to Connect"; onClicked: root.saveStep(2) }
              EditorialButton { text: "Finish for now"; quiet: true; enabled: !root.closingQueued; Accessible.name: "Defer setup"; onClicked: root.finishForNow() }
            }
            Text { textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "No passwords, account details, or personal notes are requested here."; color: root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(12 * root.contentScale)) }
          }

          Flickable {
            id: connectView
            contentWidth: width
            contentHeight: connectContent.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            ColumnLayout {
              id: connectContent
              width: connectView.width - Style.space(8)
              spacing: Style.space(14)
              Text { textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "A familiar account.\nA useful start."; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.round(42 * root.contentScale); lineHeight: 1.0 }
              Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: "Connect one account to get started. You can add another whenever you like."; color: root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(16 * root.contentScale)); wrapMode: Text.WordWrap }
              GridLayout {
                columns: window.width < 900 ? 1 : 2
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                Repeater {
                  model: [{ id: "codex", title: "ChatGPT", copy: "Your ChatGPT account powers Codex, the OpenAI tool included with Maslow." }, { id: "claude", title: "Claude Code", copy: "Your Claude account powers Claude Code, included and ready to sign in." }]
                  delegate: BorderSurface {
                    id: accountCard
                    required property var modelData
                    property var entry: root.statusFor(modelData.id)
                    Layout.fillWidth: true
                    Layout.preferredHeight: Style.space(200)
                    color: root.accountChoice === modelData.id ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18) : root.softSurface
                    borderSpec: Border.controlSpec(root.accountChoice === modelData.id ? "selected" : "normal", root.foreground, root.accent)
                    radius: Style.space(10)
                    ColumnLayout {
                      anchors.fill: parent
                      anchors.margins: Style.space(18)
                      spacing: Style.space(8)
                      Text { textFormat: Text.PlainText; text: accountCard.modelData.title; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.max(Style.font.heading, Math.round(23 * root.contentScale)) }
                      Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: accountCard.modelData.copy; color: root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(13 * root.contentScale)); wrapMode: Text.WordWrap }
                      RowLayout {
                        Layout.fillWidth: true
                        Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: root.statusLabel(accountCard.entry.authentication); color: accountCard.entry.authentication === "signed-out" ? root.urgent : root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.max(Style.font.body, Math.round(12 * root.contentScale)) }
                        EditorialButton {
                          id: accountChoiceButton
                          text: root.accountChoice === accountCard.modelData.id ? "Selected" : "Choose"
                          quiet: root.accountChoice !== accountCard.modelData.id
                          Accessible.name: "Choose " + accountCard.modelData.title
                          onClicked: root.selectAccount(accountCard.modelData.id)
                          Component.onCompleted: { if (accountCard.modelData.id === "codex") root.codexChoiceButton = accountChoiceButton }
                        }
                      }
                    }
                  }
                }
              }
              GridLayout {
                columns: window.width < 900 ? 1 : 3
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                visible: root.accountChoice !== ""
                Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: root.accountProofSufficient() ? "Your account is connected. You can continue setup." : "Finish signing in, then refresh this status."; color: root.accountProofSufficient() ? root.foreground : root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(13 * root.contentScale)); wrapMode: Text.WordWrap }
                EditorialButton { text: root.statusFor(root.accountChoice).reasonCode === "path-shadow" ? "Needs attention" : (root.statusFor(root.accountChoice).installed ? (root.accountProofSufficient() ? "Open " + root.statusFor(root.accountChoice).toolName : "Sign in to " + (root.accountChoice === "codex" ? "ChatGPT" : "Claude")) : "Repair " + root.accountChoice); enabled: !root.busy && root.statusFor(root.accountChoice).reasonCode !== "path-shadow" && (root.statusFor(root.accountChoice).installed || root.statusFor(root.accountChoice).available); onClicked: root.runToolAction(root.accountChoice, root.statusFor(root.accountChoice).installed ? (root.accountProofSufficient() ? "launch" : "open") : "install") }
                EditorialButton { text: "Refresh status"; quiet: true; enabled: !root.busy; onClicked: root.refreshStatus([root.accountChoice]) }
              }
              Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.line }
              GridLayout {
                columns: window.width < 900 ? 1 : 3
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: "Hermes is an optional assistant that can bring tools and memory together. You can set it up now or come back later."; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.heading, Math.round(16 * root.contentScale)); wrapMode: Text.WordWrap }
                EditorialButton { id: hermesChoiceButton; text: root.hermesChoice === "deferred" ? "Set up Hermes" : "Set up Hermes later"; quiet: root.hermesChoice === "deferred"; enabled: !root.busy; onClicked: root.selectHermes(root.hermesChoice === "deferred" ? "recommended" : "deferred") }
                EditorialButton { text: root.statusFor("hermes").reasonCode === "path-shadow" ? "Needs attention" : "Open guided setup"; quiet: true; enabled: !root.busy && root.statusFor("hermes").reasonCode !== "path-shadow" && (root.statusFor("hermes").installed || root.statusFor("hermes").available); onClicked: root.runToolAction("hermes", root.statusFor("hermes").installed ? "launch" : "install") }
              }
              GridLayout {
                columns: window.width < 900 ? 1 : 2
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                visible: root.hermesChoice === "recommended"
                Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: root.hermesOperational === "unverified" ? (root.hermesCheckAvailable ? "Check sends one small bounded request to the provider Hermes is already configured to use." : "This version cannot run an automatic check safely. Guided setup is still available.") : root.statusLabel(root.hermesOperational); color: root.hermesOperational === "failed" || root.hermesOperational === "unavailable" ? root.urgent : root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(13 * root.contentScale)); wrapMode: Text.WordWrap }
                EditorialButton { text: root.hermesCheckAvailable ? "Check Hermes" : "Check unavailable"; quiet: !root.hermesCheckAvailable; enabled: !root.busy; onClicked: root.checkHermes() }
              }
              Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.line }
              GridLayout {
                columns: window.width < 900 ? 1 : 2
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: "Memory is optional. Hermes uses built-in memory unless you choose another provider."; color: root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(13 * root.contentScale)); wrapMode: Text.WordWrap }
                EditorialButton { text: root.memoryExpanded ? "Hide setup" : "Customize setup"; quiet: true; enabled: !root.busy; onClicked: root.memoryExpanded = !root.memoryExpanded }
              }
              GridLayout {
                columns: window.width < 900 ? 1 : 4
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                visible: root.memoryExpanded
                Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: "Choose memory for Hermes."; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(14 * root.contentScale)) }
                ComboBox { model: [{ label: "Built-in memory", value: "builtin" }, { label: "Honcho", value: "honcho" }, { label: "Hindsight", value: "hindsight" }, { label: "Defer external setup", value: "deferred" }]; textRole: "label"; currentIndex: root.memoryChoice === "builtin" ? 0 : (root.memoryChoice === "honcho" ? 1 : (root.memoryChoice === "hindsight" ? 2 : 3)); Accessible.name: "Memory for Hermes"; onActivated: root.selectMemory(model[currentIndex].value) }
                EditorialButton { text: "Open wizard"; quiet: true; visible: root.memoryChoice === "honcho" || root.memoryChoice === "hindsight"; enabled: !root.busy && root.statusFor("hermes").installed; onClicked: root.openMemoryWizard() }
                EditorialButton { text: "I finished setup"; quiet: true; visible: (root.memoryChoice === "honcho" || root.memoryChoice === "hindsight") && !root.memoryConfirmed; enabled: !root.busy; onClicked: root.confirmMemorySetup() }
              }
              GridLayout {
                columns: window.width < 900 ? 1 : 4
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                EditorialButton { text: "Back"; quiet: true; enabled: !root.busy; onClicked: root.saveStep(1) }
                Item { Layout.fillWidth: true }
                EditorialButton { text: "Choose a desktop  →"; enabled: !root.busy && root.accountChoice !== ""; onClicked: root.saveStep(3) }
                EditorialButton { text: "Finish for now"; quiet: true; enabled: !root.closingQueued; onClicked: root.finishForNow() }
              }
            }
          }

          Flickable {
            id: openView
            contentWidth: width
            contentHeight: openContent.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            ColumnLayout {
              id: openContent
              width: openView.width - Style.space(8)
              spacing: Style.space(14)
              Text { textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Give your AI\na place to open."; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.round(42 * root.contentScale); lineHeight: 1.0 }
              Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: "Desktop apps are optional. Choose one if you want a dedicated place to open your tools."; color: root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.heading, Math.round(16 * root.contentScale)); wrapMode: Text.WordWrap }
              EditorialButton {
                text: "Open " + root.statusFor(root.accountChoice).toolName
                visible: root.accountProofSufficient()
                enabled: !root.busy
                onClicked: root.runToolAction(root.accountChoice, "launch")
              }
              GridLayout {
                columns: window.width < 900 ? 1 : 2
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                Repeater {
                  model: [{ id: "hermes-desktop", title: "Hermes Desktop", copy: "A dedicated home for Hermes. Its first launch prepares the assistant for you." }, { id: "chatgpt-desktop", title: "ChatGPT Desktop", copy: "A separate desktop account experience. It does not share Hermes memory." }]
                  delegate: BorderSurface {
                    id: desktopCard
                    required property var modelData
                    property var entry: root.statusFor(modelData.id)
                    Layout.fillWidth: true
                    Layout.preferredHeight: Style.space(200)
                    color: root.desktopChoice === modelData.id ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18) : root.softSurface
                    borderSpec: Border.controlSpec(root.desktopChoice === modelData.id ? "selected" : "normal", root.foreground, root.accent)
                    radius: Style.space(10)
                    ColumnLayout {
                      anchors.fill: parent
                      anchors.margins: Style.space(18)
                      spacing: Style.space(8)
                      Text { textFormat: Text.PlainText; text: desktopCard.modelData.title + (desktopCard.modelData.id === "hermes-desktop" && root.hermesOperational === "ready" ? " · Recommended" : ""); wrapMode: Text.WordWrap; Layout.fillWidth: true; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.max(Style.font.heading, Math.round(22 * root.contentScale)) }
                      Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: desktopCard.modelData.copy; color: root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(13 * root.contentScale)); wrapMode: Text.WordWrap }
                      RowLayout {
                        Layout.fillWidth: true
                        Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: root.desktopStateLabel(desktopCard.entry); color: desktopCard.entry.runtimeState === "attention" ? root.urgent : root.subdued; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: Math.max(Style.font.body, Math.round(12 * root.contentScale)) }
                        EditorialButton {
                          id: desktopChoiceButton
                          text: root.desktopChoice === desktopCard.modelData.id ? "Selected" : "Choose"
                          quiet: root.desktopChoice !== desktopCard.modelData.id
                          Accessible.name: "Choose " + desktopCard.modelData.title
                          onClicked: root.selectDesktop(desktopCard.modelData.id)
                          Component.onCompleted: { if (desktopCard.modelData.id === "hermes-desktop") root.desktopHermesChoiceButton = desktopChoiceButton }
                        }
                      }
                    }
                  }
                }
              }
              GridLayout {
                columns: window.width < 900 ? 1 : 4
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                EditorialButton { text: root.desktopChoice === "none" ? "No desktop app" : "Use no desktop app"; quiet: root.desktopChoice !== "none"; enabled: !root.busy; onClicked: root.selectDesktop("none") }
                Item { Layout.fillWidth: true }
                EditorialButton { text: "Refresh status"; quiet: true; enabled: !root.busy; onClicked: root.refreshStatus(["hermes-desktop", "chatgpt-desktop", "hermes"]) }
                EditorialButton { visible: root.desktopChoice !== "none"; text: root.desktopActionLabel(root.statusFor(root.desktopChoice)); enabled: !root.busy && (root.statusFor(root.desktopChoice).desktopInstalled || root.statusFor(root.desktopChoice).available); onClicked: root.runToolAction(root.desktopChoice, root.statusFor(root.desktopChoice).desktopInstalled ? "open" : "install") }
              }
              Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.line }
              Text { textFormat: Text.PlainText; Layout.fillWidth: true; text: root.completionMessage(); wrapMode: Text.WordWrap; color: root.completeEligible() ? root.foreground : root.subdued; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(14 * root.contentScale)) }
              GridLayout {
                columns: window.width < 900 ? 1 : 4
                columnSpacing: Style.space(12)
                rowSpacing: Style.space(10)
                Layout.fillWidth: true
                EditorialButton { text: "Back"; quiet: true; enabled: !root.busy; onClicked: root.saveStep(2) }
                Item { Layout.fillWidth: true }
                EditorialButton { id: finishForNowButton; text: "Finish for now"; quiet: true; enabled: !root.closingQueued; onClicked: root.finishForNow() }
                EditorialButton { text: "Complete setup"; enabled: root.completeEligible() && !root.busy && !root.closingQueued; onClicked: root.completeSetup() }
              }
            }
          }
        }

        Text { textFormat: Text.PlainText; Layout.fillWidth: true; visible: root.statusText !== ""; text: root.statusText; wrapMode: Text.WordWrap; color: root.statusText.indexOf("attention") >= 0 || root.statusText.indexOf("unavailable") >= 0 ? root.urgent : root.foreground; font.family: root.fontFamily; font.pixelSize: Math.max(Style.font.body, Math.round(13 * root.contentScale)); Accessible.role: Accessible.AlertMessage; Accessible.name: root.statusText }
      }
    }
  }
}
