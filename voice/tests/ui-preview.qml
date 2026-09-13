import QtQuick
import Quickshell
import Quickshell.Io
import "../ui" as Voice

ShellRoot {
  QtObject { id: fixtureLock; property bool locked: false }
  QtObject { id: fixtureShell; function serviceFor(pluginId) { return pluginId === "omarchy.lock" ? fixtureLock : null } }
  Voice.Panel {
    id: panel
    shell: fixtureShell
    nativePreviewFixtureMode: true
    Component.onCompleted: voiceController.setFixture({
      schemaVersion: 1,
      voice: { enabled: false, state: "disabled", microphone: false, speaking: false, level: 0, error: "" },
      settings: { mode: "offline", server_kind: "ollama", server_url: "http://127.0.0.1:11434", model: "qwen3:8b", default_coder: "codex", reduced_motion: false, fixed_position: false, display: "", ollama_models: "/home/maslow/.ollama/models", speech_directory: "/home/maslow/.local/share/maslow-voice/speech" },
      tasks: [], session: { id: "fixture", transcript: [] },
      readiness: { ready: true, checks: [{ name: "Speech models", ok: true, message: "Available on this computer." }], models: [{ id: "qwen3:8b", label: "Qwen 3 · 8B" }] }
    })
  }
  IpcHandler {
    target: "voice-fixture"
    function page(value: string): void { panel.open(JSON.stringify({ page: value })) }
    function close(): void { panel.close() }
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
    function lock(value: string): void { fixtureLock.locked = value === "true" }
    function preference(key: string, value: string): void {
      var next = JSON.parse(JSON.stringify(panel.voiceController.snapshot))
      next.settings[key] = value === "true" ? true : (value === "false" ? false : value)
      panel.voiceController.setFixture(next)
    }
    function requests(): string { return JSON.stringify(panel.voiceController.fixtureRequests) }
    function status(): string { return JSON.stringify({ placement: panel.heldPlacement, diameter: panel.heldDiameter, desired: panel.desiredPlacement, controllerOpen: panel.controllerOpen, state: panel.voice.state }) }
  }
}
