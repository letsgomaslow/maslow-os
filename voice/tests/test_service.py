import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.ipc import ControlServer


class FakeProvider:
    def __init__(self, config, secrets, emit, submit, transport):
        self.emit, self.submit = emit, submit
        self.started = False
    async def start(self, audio=True):
        self.started = True
        await self.emit({"type": "voice_state", "state": "listening", "microphone": audio})
    async def stop(self):
        self.started = False
    async def text(self, text, context):
        await self.emit({"type": "transcript", "role": "user", "text": text, "final": True, "turn_id": "turn-" + text})


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.credentials = AsyncMock()
        self.credentials.get.return_value = "test-secret-never-echo"
        self.service = VoiceService(self.root / "state", self.root / "runtime", provider_factory=FakeProvider, credentials=self.credentials)
        self.service.tasks._start = lambda task: None

    async def asyncTearDown(self):
        await self.service.end_voice()
        self.service.store.close()
        self.temporary.cleanup()

    async def test_typed_session_never_enables_microphone_and_voice_off_preserves_task(self):
        await self.service.dispatch({"action": "submit_text", "text": "Fix tests", "project": str(self.project)})
        self.assertFalse(self.service.voice["enabled"])
        self.assertFalse(self.service.voice["microphone"])
        brief = {"objective": "Fix tests", "summary": "Repair failing tests", "constraints": [], "requested_output": "Passing tests", "tool_preference": "auto", "unresolved_questions": []}
        first = await self.service.submit_intent(brief, "turn-Fix tests")
        second = await self.service.submit_intent(brief, "turn-Fix tests")
        self.assertEqual(first["id"], second["id"])
        await self.service.end_voice()
        self.assertEqual(self.service.session["transcript"], [])
        self.assertEqual(len(self.service.store.list()), 1)
        self.assertNotIn("test-secret-never-echo", json.dumps(self.service.snapshot()))

    async def test_provider_cannot_override_project_mode_or_permissions(self):
        with self.assertRaises(VoiceError):
            await self.service.dispatch({"action": "submit_text", "text": "hello", "command": "anything"})
        with self.assertRaises(VoiceError):
            await self.service.submit_intent({"objective": "bad", "summary": "bad", "project": "/tmp"})
        self.assertEqual(self.service.store.list(), [])

    async def test_delayed_intent_uses_its_original_turn_and_rejects_after_off(self):
        await self.service.dispatch({"action": "submit_text", "text": "Fix first", "project": str(self.project)})
        provider = self.service.provider
        await self.service.dispatch({"action": "submit_text", "text": "Explain second", "project": str(self.project)})
        brief = {"objective": "Fix first", "summary": "Repair the first request"}
        handed = await provider.submit(brief, "turn-Fix first")
        saved = self.service.store.get(handed["id"])
        self.assertEqual(saved["source"], "Fix first")
        self.assertEqual(saved["project"], str(self.project.resolve()))
        await self.service.end_voice()
        await self.service.dispatch({"action": "submit_text", "text": "New conversation", "project": str(self.project)})
        with self.assertRaises(VoiceError):
            await provider.submit(brief, "turn-Fix first")
        self.assertEqual(len(self.service.store.list()), 1)

    async def test_active_conversation_cannot_switch_project_for_pending_intent(self):
        await self.service.dispatch({"action": "submit_text", "text": "Fix first", "project": str(self.project)})
        other = self.root / "other"
        other.mkdir()
        with self.assertRaisesRegex(VoiceError, "End this conversation"):
            await self.service.dispatch({"action": "submit_text", "text": "Second", "project": str(other)})
        self.assertEqual(self.service.project, str(self.project.resolve()))

    async def test_unidentified_or_untranscribed_turn_never_hands_off(self):
        await self.service.dispatch({"action": "submit_text", "text": "Fix first", "project": str(self.project)})
        with self.assertRaises(VoiceError):
            await self.service.submit_intent({"objective": "Fix first", "summary": "Fix it"}, "not-transcribed")
        self.assertEqual(self.service.store.list(), [])

    async def test_private_duplex_socket_delivers_snapshot_and_rejects_unknown_action(self):
        control = ControlServer(self.root / "test.sock", self.service.dispatch, self.service.snapshot, peer_check=lambda writer: True)
        await control.start()
        try:
            reader, writer = await asyncio.open_unix_connection(str(control.path))
            writer.write(b'{"action":"watch"}\n')
            await writer.drain()
            self.assertEqual(json.loads(await reader.readline())["schemaVersion"], 1)
            writer.write(b'{"action":"execute","command":"bad"}\n')
            await writer.drain()
            self.assertFalse(json.loads(await reader.readline())["ok"])
            self.assertEqual(control.path.stat().st_mode & 0o777, 0o600)
            writer.close()
            await writer.wait_closed()
        finally:
            await control.close()

    async def test_offline_model_discovery_needs_no_selected_model_or_runtime(self):
        models = self.root / "models"
        manifest = models / "manifests/registry.ollama.ai/library/small/latest"
        manifest.parent.mkdir(parents=True)
        manifest.write_text('{}')
        self.service.settings.update({"mode": "offline", "ollama_models": str(models), "model": ""})
        result = await self.service.dispatch({"action": "models"})
        self.assertEqual(result["readiness"]["models"], [{"id": "small:latest", "label": "small:latest"}])
        self.assertFalse(result["readiness"]["ready"])
        self.assertIsNone(self.service.offline)

    async def test_restart_can_review_private_files_without_starting_model(self):
        from maslow_voice.offline import OfflineWorkspace
        original = self.project / "example.txt"
        original.write_text("original")
        workspace = OfflineWorkspace(self.service.directory / "offline/workspace-test", str(self.project))
        (workspace.project / "example.txt").write_text("private edit")
        task = await self.service.tasks.submit("saved", {"objective": "Edit file", "summary": "Edit file"}, str(self.project.resolve()), "offline", "Edit file", "auto")
        self.service.store.update(task["id"], state="completed")
        await self.service.dispatch({"action": "task_action", "id": task["id"], "operation": "review"})
        review = self.service.store.get(task["id"])["export_review"]
        self.assertEqual(review["changes"], [{"path": "example.txt", "action": "modify"}])
        self.assertIsNone(self.service.offline.process)
        self.assertIsNone(self.service.offline.display)
        self.assertEqual(original.read_text(), "original")
