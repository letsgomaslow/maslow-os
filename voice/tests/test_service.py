import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.ipc import ControlServer
from maslow_voice.hermes import HermesClient
from maslow_voice.audio import PcmFrame
from maslow_voice.providers.openai_live import OpenAILiveProvider


class FakeProvider:
    def __init__(self, config, secrets, emit, submit, transport):
        self.emit, self.submit = emit, submit
        self.config, self.transport = config, transport
        self.context_updates = []
        self.started = False
    async def start(self, audio=True):
        self.started = True
        await self.emit({"type": "voice_state", "state": "listening", "microphone": audio})
    async def stop(self):
        self.started = False
    async def text(self, text, context):
        await self.emit({"type": "transcript", "role": "user", "text": text, "final": True, "turn_id": "turn-" + text})
    async def append_context(self, kind, content, delegation_id=None):
        self.context_updates.append((kind, content, delegation_id))


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

    def livekit_credentials(self, initial=None):
        values = dict(initial or {})
        async def get(name):
            return values.get(name, "")
        async def save(name, value):
            values[name] = value
        async def delete(name):
            values.pop(name, None)
        self.credentials.get.side_effect = get
        self.credentials.set.side_effect = save
        self.credentials.delete.side_effect = delete
        return values

    async def test_livekit_setup_ack_requires_saved_complete_connection_and_hides_values(self):
        values = self.livekit_credentials()
        result = await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid/",
                                              "api_key": "private-project-key", "api_secret": "private-project-secret"})
        self.assertEqual(result, {"livekit_saved": True})
        self.assertEqual(values, {"livekit_key": "private-project-key", "livekit_secret": "private-project-secret"})
        self.assertEqual(self.service.settings.value["mode"], "livekit")
        self.assertEqual(self.service.settings.value["livekit_url"], "wss://voice.invalid")
        public = json.dumps(self.service.snapshot()) + self.service.settings.path.read_text()
        self.assertNotIn("private-project-key", public)
        self.assertNotIn("private-project-secret", public)

    async def test_livekit_blank_credentials_keep_existing_values(self):
        values = self.livekit_credentials({"livekit_key": "saved-key", "livekit_secret": "saved-secret"})
        result = await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "", "api_secret": " "})
        self.assertTrue(result["livekit_saved"])
        self.credentials.set.assert_not_called()
        self.assertEqual(values["livekit_secret"], "saved-secret")

    async def test_livekit_invalid_or_incomplete_setup_does_not_interrupt_conversation(self):
        self.livekit_credentials()
        await self.service.dispatch({"action": "submit_text", "text": "hello"})
        provider = self.service.provider
        before = dict(self.service.settings.value)
        for fields in ({"url": "http://voice.invalid", "api_key": "key", "api_secret": "secret"},
                       {"url": "wss://voice.invalid", "api_key": "key", "api_secret": ""},
                       {"url": "wss://voice.invalid", "api_key": None, "api_secret": "secret"}):
            with self.assertRaises(VoiceError):
                await self.service.dispatch({"action": "configure_livekit", **fields})
            self.assertIs(self.service.provider, provider)
            self.assertEqual(self.service.settings.value, before)
            self.credentials.set.assert_not_called()

    async def test_livekit_second_write_failure_restores_both_credentials_and_settings(self):
        original = {"livekit_key": "old-key", "livekit_secret": "old-secret"}
        values = self.livekit_credentials(original)
        before = dict(self.service.settings.value)
        async def fail_second(name, value):
            values[name] = value
            if value == "new-secret":
                raise VoiceError("KEYRING_LOCKED", "Unlock the desktop keyring.")
        self.credentials.set.side_effect = fail_second
        with self.assertRaises(VoiceError):
            await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "new-key", "api_secret": "new-secret"})
        self.assertEqual(values, original)
        self.assertEqual(self.service.settings.value, before)

    async def test_livekit_settings_write_failure_removes_new_credentials(self):
        values = self.livekit_credentials()
        before = dict(self.service.settings.value)
        with patch.object(self.service.settings, "update", side_effect=OSError("write denied")):
            with self.assertRaises(OSError):
                await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "new-key", "api_secret": "new-secret"})
        self.assertEqual(values, {})
        self.assertEqual(self.service.settings.value, before)

    async def test_livekit_cancelled_save_restores_credentials_before_returning(self):
        original = {"livekit_key": "old-key", "livekit_secret": "old-secret"}
        values = self.livekit_credentials(original)
        async def cancel_second(name, value):
            values[name] = value
            if value == "new-secret":
                raise asyncio.CancelledError()
        self.credentials.set.side_effect = cancel_second
        with self.assertRaises(asyncio.CancelledError):
            await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "new-key", "api_secret": "new-secret"})
        self.assertEqual(values, original)

    async def test_livekit_rollback_verifies_removal_and_reports_incomplete_restore(self):
        self.livekit_credentials()
        self.credentials.delete.side_effect = None
        with patch.object(self.service.settings, "update", side_effect=OSError("write denied")):
            with self.assertRaises(VoiceError) as caught:
                await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "new-key", "api_secret": "new-secret"})
        self.assertEqual(caught.exception.code, "LIVEKIT_RESTORE_FAILED")
        self.assertNotIn("new-secret", caught.exception.message)

    async def test_livekit_valid_setup_ends_existing_conversation_and_revokes_old_turn(self):
        self.livekit_credentials()
        await self.service.dispatch({"action": "submit_text", "text": "hello"})
        provider = self.service.provider
        await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "key", "api_secret": "secret"})
        self.assertIsNone(self.service.provider)
        self.assertFalse(provider.started)
        with self.assertRaises(VoiceError):
            await provider.submit({"objective": "Late", "summary": "Late"}, "turn-hello")

    async def test_livekit_active_task_blocks_credential_and_settings_writes(self):
        self.livekit_credentials()
        with patch.object(self.service.store, "active", return_value=[{"id": "active"}]):
            with self.assertRaisesRegex(VoiceError, "Finish or stop"):
                await self.service.dispatch({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "key", "api_secret": "secret"})
        self.credentials.set.assert_not_called()

    async def test_explicit_audio_start_unmutes_existing_audio_conversation(self):
        await self.service.dispatch({"action": "start_voice"})
        provider = self.service.provider
        provider.mute = AsyncMock()
        await self.service.dispatch({"action": "start_voice"})
        self.assertIs(self.service.provider, provider)
        provider.mute.assert_awaited_once_with(False)

    async def test_livekit_save_ack_is_top_level_on_actual_ipc_wire(self):
        self.livekit_credentials()
        control = ControlServer(self.root / "save.sock", self.service.dispatch, self.service.snapshot, peer_check=lambda writer: True)
        await control.start()
        try:
            reader, writer = await asyncio.open_unix_connection(str(control.path))
            writer.write(json.dumps({"action": "configure_livekit", "url": "wss://voice.invalid", "api_key": "key", "api_secret": "secret"}).encode() + b"\n")
            await writer.drain()
            self.assertEqual(json.loads(await reader.readline()), {"ok": True, "livekit_saved": True})
            writer.close()
            await writer.wait_closed()
        finally:
            await control.close()

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

    async def test_gpt_live_delegation_uses_bounded_fragments_and_task_survives_audio_stop(self):
        self.service.settings.update({"mode": "gpt_live", "default_coder": "codex"})
        await self.service.dispatch({"action": "start_voice", "project": str(self.project)})
        provider = self.service.provider
        await self.service.provider_event({"type": "transcript_delta", "role": "user", "delta": "Create ", "start_ms": 10, "end_ms": 20})
        await self.service.provider_event({"type": "transcript_delta", "role": "user", "delta": "a harmless note.", "start_ms": 20, "end_ms": 40})
        await self.service.provider_event({"type": "delegation", "delegation_id": "delegation-1", "offset_ms": 40})
        await self.service.provider_event({"type": "delegation", "delegation_id": "delegation-1", "offset_ms": 40})
        for _ in range(40):
            if self.service.store.list():
                break
            await asyncio.sleep(.01)
        task = self.service.store.list()[0]
        self.assertEqual(task["mode"], "gpt_live")
        self.assertEqual(task["brief"]["tool_preference"], "codex")
        self.assertIn("Create a harmless note", task["source"])
        self.assertEqual(self.service.live_delegations["delegation-1"], task["id"])
        self.assertEqual(len(self.service.store.list()), 1)
        self.assertTrue(any(update[0] == "thinking" and update[2] == "delegation-1" for update in provider.context_updates))
        await self.service.end_voice()
        await asyncio.sleep(.3)
        self.assertEqual(self.service.store.get(task["id"])["state"], "queued")

    async def test_gpt_live_typed_task_does_not_open_audio_or_live_connection(self):
        self.service.settings.update({"mode": "gpt_live", "default_coder": "hermes"})
        result = await self.service.dispatch({"action": "submit_text", "text": "Create a harmless note", "project": str(self.project)})
        self.assertIsNone(self.service.provider)
        self.assertFalse(self.service.voice["microphone"])
        task = self.service.store.get(result["task"]["id"])
        self.assertEqual(task["brief"]["tool_preference"], "hermes")
        self.assertEqual(task["source"], "User transcript: Create a harmless note")

    async def test_live_task_relay_contains_safe_context_failure_and_preserves_task(self):
        task = await self.service.tasks.submit(
            "relay-context-failure",
            {"objective": "Write a note", "summary": "Write a harmless note", "constraints": [],
             "requested_output": "A note", "tool_preference": "hermes", "unresolved_questions": []},
            str(self.project), "gpt_live", "User transcript: Write a harmless note", "hermes",
        )
        task = self.service.store.update(task["id"], state="completed", result="The note was verified.")
        provider = FakeProvider(None, None, None, None, None)
        provider.append_context = AsyncMock(side_effect=VoiceError("OPENAI_SESSION_FAILED", "Safe connection failure"))
        epoch = self.service.provider_epoch = object()
        self.service.provider = provider

        relay = self.service.background(self.service._relay_live_task(provider, epoch, task["id"]))
        await asyncio.wait_for(relay, 1)

        self.assertIsNone(relay.exception())
        self.assertEqual(self.service.store.get(task["id"])["state"], "completed")
        self.assertEqual(self.service.store.get(task["id"])["result"], "The note was verified.")

    async def test_gpt_live_cancel_words_cancel_existing_task_without_creating_another(self):
        self.service.settings.update({"mode": "gpt_live", "default_coder": "hermes"})
        first = await self.service.dispatch({
            "action": "submit_text", "text": "Create a harmless note", "project": str(self.project),
        })
        result = await self.service.dispatch({
            "action": "submit_text", "text": "Cancel that task.", "project": str(self.project),
        })
        self.assertEqual(result["task"]["id"], first["task"]["id"])
        self.assertEqual(result["task"]["state"], "cancelled")
        self.assertEqual(len(self.service.store.list()), 1)
        self.assertIsNone(self.service.provider)

    async def test_gpt_live_reports_conversation_and_task_readiness_separately(self):
        self.service.settings.update({"mode": "gpt_live", "default_coder": "codex"})
        self.service.hermes.model_config = AsyncMock(return_value=({"provider": "openai-api", "default": "gpt-5-mini"}, {}))
        with patch("maslow_voice.daemon.shutil.which", side_effect=lambda name: "/usr/bin/" + name):
            result = await self.service.dispatch({"action": "test"})
        readiness = result["readiness"]
        self.assertTrue(readiness["conversation"]["ready"])
        self.assertTrue(readiness["tasks"]["ready"])
        self.assertTrue(readiness["ready"])
        self.service.hermes.model_config.assert_awaited_once_with("gpt_live")

    async def test_audio_transport_factory_can_supply_installed_integration_transport(self):
        transport = object()
        factory = Mock(return_value=transport)
        self.service.audio_transport_factory = factory
        await self.service.dispatch({"action": "start_voice"})
        self.assertIs(self.service.provider.transport, transport)
        factory.assert_called_once_with(microphone_device="", speaker_device="", on_error=unittest.mock.ANY)

    async def test_blocked_level_watcher_does_not_block_gpt_live_input_or_outlive_close(self):
        class Socket:
            def __init__(self):
                self.inbox = asyncio.Queue()
                self.sent = []
            async def send(self, raw):
                event = json.loads(raw)
                self.sent.append(event)
                if event["type"] == "session.start":
                    self.inbox.put_nowait(json.dumps({"type": "session.started"}))
                elif event["type"] == "session.close":
                    self.inbox.put_nowait(json.dumps({"type": "session.closed", "reason": "close_requested"}))
            async def recv(self):
                return await self.inbox.get()
            async def close(self):
                pass

        class Audio:
            def __init__(self):
                self.handler = None
                self.stop_count = 0
            async def start(self, handler):
                self.handler = handler
            async def set_muted(self, _muted):
                pass
            async def stop(self):
                self.stop_count += 1
            async def play(self, _frame):
                pass
            async def wait_playback(self):
                pass
            async def clear_playback(self):
                pass

        socket, audio = Socket(), Audio()
        async def socket_factory(*_args):
            return socket
        def provider_factory(config, secrets, emit, submit, transport):
            return OpenAILiveProvider(
                config=dict(config, socket_factory=socket_factory, live_close_timeout=.02),
                secrets=secrets, emit=emit, submit=submit, audio_transport=transport)
        self.service.provider_factory = provider_factory
        self.service.audio_transport_factory = lambda **_kwargs: audio
        self.service.settings.update({"mode": "gpt_live"})
        await self.service.dispatch({"action": "start_voice", "project": str(self.project)})

        publish_entered = asyncio.Event()
        snapshots = []
        async def blocked_publish():
            snapshots.append(self.service.snapshot())
            if len(snapshots) == 1:
                publish_entered.set()
                await asyncio.Event().wait()
        self.service.control.publish = blocked_publish

        frame = PcmFrame(b"\x10\x00" * 960, 48000)
        await audio.handler(frame)
        await asyncio.wait_for(publish_entered.wait(), .5)
        publisher = self.service.level_publish_task
        for _ in range(40):
            await asyncio.wait_for(audio.handler(frame), .1)
            self.assertIs(self.service.level_publish_task, publisher)
        self.assertEqual(self.service.provider.metrics_snapshot()["input_packets"], 41)
        self.assertEqual(sum(task is publisher for task in self.service.work), 1)

        await asyncio.wait_for(self.service.end_voice(), 1)
        await asyncio.sleep(.06)
        self.assertIsNone(self.service.provider)
        self.assertIsNone(self.service.level_publish_task)
        self.assertFalse(self.service.level_publish_dirty)
        self.assertEqual(snapshots[-1]["voice"]["state"], "disabled")
        self.assertFalse(snapshots[-1]["voice"]["microphone"])
        self.assertEqual(snapshots[-1]["voice"]["level"], 0)
        self.assertEqual(len(snapshots), 2)

    async def test_level_updates_coalesce_to_latest_value(self):
        snapshots = []
        async def publish():
            snapshots.append(self.service.snapshot())
        self.service.control.publish = publish
        await self.service.provider_event({"type": "level", "level": .1})
        publisher = self.service.level_publish_task
        await self.service.provider_event({"type": "level", "level": .4})
        await self.service.provider_event({"type": "level", "level": .7})
        self.assertIs(self.service.level_publish_task, publisher)
        self.assertEqual(snapshots, [])
        await asyncio.sleep(.07)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["voice"]["level"], .7)

    async def test_remote_provider_close_detaches_conversation_but_preserves_task(self):
        await self.service.dispatch({"action": "start_voice", "project": str(self.project)})
        provider = self.service.provider
        task = await self.service.tasks.submit(
            "remote-close-task", {"objective": "Keep working", "summary": "Keep working"},
            str(self.project), "openai", "Keep working", "codex")
        await self.service.provider_event({"type": "closed", "reason": "expired", "finalized": True})
        for _ in range(20):
            if self.service.provider is None and not provider.started:
                break
            await asyncio.sleep(.01)
        self.assertIsNone(self.service.provider)
        self.assertFalse(provider.started)
        self.assertFalse(self.service.voice["microphone"])
        self.assertEqual(self.service.store.get(task["id"])["state"], "queued")

    async def test_gpt_live_cleanup_uses_provider_close_handshake_budget(self):
        provider = Mock(cleanup_timeout=25, audio_transport=None)
        provider.stop = AsyncMock()
        with patch("maslow_voice.daemon.asyncio.wait_for", wraps=asyncio.wait_for) as wait_for:
            await self.service._release_provider(provider)
        self.assertEqual(wait_for.call_args.args[1], 25)

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

    async def test_active_projectless_conversation_accepts_first_project_and_clears_resolved_error(self):
        await self.service.dispatch({"action": "submit_text", "text": "Hello"})
        provider = self.service.provider
        await self.service.provider_event({"type": "task_error", "code": "PROJECT_REQUIRED", "message": "Choose a project."})
        self.assertEqual(self.service.voice["task_error"]["code"], "PROJECT_REQUIRED")
        await self.service.dispatch({"action": "submit_text", "text": "Create the page", "project": str(self.project)})
        self.assertIs(self.service.provider, provider)
        self.assertEqual(self.service.project, str(self.project.resolve()))
        self.assertNotIn("task_error", self.service.voice)
        self.assertEqual(self.service.turns["turn-Hello"]["project"], "")
        self.assertEqual(self.service.turns["turn-Create the page"]["project"], str(self.project.resolve()))
        other = self.root / "other"
        other.mkdir()
        with self.assertRaises(VoiceError) as caught:
            await self.service.dispatch({"action": "submit_text", "text": "Change project", "project": str(other)})
        self.assertEqual(caught.exception.code, "SESSION_PROJECT_FIXED")
        self.assertIs(self.service.provider, provider)

    async def test_task_error_survives_current_failure_but_clears_on_success_and_session_end(self):
        await self.service.dispatch({"action": "submit_text", "text": "Create a page", "project": str(self.project)})
        failure = {"type": "task_error", "code": "AGENT_UNAVAILABLE", "message": "Finish agent setup."}
        await self.service.provider_event(failure)
        await self.service.provider_event({"type": "level", "level": 0.2})
        self.assertEqual(self.service.voice["task_error"]["code"], "AGENT_UNAVAILABLE")
        await self.service.submit_intent({"objective": "Create a page", "summary": "Create the page."}, "turn-Create a page")
        self.assertNotIn("task_error", self.service.voice)
        await self.service.provider_event(failure)
        await self.service.end_voice()
        self.assertNotIn("task_error", self.service.voice)
        self.service.voice["task_error"] = {"code": "PROJECT_REQUIRED", "message": "old failure"}
        await self.service.dispatch({"action": "submit_text", "text": "New session"})
        self.assertNotIn("task_error", self.service.voice)

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

    async def test_same_watch_socket_off_cancels_blocked_start_and_queued_restart(self):
        entered, stopped = asyncio.Event(), asyncio.Event()
        instances = []
        class SlowProvider(FakeProvider):
            def __init__(self, *args):
                super().__init__(*args)
                self.audio_transport = AsyncMock()
                instances.append(self)
            async def start(self, audio=True):
                entered.set()
                await asyncio.Event().wait()
            async def stop(self):
                stopped.set()
        self.service.provider_factory = SlowProvider
        control = self.service.control = ControlServer(self.root / "responsive.sock", self.service.dispatch,
            self.service.snapshot, peer_check=lambda writer: True)
        await control.start()
        reader, writer = await asyncio.open_unix_connection(str(control.path))
        try:
            writer.write(b'{"action":"watch"}\n')
            await writer.drain()
            await reader.readline()
            start = json.dumps({"action": "start_voice", "project": str(self.project)}).encode() + b"\n"
            writer.write(start)
            await writer.drain()
            await asyncio.wait_for(entered.wait(), 1)
            writer.write(start + b'{"action":"end_voice"}\n')
            await writer.drain()
            replies, states = [], []
            async def receive():
                while len(replies) < 3:
                    item = json.loads(await reader.readline())
                    if "ok" in item:
                        replies.append(item)
                    else:
                        states.append(item["voice"]["state"])
            await asyncio.wait_for(receive(), 1)
            self.assertTrue(all(reply["ok"] for reply in replies))
            self.assertEqual(sum(bool(reply.get("cancelled")) for reply in replies), 2)
            self.assertIn("connecting", states)
            self.assertIn("disabled", states)
            self.assertEqual(len(instances), 1)
            self.assertTrue(stopped.is_set())
            instances[0].audio_transport.stop.assert_awaited_once()
            self.assertIsNone(self.service.provider)
        finally:
            writer.close()
            await writer.wait_closed()
            await control.close()

    async def test_same_watch_socket_off_cancels_typed_inference_and_rejects_late_handoff(self):
        entered, rejected = asyncio.Event(), asyncio.Event()
        class SlowProvider(FakeProvider):
            async def text(self, text, context):
                await super().text(text, context)
                entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    # Even a delayed callback during cancellation has no authority.
                    try:
                        await self.submit({"objective": "Late", "summary": "Late"}, "turn-Do work")
                    except VoiceError:
                        rejected.set()
                    raise
        self.service.provider_factory = SlowProvider
        control = self.service.control = ControlServer(self.root / "typed-responsive.sock", self.service.dispatch,
            self.service.snapshot, peer_check=lambda writer: True)
        await control.start()
        reader, writer = await asyncio.open_unix_connection(str(control.path))
        try:
            writer.write(b'{"action":"watch"}\n')
            await writer.drain()
            await reader.readline()
            writer.write(json.dumps({"action": "submit_text", "text": "Do work", "project": str(self.project)}).encode() + b"\n")
            await writer.drain()
            await asyncio.wait_for(entered.wait(), 1)
            writer.write(b'{"action":"end_voice"}\n')
            await writer.drain()
            replies = []
            async def receive():
                while len(replies) < 2:
                    item = json.loads(await reader.readline())
                    if "ok" in item:
                        replies.append(item)
            await asyncio.wait_for(receive(), 1)
            self.assertTrue(rejected.is_set())
            self.assertEqual(self.service.store.list(), [])
            self.assertFalse(self.service.voice["microphone"])
            self.assertEqual(self.service.voice["state"], "disabled")
        finally:
            writer.close()
            await writer.wait_closed()
            await control.close()

    async def test_offline_connecting_is_visible_before_preparation_and_off_interrupts_it(self):
        self.service.settings.update({"mode": "offline"})
        entered = asyncio.Event()
        async def prepare(project):
            entered.set()
            await asyncio.Event().wait()
        with patch.object(self.service, "offline_runtime", side_effect=prepare):
            start = asyncio.create_task(self.service.dispatch({"action": "start_voice", "project": str(self.project)}))
            await asyncio.wait_for(entered.wait(), 1)
            self.assertEqual(self.service.voice["state"], "connecting")
            await asyncio.wait_for(self.service.dispatch({"action": "end_voice"}), 1)
            with self.assertRaises(asyncio.CancelledError):
                await start
            self.assertEqual(self.service.voice["state"], "disabled")

    async def test_preparation_failure_settles_disabled_with_safe_error(self):
        self.service.settings.update({"mode": "offline"})
        with patch.object(self.service, "offline_runtime", side_effect=RuntimeError("private endpoint and secret")):
            with self.assertRaises(RuntimeError):
                await self.service.dispatch({"action": "start_voice", "project": str(self.project)})
        self.assertEqual(self.service.voice["state"], "disabled")
        self.assertFalse(self.service.voice["microphone"])
        self.assertNotIn("secret", self.service.voice["error"])
        self.assertTrue(self.service.voice["error"])

    async def test_control_keeps_mutations_ordered_while_status_bypasses_wait(self):
        gate, entered = asyncio.Event(), asyncio.Event()
        actions = []
        async def dispatch(request):
            action = request["action"]
            actions.append(action)
            if action == "configure":
                entered.set()
                await gate.wait()
                actions.append("configured")
            return {"completed": action}
        control = ControlServer(self.root / "ordered.sock", dispatch, lambda: {}, peer_check=lambda writer: True)
        await control.start()
        reader, writer = await asyncio.open_unix_connection(str(control.path))
        try:
            writer.write(b'{"action":"configure"}\n{"action":"task_action"}\n{"action":"status"}\n')
            await writer.drain()
            await asyncio.wait_for(entered.wait(), 1)
            first = json.loads(await asyncio.wait_for(reader.readline(), 1))
            self.assertEqual(first["completed"], "status")
            self.assertNotIn("task_action", actions)
            gate.set()
            rest = [json.loads(await asyncio.wait_for(reader.readline(), 1)) for _ in range(2)]
            self.assertEqual([item["completed"] for item in rest], ["configure", "task_action"])
            self.assertLess(actions.index("configured"), actions.index("task_action"))
        finally:
            gate.set()
            writer.close()
            await writer.wait_closed()
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

    async def test_readiness_releases_its_temporary_offline_workspace(self):
        runtime = Mock()
        runtime.open_display = AsyncMock()
        runtime.start = AsyncMock()
        runtime.stop = AsyncMock()
        runtime.model_request = AsyncMock(return_value={"models": [{"name": "small:latest"}]})
        self.service.settings.update({"mode": "offline", "model": "small:latest"})
        with patch("maslow_voice.offline.OfflineRuntime", return_value=runtime):
            await self.service.dispatch({"action": "test"})
        runtime.start.assert_awaited_once()
        runtime.stop.assert_awaited_once()
        self.assertIsNone(self.service.offline)

    async def test_new_offline_task_evicts_reported_dead_hermes_client(self):
        runtime = AsyncMock()
        runtime.launch_hermes.return_value = {"endpoint": "http://127.0.0.1:18001", "token": "fresh"}
        self.service.offline_runtime = AsyncMock(return_value=runtime)
        self.service.hermes.model_config = AsyncMock(return_value=({"provider": "custom", "default": "local"}, {}))
        project = str(self.project)
        dead = HermesClient("http://127.0.0.1:18000", "old", request=runtime.hermes_request,
            discard_process=lambda: self.service.offline_clients.pop(project, None))
        dead.record_process_exit()
        self.service.offline_clients[project] = dead

        client = await self.service.executor_client({"mode": "offline", "project": project})
        self.assertIsNot(client, dead)
        self.assertIs(self.service.offline_clients[project], client)
        runtime.launch_hermes.assert_awaited_once()

    async def test_large_child_history_cannot_break_the_control_frame(self):
        approval = {"request_id": "exact", "message": "Review the complete proposed command."}
        children = [{"result": "x" * 200000, "instructions": "y" * 12000} for _ in range(20)]
        tasks = [{"id": str(i), "result": "r" * 12000, "source": "s" * 12000,
                  "children": children, "approval": approval} for i in range(50)]
        with patch.object(self.service.store, "list", return_value=tasks):
            snapshot = self.service.snapshot()
        self.assertLess(len(json.dumps(snapshot).encode()), 4 * 1024 * 1024)
        self.assertEqual(snapshot["tasks"][0]["approval"], approval)
        self.assertEqual(len(tasks[0]["children"][0]["result"]), 200000)

    async def test_audio_shutdown_failure_does_not_skip_provider_cleanup(self):
        provider = Mock()
        provider.audio_transport.stop = AsyncMock(side_effect=OSError("device disconnected"))
        provider.stop = AsyncMock()
        await self.service._release_provider(provider)
        provider.stop.assert_awaited_once()
