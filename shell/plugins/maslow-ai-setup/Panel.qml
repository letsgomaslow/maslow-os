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
  property string statusText: ""
  property string activeTool: ""
  property string activeAction: ""
  property string statusTool: ""
  property bool busy: false
  property bool canFinish: false
  property bool stateCatalogLoaded: false
  property bool stateLoaded: false
  property bool adapterCatalogLoaded: false
  property bool statusChecksComplete: false
  property bool statusChecksFailed: false
  property bool closingQueued: false
  property var statusQueue: []
  property var stateWriteQueue: []
  property var stateWriteCurrent: null
  property string productName: ""
  property string productTagline: ""

  readonly property color foreground: Color.foreground
  readonly property color background: Color.background
  readonly property color accent: Color.accent
  readonly property color urgent: Color.urgent
  readonly property string fontFamily: "Manrope"

  ListModel { id: toolModel }

  function focusCurrentStep() {
    Qt.callLater(function() {
      if (!window.visible) return
      switch (root.step) {
        case 1: continueButton.forceActiveFocus(); break
        case 2: toolsView.forceActiveFocus(); break
        case 3: finishButton.forceActiveFocus(); break
      }
    })
  }

  function ensureToolVisible(card) {
    Qt.callLater(function() {
      var viewport = toolsView.contentItem
      if (!viewport || !card) return
      var top = card.mapToItem(viewport.contentItem, 0, 0).y
      var bottom = top + card.height
      var nextY = viewport.contentY
      if (top < nextY) nextY = top
      else if (bottom > nextY + viewport.height) nextY = bottom - viewport.height
      viewport.contentY = Math.max(0, Math.min(nextY, Math.max(0, viewport.contentHeight - viewport.height)))
    })
  }

  function open(payloadJson) {
    closingFromHost = false
    closingQueued = false
    canFinish = false
    stateCatalogLoaded = false
    stateLoaded = false
    adapterCatalogLoaded = false
    statusChecksComplete = false
    statusChecksFailed = false
    statusQueue = []
    statusText = ""
    window.visible = true
    root.focusCurrentStep()
    stateCatalogProc.running = true
    adapterCatalogProc.running = true
    stateProc.command = ["omarchy-setup-ai-state", "open"]
    stateProc.running = true
    productProc.running = true
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
    if (closingQueued) return
    step = next
    root.focusCurrentStep()
    queueStateWrite(["omarchy-setup-ai-state", "step", String(next)])
  }

  function findTool(toolId) {
    for (var index = 0; index < toolModel.count; index++) {
      if (toolModel.get(index).toolId === toolId) return index
    }
    return -1
  }

  function applyState(state) {
    step = Math.max(1, Math.min(3, Number(state.currentStep || 1)))
    var tools = state.tools || {}
    for (var toolId in tools) {
      var index = findTool(toolId)
      if (index < 0) continue
      toolModel.setProperty(index, "selected", tools[toolId].selected === true)
      toolModel.setProperty(index, "toolStatus", String(tools[toolId].status || "not-started"))
    }
    updateCompletionState()
    root.focusCurrentStep()
  }

  function applyAdapterCatalog(catalog) {
    if (toolModel.count === 0) return
    statusChecksComplete = false
    statusChecksFailed = false
    var tools = catalog.tools || []
    var queue = []
    for (var i = 0; i < tools.length; i++) {
      var entry = tools[i]
      var index = findTool(String(entry.id || ""))
      if (index < 0) continue
      toolModel.setProperty(index, "adapterSupported", entry.supported === true)
      toolModel.setProperty(index, "planned", entry.planned === true)
      toolModel.setProperty(index, "setupOnly", entry.setupOnly === true)
      toolModel.setProperty(index, "userConfirmable", entry.userConfirmable === true)
      if (entry.setupOnly === true || String(entry.id) === "memory-builtin") {
        toolModel.setProperty(index, "prerequisiteInstalled", false)
        toolModel.setProperty(index, "installSupported", false)
        toolModel.setProperty(index, "openSupported", false)
      }
      if (entry.supported !== true) continue
      if (entry.setupOnly === true || String(entry.id) === "memory-builtin") continue
      queue.push(String(entry.id))
    }
    statusQueue = queue
    checkNextToolStatus()
  }

  function checkNextToolStatus() {
    if (statusProc.running) return
    if (statusQueue.length === 0) {
      statusChecksComplete = stateCatalogLoaded && adapterCatalogLoaded && !statusChecksFailed
      updateCompletionState()
      return
    }
    var queue = statusQueue.slice()
    statusTool = String(queue.shift())
    statusQueue = queue
    statusProc.command = ["omarchy-setup-ai-tool", "status", statusTool]
    statusProc.running = true
  }

  function toggleTool(toolId, selected) {
    var index = findTool(toolId)
    if (index < 0 || busy || closingQueued) return
    toolModel.setProperty(index, "selected", selected)
    var nextStatus = selected ? (toolModel.get(index).openSupported ? "action-required" : "selected") : "not-started"
    toolModel.setProperty(index, "toolStatus", nextStatus)
    if (selected && (toolId === "honcho" || toolId === "hindsight")) {
      var otherProvider = toolId === "honcho" ? "hindsight" : "honcho"
      var otherIndex = findTool(otherProvider)
      if (otherIndex >= 0) {
        toolModel.setProperty(otherIndex, "selected", false)
        toolModel.setProperty(otherIndex, "toolStatus", "not-started")
      }
    }
    updateCompletionState()
    queueStateWrite(["omarchy-setup-ai-state", "tool-select", toolId, selected ? "true" : "false"])
    if (nextStatus === "action-required") queueStateWrite(["omarchy-setup-ai-state", "tool-status", toolId, nextStatus])
  }

  function runToolAction(toolId, action) {
    var index = findTool(toolId)
    if (index < 0 || busy || closingQueued) return
    var item = toolModel.get(index)
    if ((action === "install" && !item.installSupported) || (action === "open" && !item.openSupported)) return
    busy = true
    activeTool = toolId
    activeAction = action
    if (toolId === "hermes") updateHermesDependents(false)
    statusText = action === "install" ? (isCoreTool(toolId) ? "Opening the repair flow…" : "Opening setup…") : "Opening the tool…"
    toolModel.setProperty(index, "selected", true)
    toolModel.setProperty(index, "toolStatus", "in-progress")
    updateCompletionState()
    queueStateWrite(["omarchy-setup-ai-state", "tool-status", toolId, "in-progress"], false, toolId, action)
  }

  function statusLabel(status) {
    switch (status) {
      case "selected": return "Selected"
      case "in-progress": return "In progress"
      case "action-required": return "Complete the action shown, then confirm"
      case "ready": return "Ready"
      case "needs-attention": return "Needs attention — retry available"
      case "skipped": return "Skipped"
      default: return "Not selected"
    }
  }

  function toolDescription(toolId) {
    switch (toolId) {
      case "bitwarden": return "Get your passwords and SSH keys ready before AI setup."
      case "codex": return "Tested starter coding agent from OpenAI. Sign-in happens in Codex; Maslow OS does not inspect authentication."
      case "claude": return "Tested starter coding agent from Anthropic. Sign-in happens in Claude Code; Maslow OS does not inspect authentication."
      case "hermes": return "Tested starter agent harness with built-in memory. Launch it to check the local tool."
      case "memory-builtin": return "Hermes uses this by default. No extra provider is required."
      case "honcho": return "Optional external memory provider. Choose this or Hindsight, not both."
      case "hindsight": return "Optional external memory provider. Choose this or Honcho, not both."
      case "mcp": return "MCP connections are set up separately for each agent."
      case "speech": return "Optional desktop speech support will be guided in a later version."
      default: return "Optional setup item."
    }
  }

  function isCoreTool(toolId) {
    return toolId === "bitwarden" || toolId === "codex" || toolId === "claude" || toolId === "hermes"
  }

  function primaryActionLabel(toolId, setupOnly, status) {
    if (status === "needs-attention") return "Retry"
    if (isCoreTool(toolId)) return "Repair"
    if (setupOnly) return "Configure"
    return "Check"
  }

  function openActionLabel(toolId, setupOnly, status) {
    if (status === "in-progress" || status === "needs-attention") return "Retry"
    if (setupOnly) return "Configure"
    if (toolId === "codex" || toolId === "claude") return "Sign in"
    if (toolId === "hermes") return "Launch & check"
    if (toolId === "memory-builtin") return "Check"
    return "Open"
  }

  function availabilityLabel(toolId, planned, setupOnly, prerequisiteInstalled, installSupported, openSupported, status, reasonCode) {
    if (toolId === "memory-builtin") return openSupported ? "Included with Hermes" : "Set up Hermes first"
    if (planned) return "Guided setup planned"
    if (reasonCode === "path-shadow") return "Command override needs attention"
    if (isCoreTool(toolId) && !openSupported) return "Core software missing — repair required"
    if (setupOnly && !prerequisiteInstalled) return "Set up Hermes first"
    if (!installSupported && !openSupported) return "Unavailable on this system"
    if (!setupOnly && status === "ready" && !openSupported) return "Installation needs attention"
    return statusLabel(status)
  }

  function updateHermesDependents(installed) {
    for (var index = 0; index < toolModel.count; index++) {
      var item = toolModel.get(index)
      if (!item.setupOnly && item.toolId !== "memory-builtin") continue
      toolModel.setProperty(index, "prerequisiteInstalled", installed)
      toolModel.setProperty(index, "installSupported", item.setupOnly && installed)
      toolModel.setProperty(index, "openSupported", installed)
    }
  }

  function updateCompletionState() {
    var complete = true
    for (var index = 0; index < toolModel.count; index++) {
      var item = toolModel.get(index)
      if (item.adapterSupported && item.selected && (item.toolStatus !== "ready" || (item.setupOnly ? !item.prerequisiteInstalled : !item.openSupported))) complete = false
    }
    canFinish = stateCatalogLoaded && stateLoaded && adapterCatalogLoaded && statusChecksComplete && complete
  }

  function markReady(toolId) {
    var index = findTool(toolId)
    if (index < 0) return
    var item = toolModel.get(index)
    if (!item.adapterSupported || (item.setupOnly && !item.prerequisiteInstalled) || (!item.openSupported && !item.userConfirmable)) return
    toolModel.setProperty(index, "selected", true)
    toolModel.setProperty(index, "toolStatus", "ready")
    updateCompletionState()
    statusText = "Marked ready. Maslow OS saved only your confirmation, not any account details."
    queueStateWrite(["omarchy-setup-ai-state", "tool-status", toolId, "ready"])
  }

  function queueStateWrite(command, closeAfterWrite, launchTool, launchAction) {
    if (closingQueued && closeAfterWrite !== true) return
    if (closeAfterWrite === true) closingQueued = true
    var queue = stateWriteQueue.slice()
    queue.push({
      command: command,
      closeAfterWrite: closeAfterWrite === true,
      launchTool: String(launchTool || ""),
      launchAction: String(launchAction || "")
    })
    stateWriteQueue = queue
    startNextStateWrite()
  }

  function startNextStateWrite() {
    if (stateWriteProc.running || stateWriteCurrent !== null || stateWriteQueue.length === 0) return
    var queue = stateWriteQueue.slice()
    stateWriteCurrent = queue.shift()
    stateWriteQueue = queue
    stateWriteProc.command = stateWriteCurrent.command
    stateWriteProc.running = true
  }

  function deferSetup() {
    if (closingQueued) return
    queueStateWrite(["omarchy-setup-ai-state", "defer"], true)
  }

  function finishSetup() {
    if (busy || closingQueued || !stateCatalogLoaded || !stateLoaded || !adapterCatalogLoaded || !statusChecksComplete) return
    queueStateWrite(["omarchy-setup-ai-state", canFinish ? "complete" : "defer"], true)
  }

  function retryStatusChecks() {
    if (busy || closingQueued || !adapterCatalogOutput.text) return
    statusChecksFailed = false
    statusText = "Checking tool status again…"
    try { applyAdapterCatalog(JSON.parse(adapterCatalogOutput.text)) }
    catch (e) { statusText = "Tool status could not be checked. You can retry." }
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
    id: stateCatalogProc
    command: ["omarchy-setup-ai-state", "catalog"]
    stdout: StdioCollector { id: stateCatalogOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.statusText = "The setup list could not be loaded."
        return
      }
      try {
        var catalog = JSON.parse(stateCatalogOutput.text)
        toolModel.clear()
        for (var i = 0; i < catalog.tools.length; i++) {
          var item = catalog.tools[i]
          toolModel.append({
            toolId: String(item.id),
            toolName: String(item.name),
            toolKind: String(item.kind),
            selected: false,
            toolStatus: "not-started",
            installSupported: false,
            openSupported: false,
            adapterSupported: false,
            planned: true,
            setupOnly: false,
            userConfirmable: false,
            prerequisiteInstalled: false,
            reasonCode: "",
            toolDescription: root.toolDescription(String(item.id))
          })
        }
        root.stateCatalogLoaded = true
        if (stateOutput.text) root.applyState(JSON.parse(stateOutput.text))
        if (adapterCatalogOutput.text) root.applyAdapterCatalog(JSON.parse(adapterCatalogOutput.text))
      } catch (e) {
        root.statusText = "The setup list could not be read."
      }
    }
  }

  Process {
    id: adapterCatalogProc
    command: ["omarchy-setup-ai-tool", "catalog"]
    stdout: StdioCollector { id: adapterCatalogOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) return
      try {
        root.adapterCatalogLoaded = true
        root.applyAdapterCatalog(JSON.parse(adapterCatalogOutput.text))
      }
      catch (e) { root.statusText = "Tool actions are unavailable right now." }
    }
  }

  Process {
    id: stateProc
    stdout: StdioCollector { id: stateOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.statusText = "AI setup progress needs attention."
        return
      }
      try {
        root.stateLoaded = true
        root.applyState(JSON.parse(stateOutput.text))
      }
      catch (e) { root.statusText = "AI setup progress could not be read." }
    }
  }

  Process {
    id: statusProc
    stdout: StdioCollector { id: toolStatusOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode === 0) {
        try {
          var result = JSON.parse(toolStatusOutput.text)
          if (result.id !== root.statusTool || result.supported !== true || typeof result.available !== "boolean" || typeof result.installed !== "boolean" || typeof result.prerequisiteInstalled !== "boolean") throw new Error("Invalid tool status")
          var index = root.findTool(String(result.id || ""))
          if (index >= 0 && result.supported === true) {
            var setupOnly = result.setupOnly === true
            var prerequisiteInstalled = result.prerequisiteInstalled === true
            var reasonCode = String(result.reasonCode || "")
            toolModel.setProperty(index, "prerequisiteInstalled", prerequisiteInstalled)
            toolModel.setProperty(index, "reasonCode", reasonCode)
            toolModel.setProperty(index, "installSupported", reasonCode !== "path-shadow" && result.available === true && result.installed !== true && (!setupOnly || prerequisiteInstalled))
            toolModel.setProperty(index, "openSupported", result.installed === true || (setupOnly && prerequisiteInstalled))
            if (result.installed === true) {
              var previousStatus = String(toolModel.get(index).toolStatus)
              if (toolModel.get(index).selected && (previousStatus === "not-started" || previousStatus === "selected")) {
                toolModel.setProperty(index, "toolStatus", "action-required")
                root.queueStateWrite(["omarchy-setup-ai-state", "tool-status", String(result.id), "action-required"])
              }
            }
            if (String(result.id) === "hermes") root.updateHermesDependents(result.installed === true)
            root.updateCompletionState()
          }
        } catch (e) {
          if (root.statusTool === "hermes") root.updateHermesDependents(false)
          root.statusChecksFailed = true
          root.statusText = "One tool status could not be read. You can retry from its card."
        }
      } else {
        if (root.statusTool === "hermes") root.updateHermesDependents(false)
        root.statusChecksFailed = true
        root.statusText = "One tool status could not be checked. You can retry."
      }
      root.checkNextToolStatus()
    }
  }

  Process {
    id: stateWriteProc
    onExited: function(exitCode) {
      var completedWrite = root.stateWriteCurrent
      root.stateWriteCurrent = null
      if (exitCode !== 0) {
        root.statusText = "Could not save AI setup progress. You can retry."
        root.busy = false
        root.stateWriteQueue = []
        root.closingQueued = false
        return
      }
      if (completedWrite && completedWrite.launchTool !== "") {
        root.activeTool = completedWrite.launchTool
        root.activeAction = completedWrite.launchAction
        actionProc.command = ["omarchy-setup-ai-tool", root.activeAction, root.activeTool]
        actionProc.running = true
      }
      if (completedWrite && completedWrite.closeAfterWrite) {
        root.stateWriteQueue = []
        root.requestClose()
        return
      }
      root.startNextStateWrite()
    }
  }

  Process {
    id: actionProc
    onExited: function(exitCode) {
      var index = root.findTool(root.activeTool)
      root.busy = false
      if (index < 0) return
      if (exitCode === 130) {
        toolModel.setProperty(index, "toolStatus", "selected")
        root.statusText = "Canceled. Your selection was kept."
        root.queueStateWrite(["omarchy-setup-ai-state", "tool-status", root.activeTool, "selected"])
      } else if (exitCode !== 0) {
        toolModel.setProperty(index, "toolStatus", "needs-attention")
        root.statusText = "This step needs attention. You can retry safely."
        root.queueStateWrite(["omarchy-setup-ai-state", "tool-status", root.activeTool, "needs-attention"])
      } else {
        var item = toolModel.get(index)
        var nextStatus = item.setupOnly && item.userConfirmable ? "action-required" : "selected"
        toolModel.setProperty(index, "toolStatus", nextStatus)
        root.statusText = item.setupOnly && item.userConfirmable ? "The official setup was opened. Mark ready only after you finish it." : (root.activeAction === "install" ? (root.isCoreTool(root.activeTool) ? "The repair flow was opened. When it finishes, use Check again." : "Setup was opened. When it finishes, use Check again.") : "The tool was opened. Authentication is not inspected; complete the action shown, then mark ready.")
        root.queueStateWrite(["omarchy-setup-ai-state", "tool-status", root.activeTool, nextStatus])
        if (!item.setupOnly) {
          root.statusChecksComplete = false
          root.statusQueue = [root.activeTool]
        }
      }
      root.updateCompletionState()
      if (exitCode === 0 && !toolModel.get(index).setupOnly) root.checkNextToolStatus()
    }
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
          id: productHeader
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
            Text { text: root.productName; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: 24 }
            Text { text: root.productTagline; textFormat: Text.PlainText; color: Qt.darker(root.foreground, 1.3); font.family: root.fontFamily; font.pixelSize: 14 }
          }
        }

        Row {
          id: progressHeader
          width: parent.width
          spacing: Style.space(8)
          Repeater {
            model: 3
            Rectangle {
              required property int index
              width: (parent.width - Style.space(16)) / 3
              height: 4
              radius: 2
              color: index + 1 <= root.step ? root.accent : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.18)
            }
          }
        }

        StackLayout {
          id: setupSteps
          width: parent.width
          height: Math.max(0, parent.height - productHeader.height - progressHeader.height - parent.spacing * 2
            - (feedbackText.visible ? feedbackText.height + parent.spacing : 0)
            - (statusRefreshButton.visible ? statusRefreshButton.height + parent.spacing : 0))
          currentIndex: root.step - 1

          Column {
            spacing: Style.space(18)
            Text { text: "Welcome to " + root.productName; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: 28 }
            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: "Core AI tools come with Maslow OS. Choose which ones you want to configure; sign-in happens separately in the supported tools."
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: 16
            }
            Item { width: 1; height: Style.space(12) }
            Button { id: continueButton; text: "Continue"; focusable: true; enabled: !root.closingQueued; Accessible.name: "Continue to AI tool setup"; onClicked: root.saveStep(2) }
            Button { text: "Not now"; focusable: true; enabled: !root.closingQueued; Accessible.name: "Stop opening AI setup automatically"; onClicked: root.deferSetup() }
          }

          Column {
            spacing: Style.space(12)
            Text { text: "Set up your AI workspace"; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: 28 }
            Text { width: parent.width; wrapMode: Text.WordWrap; text: "Start with Bitwarden for secure readiness, then choose Codex, Claude Code, or Hermes. Sign-in stays in Codex and Claude Code; Maslow OS does not inspect authentication."; color: root.foreground; font.family: root.fontFamily; font.pixelSize: 15 }

            ScrollView {
              id: toolsView
              width: parent.width
              // Hidden step Columns use implicit height until laid out. Their
              // child must measure the stack, not feed back into that height.
              height: Math.max(0, setupSteps.height - 150)
              focus: true
              Accessible.name: "AI setup checklist"
              clip: true

              Column {
                width: toolsView.availableWidth
                spacing: Style.space(8)
                Repeater {
                  model: toolModel
                  Rectangle {
                    id: toolCard
                    required property string toolId
                    required property string toolName
                    required property bool selected
                    required property string toolStatus
                    required property bool installSupported
                    required property bool openSupported
                    required property bool adapterSupported
                    required property bool planned
                    required property bool setupOnly
                    required property bool userConfirmable
                    required property bool prerequisiteInstalled
                    required property string reasonCode
                    required property string toolDescription
                    width: parent.width
                    height: 82
                    radius: 8
                    color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, selected ? 0.11 : 0.06)
                    border.color: selected ? root.accent : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.16)

                    RowLayout {
                      anchors.fill: parent
                      anchors.margins: Style.space(10)
                      spacing: Style.space(10)
                      CheckBox {
                        checked: selected
                        onActiveFocusChanged: if (activeFocus) root.ensureToolVisible(toolCard)
                        enabled: !root.busy && !root.closingQueued && adapterSupported && (selected || installSupported || openSupported)
                        Accessible.name: (checked ? "Remove " : "Select ") + toolName
                        Accessible.description: toolDescription
                        onClicked: root.toggleTool(toolId, checked)
                      }
                      ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: toolName; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: 15 }
                        Text {
                          text: root.availabilityLabel(toolId, planned, setupOnly, prerequisiteInstalled, installSupported, openSupported, toolStatus, reasonCode)
                          textFormat: Text.PlainText
                          color: toolStatus === "needs-attention" ? root.urgent : Qt.darker(root.foreground, 1.25)
                          font.family: root.fontFamily
                          font.pixelSize: 13
                        }
                      }
                      Button {
                        focusable: true
                        onActiveFocusChanged: if (activeFocus) root.ensureToolVisible(toolCard)
                        visible: toolCard.selected && installSupported && toolStatus !== "action-required" && (!setupOnly || toolStatus !== "ready")
                        text: root.primaryActionLabel(toolId, setupOnly, toolStatus)
                        enabled: !root.busy && !root.closingQueued
                        Accessible.name: text + " " + toolName
                        onClicked: root.runToolAction(toolId, "install")
                      }
                      Button {
                        focusable: true
                        onActiveFocusChanged: if (activeFocus) root.ensureToolVisible(toolCard)
                        visible: toolCard.selected && openSupported && (toolStatus === "in-progress" || toolStatus === "action-required" || toolStatus === "ready" || toolStatus === "needs-attention")
                        text: root.openActionLabel(toolId, setupOnly, toolStatus)
                        enabled: !root.busy && !root.closingQueued
                        Accessible.name: text + " " + toolName
                        onClicked: root.runToolAction(toolId, "open")
                      }
                      Button {
                        focusable: true
                        onActiveFocusChanged: if (activeFocus) root.ensureToolVisible(toolCard)
                        visible: toolCard.selected && (!setupOnly || prerequisiteInstalled) && (openSupported || userConfirmable) && toolStatus === "action-required"
                        text: "Mark ready"
                        enabled: !root.busy && !root.closingQueued
                        Accessible.name: "Mark " + toolName + " ready after completing the action shown"
                        onClicked: root.markReady(toolId)
                      }
                    }
                  }
                }
              }
            }

            Row {
              spacing: Style.space(10)
              Button { text: "Back"; focusable: true; enabled: !root.busy && !root.closingQueued; onClicked: root.saveStep(1) }
              Button { text: "Review"; focusable: true; enabled: !root.busy && !root.closingQueued; Accessible.name: "Review AI setup progress"; onClicked: root.saveStep(3) }
              Button { text: "Finish later"; focusable: true; enabled: !root.busy && !root.closingQueued; Accessible.name: "Save progress and finish later"; onClicked: root.deferSetup() }
            }
          }

          Column {
            spacing: Style.space(14)
            Text { text: "Your setup summary"; color: root.foreground; font.family: root.fontFamily; font.weight: Font.DemiBold; font.pixelSize: 28 }
            Text { width: parent.width; wrapMode: Text.WordWrap; text: "Ready means you completed the action shown and confirmed it; it does not prove provider authentication. Hermes uses built-in memory. External memory and MCP connections stay separate."; color: root.foreground; font.family: root.fontFamily; font.pixelSize: 15 }
            ScrollView {
              width: parent.width
              height: Math.max(0, setupSteps.height - 150)
              clip: true
              Column {
                width: parent.width
                spacing: Style.space(8)
                Repeater {
                  model: toolModel
                  Text {
                    required property string toolId
                    required property string toolName
                    required property bool selected
                    required property string toolStatus
                    required property bool planned
                    required property bool setupOnly
                    required property bool prerequisiteInstalled
                    required property bool installSupported
                    required property bool openSupported
                    required property string reasonCode
                    visible: selected || toolStatus === "skipped"
                    text: toolName + " — " + root.availabilityLabel(toolId, planned, setupOnly, prerequisiteInstalled, installSupported, openSupported, toolStatus, reasonCode)
                    textFormat: Text.PlainText
                    color: toolStatus === "needs-attention" ? root.urgent : root.foreground
                    font.family: root.fontFamily
                    font.pixelSize: 15
                  }
                }
              }
            }
            Row {
              spacing: Style.space(10)
              Button { text: "Back"; focusable: true; enabled: !root.closingQueued; onClicked: root.saveStep(2) }
              Button {
                id: finishButton
                text: root.canFinish ? "Finish" : "Finish later"
                focusable: true
                enabled: !root.busy && !root.closingQueued && root.stateCatalogLoaded && root.stateLoaded && root.adapterCatalogLoaded && root.statusChecksComplete
                Accessible.name: root.canFinish ? "Finish AI setup" : "Save incomplete AI setup and finish later"
                onClicked: root.finishSetup()
              }
            }
          }
        }

        Text {
          id: feedbackText
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
        Button {
          id: statusRefreshButton
          focusable: true
          visible: root.stateCatalogLoaded && root.adapterCatalogLoaded && root.step > 1
          text: root.statusChecksFailed ? "Retry checks" : "Check again"
          enabled: !root.busy && !root.closingQueued
          Accessible.name: "Retry AI tool status checks"
          onClicked: root.retryStatusChecks()
        }
      }
    }
  }
}
