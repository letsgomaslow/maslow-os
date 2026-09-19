import QtQuick
import Quickshell
import Quickshell.Io
import "../ui" as Voice

ShellRoot {
  property int meterFramesRemaining: 0
  property int meterTick: 0
  QtObject { id: fixtureLock; property bool locked: false }
  QtObject { id: fixtureShell; function serviceFor(pluginId) { return pluginId === "omarchy.lock" ? fixtureLock : null } }
  Voice.Panel {
    id: panel
    shell: fixtureShell
    nativePreviewFixtureMode: true
    uiTestInstrumentation: true
    Component.onCompleted: voiceController.setFixture({
      schemaVersion: 1,
      voice: { enabled: false, state: "disabled", microphone: false, speaking: false, level: 0, error: "" },
      settings: { mode: "gemini_live", livekit_url: "wss://your-project.livekit.cloud", gemini_live_model: "gemini-3.8-live", gemini_live_voice: "Puck", livekit_voice: "Ashley", realtime_voice: "cedar", live_voice: "marin", server_kind: "ollama", server_url: "http://127.0.0.1:11434", model: "qwen3:8b", default_coder: "auto", task_policy: "lab_auto", reduced_motion: false, fixed_position: false, display: "", ollama_models: "/home/maslow/.ollama/models", speech_directory: "/home/maslow/.local/share/maslow-voice/speech" },
      tasks: [], session: { id: "fixture", transcript: [] },
      readiness: { ready: true, checks: [{ name: "Speech models", ok: true, message: "Available on this computer." }], conversation: { ready: true, checks: [{ name: "Maslow Voice connection", ok: true, message: "Available on this computer." }] }, tasks: { ready: true, checks: [{ name: "Automatic routing", ok: true, message: "A coding agent will be selected for each task." }] }, models: [{ id: "qwen3:8b", label: "Qwen 3 · 8B" }] }
    })
  }
  Timer {
    id: meterTimer
    interval: 50
    repeat: true
    onTriggered: {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      meterTick += 1
      next.voice.enabled = true
      next.voice.state = "listening"
      next.voice.microphone = true
      next.voice.level = (meterTick % 5 + 1) / 5
      panel.voiceController.setFixture(next)
      meterFramesRemaining -= 1
      if (meterFramesRemaining <= 0) meterTimer.stop()
    }
  }
  IpcHandler {
    target: "voice-fixture"
    function page(value: string): void { panel.open(JSON.stringify({ page: value })) }
    function close(): void { panel.close() }
    function compact(): void { panel.compactControlsOpen = true }
    function state(value: string): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.voice.state = value
      next.voice.enabled = value !== "disabled"
      next.voice.microphone = value === "listening"
      next.voice.speaking = value === "speaking"
      next.voice.level = value === "speaking" ? 0.7 : 0.2
      panel.voiceController.setFixture(next)
    }
    function mode(value: string): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.settings.mode = value
      panel.voiceController.setFixture(next)
    }
    function tasks(): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.tasks = [{ id: "fixture", title: "Update the welcome screen", state: "completed", mode: "offline", result: "The welcome copy is ready for your review.", export_review: { digest: "fixture-digest", changes: [{ path: "README.md", action: "modify" }, { path: "welcome.txt", action: "add" }] } }, { id: "approval", title: "Publish the reviewed update", state: "awaiting_approval", mode: "server", approval: { request_id: "fixture-approval", action: "Publish changes", destination: "Project repository", detail: "Push the reviewed welcome copy to the project branch." } }]
      panel.voiceController.setFixture(next)
    }
    function taskError(code: string, message: string): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.voice.task_error = { code: code, message: message }
      panel.voiceController.setFixture(next)
    }
    function stressPrepare(): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.tasks = []
      for (var index = 0; index < 30; index++) {
        next.tasks.push({
          id: "history-" + index,
          title: "Historical acceptance task " + index,
          state: "completed",
          mode: "gpt_live",
          result: "Completed fixture task " + index,
          approval: index === 0 ? { request_id: "approval-0", detail: "Review this fixture approval." } : null,
          children: [{ id: "child-" + index, result: "Completed child fixture " + index }],
        })
      }
      next.session = { id: "stress-session", transcript: [{ role: "user", text: "First fixture caption." }, { role: "assistant", text: "Second fixture caption." }] }
      panel.voiceController.setFixture(next)
      panel.open(JSON.stringify({ page: "tasks" }))
      Qt.callLater(function() {
        panel.taskDelegateCreations = 0
        panel.transcriptDelegateCreations = 0
      })
    }
    function stressMeters(frames: int): void {
      meterFramesRemaining = frames
      meterTick = 0
      meterTimer.restart()
    }
    function stressTaskChange(): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.tasks[0].approval.detail = "Changed approval content without a timestamp change."
      panel.voiceController.setFixture(next)
    }
    function stressSessionChange(): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.session.transcript.push({ role: "assistant", text: "Changed fixture caption." })
      panel.voiceController.setFixture(next)
    }
    function lock(value: string): void { fixtureLock.locked = value === "true" }
    function preference(key: string, value: string): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.settings[key] = value === "true" ? true : (value === "false" ? false : value)
      panel.voiceController.setFixture(next)
    }
    function requests(): string { return JSON.stringify(panel.voiceController.fixtureRequests) }
    function setupSaved(): void { panel.voiceController.applyLine('{"ok":true,"livekit_saved":true}') }
    function setupError(): void { panel.voiceController.applyLine('{"ok":false,"error":{"message":"LiveKit setup could not be saved. Check the project URL and try again."}}') }
    function status(): string { return JSON.stringify({ placement: panel.heldPlacement, diameter: panel.heldDiameter, desired: panel.desiredPlacement, controllerOpen: panel.controllerOpen, compactControlsOpen: panel.compactControlsOpen, state: panel.voice.state }) }
    function stressStatus(): string { return JSON.stringify({ taskDelegateCreations: panel.taskDelegateCreations, transcriptDelegateCreations: panel.transcriptDelegateCreations, meterFramesRemaining: meterFramesRemaining, meterLevel: panel.voice.level, taskApproval: panel.tasks[0] ? panel.tasks[0].approval.detail : "", captions: panel.transcript.length }) }
  }
}
