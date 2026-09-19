import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland

Item {
  id: root
  property var omarchyPath: null
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null
  property bool closingFromHost: false
  property bool nativePreviewFixtureMode: false
  property string page: "talk"
  property bool settingsOpen: false
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
  property bool compactControlsOpen: false
  property bool orbLongPress: false
  property bool voiceStartPending: false
  property string handledTaskErrorSignature: ""
  property string setupFocusMessage: ""
  property bool focusedOrb: false
  property bool uiTestInstrumentation: false
  property int taskDelegateCreations: 0
  property int transcriptDelegateCreations: 0
  property alias voiceController: controller

  readonly property var lockService: shell && typeof shell.serviceFor === "function" ? shell.serviceFor("omarchy.lock") : null
  readonly property bool sessionLocked: lockService ? lockService.locked === true : false
  onSessionLockedChanged: if (sessionLocked) { compactControlsOpen = false; close(); send("end_voice") }

  readonly property var voice: controller.voice || ({})
  readonly property var taskError: voice.task_error || ({})
  readonly property var settings: controller.settings || ({})
  readonly property var readiness: controller.readiness || ({})
  readonly property var transcript: (controller.session || {}).transcript || []
  readonly property var tasks: controller.visibleTasks || []
  readonly property bool reducedMotion: settings.reduced_motion === true
  readonly property bool fixedPosition: settings.fixed_position === true
  readonly property bool conversationReady: root.conversationReadiness().ready === true
  readonly property bool disabled: voice.enabled !== true && !conversationReady
  readonly property string orbState: voice.error ? "error" : (voice.state === "listening" && voice.microphone !== true ? "muted" : String(voice.state || "idle"))
  property bool controllerOpen: false
  property string heldPlacement: "right"
  property int heldDiameter: 56
  readonly property bool interactionHeld: orbButton.hovered || orbButton.down || orbButton.activeFocus || controllerOpen || compactControlsOpen
  readonly property string desiredPlacement: fixedPosition ? "right" : (conversation ? "center" : (working ? "left" : "right"))
  onDesiredPlacementChanged: if (!interactionHeld) heldPlacement = desiredPlacement
  onInteractionHeldChanged: if (!interactionHeld) { heldPlacement = desiredPlacement; heldDiameter = conversation ? 88 : 56 }
  onConversationChanged: {
    if (!interactionHeld) heldDiameter = conversation ? 88 : 56
    compactControlsOpen = conversation
  }
  readonly property bool conversation: ["connecting", "thinking", "listening", "speaking", "talking", "conversation"].indexOf(String(voice.state || "")) >= 0
  readonly property bool working: tasks.some(function(task) { return task.state !== "dismissed" && task.dismissed !== true })

  onTaskErrorChanged: {
    if (shouldHandleTaskError(taskError) && taskError.code === "PROJECT_REQUIRED") {
      page = "type"
      controllerOpen = true
      compactControlsOpen = true
      Qt.callLater(function() { projectField.forceActiveFocus() })
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
    page = "settings"
    settingsOpen = true
    controllerOpen = true
    compactControlsOpen = false
    controller.start()
    Qt.callLater(function() { connectionMode.forceActiveFocus() })
  }
  function startFromOrb() {
    if (conversation) {
      if (voice.enabled !== true) {
        requestVoiceStart()
      } else {
        controllerOpen = false
        compactControlsOpen = true
      }
      return
    }
    if (!conversationReady || voice.error) {
      openSettings(voice.error || "Maslow Voice needs attention before it can start.")
      return
    }
    requestVoiceStart()
  }
  function requestVoiceStart() {
    voiceStartPending = true
    send("start_voice", { project: selectedProject, context: explicitContext })
  }

  function stateText() {
    if (voice.error) return "Needs attention"
    if (disabled) return "Voice is off"
    if (voice.state === "connecting") return "Connecting"
    if (voice.state === "thinking") return "Thinking"
    if (voice.speaking === true || voice.state === "speaking" || voice.state === "talking") return "Speaking"
    if (voice.state === "listening") return "Listening"
    return "Ready to listen"
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
  function needsApproval(task) {
    var approval = task ? task.approval : null
    return !!(approval === true || approval === "required" || (approval && typeof approval === "object" && String(approval.request_id || "") !== ""))
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
    if (voice.state === "connecting") return "Connecting — requesting microphone access"
    if (voice.state === "listening") return voice.microphone === true ? "Listening — microphone on" : "Listening — microphone off"
    return voice.microphone === true ? "Microphone on" : "Microphone off"
  }
  function handleControlResponse(response) {
    if (voiceStartPending && response.ok === false) {
      voiceStartPending = false
      openSettings(String((response.error || {}).message || "Maslow Voice could not start. Check the setup details."))
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
      openSettings(safeMessage)
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
      page = String(payload.page)
    settingsOpen = page === "settings"
    closingFromHost = false
    controllerOpen = true
    controller.start()
    Qt.callLater(function() {
      if (root.page === "talk") talkAction.forceActiveFocus()
      else if (root.page === "type") projectField.forceActiveFocus()
      else if (root.page === "settings") connectionMode.forceActiveFocus()
      else controlsFocus.forceActiveFocus()
    })
  }
  function close() {
    closingFromHost = true
    controllerOpen = false
    if (conversation) compactControlsOpen = true
    orbButton.focus = false
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
    color: "#FFFFFF"
    placeholderTextColor: "#D1D5DB"
    font.family: "Manrope"
    font.pixelSize: 14
    leftPadding: 12
    background: Rectangle { radius: 8; color: "#1E2D47"; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? "#6DC4AD" : "#75879D" }
  }
  component VoiceArea: TextArea {
    Keys.priority: Keys.BeforeItem
    Keys.onTabPressed: function(event) { nextItemInFocusChain(true).forceActiveFocus(Qt.TabFocusReason); event.accepted = true }
    Keys.onBacktabPressed: function(event) { nextItemInFocusChain(false).forceActiveFocus(Qt.BacktabFocusReason); event.accepted = true }
    color: "#FFFFFF"
    placeholderTextColor: "#D1D5DB"
    font.family: "Manrope"
    font.pixelSize: 14
    padding: 12
    background: Rectangle { radius: 8; color: "#1E2D47"; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? "#6DC4AD" : "#75879D" }
  }
  component VoiceSelect: ComboBox {
    id: select
    implicitHeight: 44
    Layout.fillWidth: true
    font.family: "Manrope"
    font.pixelSize: 14
    leftPadding: 12
    rightPadding: 36
    palette.text: "#FFFFFF"
    palette.buttonText: "#FFFFFF"
    palette.highlightedText: "#121D35"
    palette.highlight: "#6DC4AD"
    background: Rectangle {
      radius: 8
      color: "#1E2D47"
      border.width: select.activeFocus ? 2 : 1
      border.color: select.activeFocus ? "#6DC4AD" : "#75879D"
    }
    contentItem: Text {
      text: select.displayText
      color: select.enabled ? "#FFFFFF" : "#D1D5DB"
      font: select.font
      elide: Text.ElideRight
      verticalAlignment: Text.AlignVCenter
    }
    indicator: Text {
      x: select.width - width - 12
      y: (select.height - height) / 2
      text: "\u25BE"
      color: select.enabled ? "#FFFFFF" : "#D1D5DB"
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
        color: option.highlighted ? "#121D35" : "#FFFFFF"
        font: select.font
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
      }
      background: Rectangle {
        radius: 6
        color: option.highlighted ? "#6DC4AD" : "#1E2D47"
        border.width: option.activeFocus ? 2 : 0
        border.color: "#FFFFFF"
      }
    }
    popup: Popup {
      width: select.width
      padding: 6
      implicitHeight: Math.min(contentItem.implicitHeight + 12, 264, card.height - 40)
      // Keep every option inside the controller's input region.
      y: select.mapToItem(card, 0, select.height).y + implicitHeight + 6 > card.height - 20 ? -implicitHeight - 6 : select.height + 6
      background: Rectangle { color: "#1E2D47"; radius: 8; border.color: "#6DC4AD"; border.width: 1 }
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
    implicitHeight: 44
    contentItem: Text { text: parent.text; leftPadding: parent.indicator.width + parent.spacing; color: "#FFFFFF"; font.family: "Manrope"; verticalAlignment: Text.AlignVCenter }
    background: Rectangle { color: "transparent"; radius: 6; border.width: parent.activeFocus ? 2 : 0; border.color: "#6DC4AD" }
  }

  component VoiceButton: Button {
    focusPolicy: Qt.StrongFocus
    implicitHeight: 44
    horizontalPadding: 14
    Accessible.role: Accessible.Button
    Accessible.name: text
    background: Rectangle {
      radius: 8
      opacity: parent.enabled ? 1 : 0.55
      color: parent.down ? "#A070A6" : (parent.hovered ? "#6DC4AD" : "#F6F7F9")
      border.color: parent.activeFocus ? "#247967" : "#121D35"
      border.width: parent.activeFocus ? 2 : 1
    }
    contentItem: Text {
      text: parent.text
      color: "#121D35"
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
    WlrLayershell.keyboardFocus: root.controllerOpen ? WlrKeyboardFocus.Exclusive : (root.compactControlsOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None)
    color: "transparent"
    mask: Region {
      item: orbButton
      Region { item: root.conversation && root.compactControlsOpen ? compactStrip : null; intersection: Intersection.Combine }
      Region { item: root.controllerOpen ? card : null; intersection: Intersection.Combine }
    }

    Button {
      id: orbButton
      padding: 8
      width: root.heldDiameter + 16
      height: width
      x: root.heldPlacement === "left" ? 20 : (root.heldPlacement === "center" ? (parent.width - width) / 2 : parent.width - width - 20)
      y: parent.height - height - 20
      focusPolicy: Qt.StrongFocus
      Accessible.name: "Maslow Voice, " + root.stateText() + ". Start talking or open conversation controls"
      background: Item {}
      contentItem: VoiceOrb {
        width: orbButton.width - 16; height: width
        voiceState: root.orbState
        audioLevel: root.voice.level || 0
        disabled: root.disabled
        reducedMotion: root.reducedMotion
        interactive: orbButton.hovered || orbButton.down || orbButton.activeFocus
        gpuShaderAvailable: Quickshell.env("MASLOW_VOICE_GPU_SHADER") !== "0"
      }
      onClicked: {
        if (root.orbLongPress) {
          root.orbLongPress = false
          return
        }
        root.startFromOrb()
      }
      onPressAndHold: { root.orbLongPress = true; root.openSettings("Advanced Voice settings") }
    }

    Rectangle {
      id: compactStrip
      visible: root.conversation && root.compactControlsOpen
      width: Math.min(600, panelWindow.width - 32)
      implicitHeight: compactControls.implicitHeight + 24
      x: Math.max(16, Math.min(panelWindow.width - width - 16, orbButton.x + orbButton.width / 2 - width / 2))
      y: Math.max(16, orbButton.y - height - 12)
      color: "#121D35"
      radius: 14
      border.color: "#6DC4AD"
      border.width: 1
      Accessible.role: Accessible.Pane
      Accessible.name: "Maslow Voice conversation controls"
      ColumnLayout {
        id: compactControls
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        Text { text: root.stateText() + " · " + root.microphoneText(); color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.WordWrap; Accessible.role: Accessible.StatusBar; Accessible.name: text }
        Flow {
          Layout.fillWidth: true
          spacing: 8
          VoiceButton {
            text: root.voice.microphone === true ? "Mute" : "Resume"
            onClicked: {
              if (root.voice.enabled !== true) root.requestVoiceStart()
              else root.send("mute", { muted: root.voice.microphone === true })
            }
          }
          VoiceButton { text: "End"; onClicked: { root.compactControlsOpen = false; root.send("end_voice") } }
          VoiceButton { text: "Captions"; onClicked: { root.page = "type"; root.controllerOpen = true; root.compactControlsOpen = false; Qt.callLater(function() { textDraft.forceActiveFocus() }) } }
          VoiceButton { text: "Tasks"; onClicked: { root.page = "tasks"; root.controllerOpen = true; root.compactControlsOpen = false; Qt.callLater(function() { controlsFocus.forceActiveFocus() }) } }
          VoiceButton { text: "Settings"; onClicked: root.openSettings("Advanced Voice settings") }
        }
        Text { visible: String(root.taskError.message || "") !== ""; text: String(root.taskError.message || ""); color: "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
        VoiceButton { visible: root.taskError.code === "PROJECT_REQUIRED"; text: "Choose project"; onClicked: { root.page = "type"; root.controllerOpen = true; Qt.callLater(function() { projectField.forceActiveFocus() }) } }
      }
    }

    Rectangle {
      id: card
      visible: root.controllerOpen
      width: Math.min(600, panelWindow.width - 32)
      height: Math.min(720, panelWindow.height - 16)
      x: Math.max(16, Math.min(panelWindow.width - width - 16, orbButton.x + orbButton.width / 2 - width / 2))
      y: Math.max(16, panelWindow.height - height - 136)
      color: "#121D35"
      radius: 17
      border.color: "#6DC4AD"
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
            Text { text: "MASLOW VOICE"; color: "#FFFFFF"; font.family: "Manrope"; font.weight: Font.Bold; font.pixelSize: 18; Accessible.role: Accessible.Heading; Accessible.name: "Maslow Voice" }
            Item { Layout.fillWidth: true }
            Text { text: root.stateText(); color: root.disabled ? "#D1D5DB" : "#6DC4AD"; font.family: "Manrope"; font.pixelSize: 14; Accessible.role: Accessible.StatusBar; Accessible.name: text }
            VoiceButton { text: "Close"; onClicked: root.close() }
          }
          RowLayout {
            Layout.fillWidth: true
            Repeater {
              model: [{ id: "talk", label: "Talk" }, { id: "type", label: "Type" }, { id: "tasks", label: "Tasks" }, { id: "settings", label: "Settings" }]
              delegate: VoiceButton {
                required property var modelData
                text: modelData.label
                Accessible.name: text + (root.page === modelData.id ? ", current section" : "")
                onClicked: { root.page = modelData.id; root.settingsOpen = modelData.id === "settings" }
              }
            }
          }
          Rectangle { Layout.fillWidth: true; height: 1; color: "#496078" }
          Text { visible: root.feedback !== "" || controller.transportError !== ""; text: controller.transportError || root.feedback; color: "#EE7BB3"; Layout.fillWidth: true; wrapMode: Text.Wrap; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
          StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: ["talk", "type", "tasks", "settings"].indexOf(root.page)
            Item {
              ColumnLayout {
                anchors.fill: parent
                spacing: 12
                Item { Layout.fillHeight: true }
                Text { visible: root.voice.error || controller.transportError; Layout.alignment: Qt.AlignHCenter; text: root.voice.error || controller.transportError; color: "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
                Text { Layout.alignment: Qt.AlignHCenter; text: root.conversation ? root.stateText() : "What would you like to work on?"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 24 }
                VoiceButton { id: talkAction; Layout.alignment: Qt.AlignHCenter; text: root.conversation ? "End conversation" : "Start talking"; onClicked: root.conversation ? root.send("end_voice") : root.requestVoiceStart() }
                VoiceField { Layout.fillWidth: true; placeholderText: "Project folder for tasks (optional for conversation)"; text: root.selectedProject; onTextEdited: root.selectedProject = text; Accessible.name: "Project folder" }
                Text { Layout.alignment: Qt.AlignHCenter; text: "Talk through an idea, or ask Maslow to hand work to your agents."; color: "#D1D5DB"; font.family: "Manrope"; font.pixelSize: 15; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.maximumWidth: 520 }
                Text { Layout.alignment: Qt.AlignHCenter; text: root.microphoneText() + (root.transcript.length > 0 ? "  ·  Captions: " + String(root.transcript[root.transcript.length - 1].text || "") : ""); color: "#D1D5DB"; font.family: "Manrope"; font.pixelSize: 13; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.maximumWidth: 520; Accessible.role: Accessible.StatusBar; Accessible.name: text }
                Item { Layout.fillHeight: true }
              }
            }
            ScrollView {
              id: typeScroll
              clip: true
              ScrollBar.vertical.policy: ScrollBar.AlwaysOn
              ColumnLayout {
                width: typeScroll.availableWidth - 14
                spacing: 12
                Text { text: "Send a clear request"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 22; Accessible.role: Accessible.Heading }
                Text { visible: String(root.taskError.message || "") !== ""; text: String(root.taskError.message || ""); color: "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
                VoiceField { Layout.fillWidth: true; id: projectField; placeholderText: "Project folder (required to hand off work)"; text: root.selectedProject; onTextEdited: root.selectedProject = text; Accessible.name: "Selected project" }
                VoiceArea { Layout.fillWidth: true; id: contextField; placeholderText: "Context you choose to share (optional)"; text: root.explicitContext; onTextChanged: root.explicitContext = text; Accessible.name: "Explicit context"; implicitHeight: 80; wrapMode: TextEdit.Wrap }
                VoiceArea { Layout.fillWidth: true; id: textDraft; placeholderText: "Describe the work to coordinate"; text: root.draft; onTextChanged: root.draft = text; Accessible.name: "Task request"; implicitHeight: 110; wrapMode: TextEdit.Wrap }
                Text { text: "Maslow only sends the request, project, and context you enter here. It does not capture screenshots automatically."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                VoiceButton { text: "Send request"; enabled: root.draft.trim() !== ""; onClicked: root.submitText() }
                Repeater { model: root.transcript; delegate: Text { required property var modelData; Component.onCompleted: if (root.uiTestInstrumentation) root.transcriptDelegateCreations += 1; Layout.fillWidth: true; text: (modelData.role === "user" ? "You: " : "Maslow: ") + String(modelData.text || ""); color: "#FFFFFF"; font.family: "Manrope"; wrapMode: Text.WordWrap } }
              }
            }
            ScrollView {
              id: tasksScroll
              clip: true
              ScrollBar.vertical.policy: ScrollBar.AlwaysOn
              ColumnLayout {
                width: tasksScroll.availableWidth - 14
                spacing: 12
                Text { text: "Coordinated tasks"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 22; Accessible.role: Accessible.Heading }
                Text { visible: root.tasks.length === 0; text: "No tasks are being coordinated yet."; color: "#D1D5DB"; font.family: "Manrope" }
                Repeater {
                  model: root.tasks
                  delegate: Rectangle {
                    required property var modelData
                    Component.onCompleted: if (root.uiTestInstrumentation) root.taskDelegateCreations += 1
                    Layout.fillWidth: true
                    implicitHeight: taskColumn.implicitHeight + 20
                    radius: 8; color: "#1E2D47"; border.color: "#496078"
                    ColumnLayout {
                      id: taskColumn; anchors.fill: parent; anchors.margins: 10; spacing: 7
                      Text { text: String(modelData.title || "Task"); color: "#FFFFFF"; font.family: "Manrope"; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                      Text { text: String(modelData.state || "unknown").replace(/_/g, " ") + " · " + String(modelData.result || (modelData.error || ({})).message || modelData.summary || ""); color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                      Text { visible: root.needsApproval(modelData); text: "Approval requested: " + JSON.stringify(modelData.approval || ({}), null, 2); wrapMode: Text.Wrap; Layout.fillWidth: true; color: "#EE7BB3"; font.family: "Manrope"; Accessible.role: Accessible.AlertMessage }
                      VoiceArea { id: taskInstruction; Layout.fillWidth: true; placeholderText: "Tell the agent what to change or do next"; wrapMode: TextEdit.Wrap; Accessible.name: "Instructions for " + String(modelData.title || "task") }
                      Repeater { model: (modelData.export_review || ({})).changes || []; delegate: Text { required property var modelData; text: String(modelData.action) + ": " + String(modelData.path); color: "#FFFFFF"; Layout.fillWidth: true; wrapMode: Text.Wrap } }
                      Flow { Layout.fillWidth: true; spacing: 8
                        VoiceButton { text: "Approve"; visible: root.needsApproval(modelData); enabled: !!((modelData.approval || ({})).request_id || modelData.approval_request_id); onClicked: root.taskAction(modelData, "approve") }
                        VoiceButton { text: "Deny"; visible: root.needsApproval(modelData); enabled: !!((modelData.approval || ({})).request_id || modelData.approval_request_id); onClicked: root.taskAction(modelData, "deny") }
                        VoiceButton { text: "Steer"; visible: ["accepted", "running", "waiting_input", "awaiting_approval"].indexOf(modelData.state) >= 0; enabled: taskInstruction.text.trim() !== ""; onClicked: root.taskAction(modelData, "steer", taskInstruction.text) }
                        VoiceButton { text: "Start"; visible: modelData.state === "proposed"; onClicked: root.taskAction(modelData, "start") }
                        VoiceButton { text: "Cancel"; visible: ["completed", "failed", "cancelled", "interrupted"].indexOf(modelData.state) < 0; onClicked: root.taskAction(modelData, "cancel") }
                        VoiceButton { text: "Continue"; visible: ["completed", "failed", "cancelled", "interrupted", "waiting_input"].indexOf(modelData.state) >= 0; enabled: taskInstruction.text.trim() !== ""; onClicked: root.taskAction(modelData, "continue", taskInstruction.text) }
                        VoiceButton { text: "Review changes"; visible: modelData.mode === "offline" && ["completed", "failed", "cancelled", "interrupted"].indexOf(modelData.state) >= 0; onClicked: root.taskAction(modelData, "review") }
                        VoiceButton { text: "Export reviewed changes"; visible: !!(modelData.export_review || ({})).digest; onClicked: root.taskAction(modelData, "export") }
                        VoiceButton { text: "Dismiss"; visible: ["completed", "failed", "cancelled", "interrupted"].indexOf(modelData.state) >= 0; onClicked: root.taskAction(modelData, "dismiss") }
                      }
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
                Text { text: "Advanced Voice settings"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 22; Accessible.role: Accessible.Heading }
                Text { visible: root.setupFocusMessage !== ""; text: root.setupFocusMessage; color: "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.AlertMessage; Accessible.name: text }
                VoiceSelect { id: connectionMode; Layout.fillWidth: true; model: ["Maslow Voice", "Offline on this computer", "Your model server", "OpenAI Realtime", "GPT-Live cloud", "LiveKit Expressive"]; currentIndex: ["gemini_live", "offline", "server", "openai", "gpt_live", "livekit"].indexOf(root.settings.mode || "gemini_live"); Accessible.name: "Voice connection"; onActivated: root.configure("mode", ["gemini_live", "offline", "server", "openai", "gpt_live", "livekit"][currentIndex]) }
                ColumnLayout { visible: ["offline", "server"].indexOf(root.settings.mode) >= 0; Layout.fillWidth: true
                  VoiceSelect { visible: root.settings.mode === "server"; model: ["Ollama", "LM Studio"]; currentIndex: root.settings.server_kind === "lmstudio" ? 1 : 0; Accessible.name: "Model server type"; onActivated: root.configure("server_kind", currentIndex === 1 ? "lmstudio" : "ollama") }
                Text { visible: root.settings.mode === "server"; text: "Model server address"; color: "#D1D5DB"; font.family: "Manrope" }
                  VoiceField { visible: root.settings.mode === "server"; Layout.fillWidth: true; placeholderText: "Model server address (local or remote)"; text: String(root.settings.server_url || ""); Accessible.name: "Model server address"; onEditingFinished: root.configure("server_url", text) }
                Text { visible: root.settings.mode === "offline"; text: "Ollama models folder"; color: "#D1D5DB"; font.family: "Manrope" }
                  VoiceField { visible: root.settings.mode === "offline"; Layout.fillWidth: true; placeholderText: "Ollama models folder"; text: String(root.settings.ollama_models || ""); Accessible.name: "Ollama models folder"; onEditingFinished: root.configure("ollama_models", text) }
                Text { visible: true; text: "Speech models folder"; color: "#D1D5DB"; font.family: "Manrope" }
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
                  Text { text: "Maslow Voice setup"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                  Text { text: "Maslow Voice uses Gemini Live with Google AI Studio. LiveKit details save optional Expressive mode setup. Credentials stay in this computer's keyring."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  Text { text: "LiveKit project URL (optional Expressive mode)"; color: "#FFFFFF"; font.family: "Manrope" }
                  VoiceField { id: geminiLiveUrlField; Layout.fillWidth: true; placeholderText: "wss://your-project.livekit.cloud (optional)"; text: String(root.settings.livekit_url || ""); Accessible.name: "Maslow Voice optional LiveKit project URL" }
                  Text { text: "LiveKit API credentials"; color: "#FFFFFF"; font.family: "Manrope" }
                  RowLayout { Layout.fillWidth: true; spacing: 8
                    VoiceField { id: geminiLiveApiKeyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API key"; Accessible.name: "Maslow Voice LiveKit API key" }
                    VoiceField { id: geminiLiveApiSecretField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API secret"; Accessible.name: "Maslow Voice LiveKit API secret" }
                  }
                  Text { text: "Google AI Studio API key"; color: "#FFFFFF"; font.family: "Manrope" }
                  VoiceField { id: geminiLiveGoogleApiKeyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "Google AI Studio API key"; Accessible.name: "Google AI Studio API key" }
                  Text { text: "LiveKit fields are optional and blank fields keep saved values. Add a Google key for first-time setup; leave it blank to keep a saved key."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  VoiceButton { text: root.geminiLiveSetupSaving ? "Saving Maslow Voice setup…" : "Save Maslow Voice setup"; enabled: !root.geminiLiveSetupSaving; onClicked: root.submitGeminiLiveSetup(geminiLiveUrlField.text, geminiLiveApiKeyField.text, geminiLiveApiSecretField.text, geminiLiveGoogleApiKeyField.text) }
                  Text { visible: root.geminiLiveSetupStatus !== ""; text: root.geminiLiveSetupStatus; color: root.geminiLiveSetupSucceeded ? "#6DC4AD" : "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: root.geminiLiveSetupSucceeded ? Accessible.StatusBar : Accessible.AlertMessage; Accessible.name: text }
                  Text { visible: root.conversation; text: "End the conversation before changing Maslow Voice settings."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                ColumnLayout {
                  visible: root.settings.mode === "livekit"
                  Layout.fillWidth: true
                  spacing: 8
                  Text { text: "LiveKit setup"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                  Text { text: "Enter your project URL and API credentials."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  Text { text: "Project URL"; color: "#FFFFFF"; font.family: "Manrope" }
                  VoiceField { id: livekitUrlField; Layout.fillWidth: true; placeholderText: "wss://your-project.livekit.cloud"; text: String(root.settings.livekit_url || ""); Accessible.name: "LiveKit project URL" }
                  Text { text: "API credentials"; color: "#FFFFFF"; font.family: "Manrope" }
                  RowLayout { Layout.fillWidth: true; spacing: 8
                    VoiceField { id: livekitApiKeyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API key"; Accessible.name: "LiveKit API key" }
                    VoiceField { id: livekitApiSecretField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "API secret"; Accessible.name: "LiveKit API secret" }
                  }
                  Text { text: "Blank fields keep saved values."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  VoiceButton { text: root.livekitSetupSaving ? "Saving LiveKit setup…" : "Save LiveKit setup"; enabled: !root.livekitSetupSaving; onClicked: root.submitLiveKitSetup(livekitUrlField.text, livekitApiKeyField.text, livekitApiSecretField.text) }
                  Text { visible: root.livekitSetupStatus !== ""; text: root.livekitSetupStatus; color: root.livekitSetupSucceeded ? "#6DC4AD" : "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: root.livekitSetupSucceeded ? Accessible.StatusBar : Accessible.AlertMessage; Accessible.name: text }
                  RowLayout { Layout.fillWidth: true; spacing: 10
                    Text { text: "Voice"; color: "#FFFFFF"; font.family: "Manrope" }
                    VoiceSelect { Layout.fillWidth: true; enabled: !root.conversation; model: ["Ashley", "Edward", "Olivia", "Alex", "Dennis"]; currentIndex: model.indexOf(String(root.settings.livekit_voice || "Ashley")); Accessible.name: "LiveKit voice"; onActivated: root.configure("livekit_voice", currentText) }
                  }
                  Text { visible: root.conversation; text: "End the conversation before choosing a different voice."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                ColumnLayout {
                  visible: root.settings.mode === "gpt_live"
                  Layout.fillWidth: true
                  spacing: 8
                  Text { text: "GPT-Live cloud"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                  Text { text: "Talk naturally, even while Maslow is speaking. It uses your saved OpenAI API key."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                  Text { text: "Voice"; color: "#FFFFFF"; font.family: "Manrope" }
                  VoiceSelect { Layout.fillWidth: true; enabled: !root.conversation; model: ["cedar", "marin", "alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse", "quartz", "ripple", "vesper", "willow", "stone", "gleam", "meridian", "bossa", "tempo", "beacon", "delta", "cinder"]; currentIndex: model.indexOf(String(root.settings.live_voice || "marin")); Accessible.name: "GPT-Live voice"; onActivated: root.configure("live_voice", currentText) }
                  Text { visible: root.conversation; text: "End the conversation before choosing a different voice."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                Text { visible: root.settings.mode === "openai"; text: "OpenAI voice model"; color: "#D1D5DB"; font.family: "Manrope" }
                VoiceField { visible: root.settings.mode === "openai"; Layout.fillWidth: true; placeholderText: "OpenAI voice model"; text: String(root.settings.realtime_model || ""); Accessible.name: "OpenAI voice model"; onEditingFinished: root.configure("realtime_model", text) }
                Text { visible: root.settings.mode === "openai"; text: "Voice"; color: "#FFFFFF"; font.family: "Manrope" }
                VoiceSelect { visible: root.settings.mode === "openai"; enabled: !root.conversation; model: ["cedar", "marin", "alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"]; currentIndex: model.indexOf(String(root.settings.realtime_voice || "cedar")); Accessible.name: "OpenAI Realtime voice"; onActivated: root.configure("realtime_voice", currentText) }
                Text { visible: root.settings.mode === "openai" && root.conversation; text: "End the conversation before choosing a different voice."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; text: "Credentials are stored privately on this computer."; color: "#D1D5DB"; font.family: "Manrope" }
                VoiceSelect { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; model: ["OpenAI API key", "Model server token", "Anthropic API key"]; Accessible.name: "Credential type"; onActivated: root.credentialName = ["openai", "server_token", "anthropic"][currentIndex] }
                VoiceField { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "Paste credential"; text: root.credentialValue; onTextEdited: root.credentialValue = text; Accessible.name: "Credential" }
                VoiceButton { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; text: "Save credential"; enabled: root.credentialValue !== ""; onClicked: root.submitCredential() }
                VoiceSelect { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0; model: ["Automatic routing", "Codex", "Claude Code", "Hermes"]; currentIndex: ["auto", "codex", "claude", "hermes"].indexOf(root.settings.default_coder || "auto"); Accessible.name: "Default coding agent"; onActivated: root.configure("default_coder", ["auto", "codex", "claude", "hermes"][currentIndex]) }
                Text { visible: root.settings.mode === "gpt_live"; text: "Set up Hermes in Hub before sending tasks. Codex and Claude also need their own connections when selected."; color: "#D1D5DB"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                VoiceField { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) < 0 && (["offline", "server"].indexOf(root.settings.mode) >= 0 || root.settings.default_coder === "claude"); Layout.fillWidth: true; placeholderText: "Task model (optional)"; text: String(root.settings.execution_model || ""); Accessible.name: "Task model"; onEditingFinished: root.configure("execution_model", text) }
                VoiceButton { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) >= 0; text: root.advancedTaskSettingsOpen ? "Hide task settings" : "Task settings"; onClicked: root.advancedTaskSettingsOpen = !root.advancedTaskSettingsOpen }
                ColumnLayout { visible: ["livekit", "gemini_live"].indexOf(root.settings.mode) >= 0 && root.advancedTaskSettingsOpen; Layout.fillWidth: true; spacing: 8
                  Text { text: "Task settings"; color: "#FFFFFF"; font.family: "Manrope"; font.pixelSize: 18; Accessible.role: Accessible.Heading }
                  VoiceSelect { model: ["Automatic routing", "Codex", "Claude Code", "Hermes"]; currentIndex: ["auto", "codex", "claude", "hermes"].indexOf(root.settings.default_coder || "auto"); Accessible.name: "Default coding agent"; onActivated: root.configure("default_coder", ["auto", "codex", "claude", "hermes"][currentIndex]) }
                  VoiceSelect { visible: root.settings.mode === "gemini_live"; model: ["Start explicit tasks in Voice Lab", "Review task before starting"]; currentIndex: root.settings.task_policy === "review" ? 1 : 0; Accessible.name: "Task start policy"; onActivated: root.configure("task_policy", currentIndex === 1 ? "review" : "lab_auto") }
                  VoiceField { visible: root.settings.default_coder === "claude"; Layout.fillWidth: true; placeholderText: "Task model (optional)"; text: String(root.settings.execution_model || ""); Accessible.name: "Task model"; onEditingFinished: root.configure("execution_model", text) }
                }
                VoiceButton { text: root.settings.mode === "openai" ? "Check setup" : "Check connection and readiness"; onClicked: root.send("test") }
                VoiceCheck { text: "Reduce voice motion"; checked: root.reducedMotion; onToggled: root.configure("reduced_motion", checked); Accessible.name: text }
                VoiceCheck { text: "Keep orb at a fixed position"; checked: root.fixedPosition; onToggled: root.configure("fixed_position", checked); Accessible.name: text }
                VoiceField { Layout.fillWidth: true; placeholderText: "Display name or connector"; text: String(settings.display || ""); Accessible.name: "Voice display"; onEditingFinished: root.configure("display", text) }
                Text { text: "Conversation readiness: " + (root.conversationReadiness().ready === true ? "Ready" : "Needs attention"); color: root.conversationReadiness().ready === true ? "#6DC4AD" : "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.StatusBar; Accessible.name: text }
                Repeater { model: root.conversationReadiness().checks || []; delegate: Text { required property var modelData; text: (modelData.ok === true ? "Ready: " : "Needs attention: ") + String(modelData.name || "Check") + " — " + String(modelData.message || ""); color: modelData.ok === true ? "#6DC4AD" : "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true } }
                Text { text: "Task readiness: " + (root.taskReadiness().ready === true ? "Ready" : "Needs attention"); color: root.taskReadiness().ready === true ? "#6DC4AD" : "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true; Accessible.role: Accessible.StatusBar; Accessible.name: text }
                Repeater { model: root.taskReadiness().checks || []; delegate: Text { required property var modelData; text: (modelData.ok === true ? "Ready: " : "Needs attention: ") + String(modelData.name || "Check") + " — " + String(modelData.message || ""); color: modelData.ok === true ? "#6DC4AD" : "#EE7BB3"; font.family: "Manrope"; wrapMode: Text.WordWrap; Layout.fillWidth: true } }
              }
            }
          }
        }
      }
    }
  }
}
