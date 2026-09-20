"""Native Gemini compatibility, turn ownership, setup and Voice Lab boundaries."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.config import DEFAULTS, Settings
from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.providers import create_provider
from maslow_voice.providers.livekit_gemini import LiveKitGeminiProvider
from maslow_voice.store import TaskStore
from maslow_voice.tasks import TaskManager

BRIEF = {"objective": "Create a page", "summary": "Create the requested page.", "constraints": [],
         "requested_output": "page.html", "tool_preference": "hermes", "unresolved_questions": []}


class GeminiSdkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        try:
            from livekit import agents
            from livekit.plugins.google.realtime.realtime_api import RealtimeSession
        except ImportError:
            self.skipTest("Google LiveKit plugin is not installed")
        self.agents, self.RealtimeSession = agents, RealtimeSession
        self.events = []
        self.provider = LiveKitGeminiProvider(config=dict(DEFAULTS), secrets={"google": "fake-local-test-key"},
            emit=AsyncMock(side_effect=self.events.append), submit=AsyncMock(return_value={"state": "queued"}))
        self.provider._session = self.provider._create_agent_session(agents, "", "")
        self.addAsyncCleanup(self.provider.stop)

    async def test_desktop_tool_binds_final_transcript_and_rejects_stale_retry(self):
        self.provider._started = True
        self.provider._tool_turns["desktop-call"] = "final-turn"
        context = SimpleNamespace(function_call=SimpleNamespace(call_id="desktop-call"),
                                  speech_handle=SimpleNamespace(interrupted=False))
        await self.provider._agent.desktop_action(context, "codex")
        self.provider._submit_callback.assert_awaited_once_with(
            {"operation": "desktop", "application": "codex"}, "final-turn")
        response = await self.provider._agent.desktop_action(context, "codex")
        self.assertEqual(json.loads(response)["status"], "not_performed")
        self.assertEqual(self.provider._submit_callback.await_count, 1)

    async def test_interrupted_task_control_cannot_mutate_job(self):
        self.provider._started = True
        self.provider._tool_turns["control-call"] = "final-turn"
        context = SimpleNamespace(function_call=SimpleNamespace(call_id="control-call"),
                                  speech_handle=SimpleNamespace(interrupted=True))
        response = await self.provider._agent.task_control(context, "cancel")
        self.assertEqual(json.loads(response)["status"], "not_performed")
        self.provider._submit_callback.assert_not_awaited()

    async def test_completion_speech_has_no_action_tools_and_waits_for_user(self):
        self.provider._started = True
        original = self.provider._session
        fake = SimpleNamespace(user_state="speaking", agent_state="listening", generate_reply=AsyncMock())
        self.provider._session = fake
        try:
            self.assertFalse(await self.provider.notify_task("Completed"))
            fake.generate_reply.assert_not_awaited()
            fake.user_state = "listening"
            self.assertTrue(await self.provider.notify_task("Completed"))
            self.assertEqual(fake.generate_reply.call_args.kwargs["tools"], [])
        finally:
            self.provider._session = original

    async def test_real_native_start_attaches_audio_and_mute_controls_capture(self):
        from maslow_voice.audio import PcmFrame
        from maslow_voice.providers.livekit_native_audio import NativeAgentAudioInput, NativeAgentAudioOutput

        audio = SimpleNamespace(start=AsyncMock(), stop=AsyncMock(), set_muted=AsyncMock(),
                                clear_playback=AsyncMock(), play=AsyncMock(), played_samples=0)
        self.provider.audio_transport = audio
        # Reuse the already constructed real AgentSession. Replace only the
        # external Google connection; AgentSession startup and I/O stay real.
        session = self.provider._session
        with patch.object(self.provider, "_create_agent_session", return_value=session), \
             patch.object(self.RealtimeSession, "_main_task", new=AsyncMock()):
            await self.provider.start(audio=True)
        self.assertIsInstance(session.input.audio, NativeAgentAudioInput)
        self.assertIsInstance(session.output.audio, NativeAgentAudioOutput)
        self.assertTrue(session.input.audio_enabled)
        self.assertTrue(self.provider._audio_enabled)
        self.assertTrue(self.events[-1]["microphone"])
        audio.start.assert_awaited_once_with(self.provider._on_audio)

        # Follow one transport callback through the real AgentSession into
        # Google's realtime input without opening an external connection.
        frame = PcmFrame(b"\x01\x00" * 960)
        received = asyncio.Event()
        captured = []

        def capture(value):
            captured.append(value)
            received.set()

        with patch.object(self.RealtimeSession, "push_audio", side_effect=capture):
            await self.provider._on_audio(frame)
            await asyncio.wait_for(received.wait(), .5)
        self.assertEqual(b"".join(bytes(value.data) for value in captured), frame.pcm)
        await self.provider.mute(True)
        self.assertFalse(session.input.audio_enabled)
        self.assertFalse(self.events[-1]["microphone"])
        await self.provider.mute(False)
        self.assertTrue(session.input.audio_enabled)
        self.assertTrue(self.events[-1]["microphone"])

    async def test_real_typed_session_unmute_does_not_enable_missing_input(self):
        session = self.provider._session
        audio = SimpleNamespace(start=AsyncMock(), stop=AsyncMock(), set_muted=AsyncMock())
        self.provider.audio_transport = audio
        with patch.object(self.provider, "_create_agent_session", return_value=session), \
             patch.object(self.RealtimeSession, "_main_task", new=AsyncMock()):
            await self.provider.start(audio=False)
        await self.provider.mute(True)
        with self.assertNoLogs("livekit.agents", level="WARNING"):
            await self.provider.mute(False)
        self.assertIsNone(session.input.audio)
        self.assertFalse(session.input.audio_enabled)
        self.assertFalse(self.provider._audio_enabled)
        self.assertFalse(self.events[-1]["microphone"])
        audio.start.assert_not_awaited()
        audio.set_muted.assert_awaited_once_with(True)

    async def test_real_agent_handoff_is_ignored_and_assistant_transcript_still_emitted(self):
        from livekit.agents.voice.events import ConversationItemAddedEvent
        from maslow_voice.providers.livekit_expressive import LiveKitExpressiveProvider
        handoff = ConversationItemAddedEvent(item=self.agents.llm.AgentHandoff(new_agent_id="maslow"))
        self.provider._conversation_item(handoff)
        # The shared Expressive callback also receives the SDK's non-chat items.
        LiveKitExpressiveProvider._conversation_item(self.provider, handoff)
        self.assertEqual(self.events, [])
        assistant = ConversationItemAddedEvent(item=self.agents.llm.ChatMessage(role="assistant", content=["Ready to help."]))
        self.provider._conversation_item(assistant)
        await asyncio.gather(*self.provider._event_tasks)
        self.assertEqual(self.events, [{"type": "transcript", "role": "assistant", "text": "Ready to help.", "final": True}])

    async def test_real_sdk_startup_control_content_warns_without_losing_next_generation(self):
        from google.genai import types
        with patch.object(self.RealtimeSession, "_main_task", new=AsyncMock()):
            realtime = self.provider._session.llm.session()
        self.addAsyncCleanup(realtime.aclose)
        generations = []
        realtime.on("generation_created", generations.append)

        async def responses():
            yield types.LiveServerMessage(server_content=types.LiveServerContent(turn_complete=True))
            yield types.LiveServerMessage(server_content=types.LiveServerContent(
                input_transcription=types.Transcription(text="Hello"),
                output_transcription=types.Transcription(text="Hi there"), turn_complete=True))
            realtime._session_should_close.set()

        connection = SimpleNamespace(receive=responses)
        realtime._active_session = connection
        try:
            with self.assertLogs("livekit.plugins.google", level="WARNING") as captured:
                await realtime._recv_task(connection)
        finally:
            realtime._active_session = None
        self.assertTrue(any("received server content but no active generation" in entry for entry in captured.output))
        self.assertEqual(len(generations), 1)
        self.assertEqual([item.text_content for item in realtime.chat_ctx.items], ["Hello", "Hi there"])

    async def test_real_model_options_schema_and_google_only_setup(self):
        from google.genai import types
        from livekit.agents.utils import is_given
        self.assertEqual(self.provider._settings(), ("", "", ""))
        model = self.provider._session.llm
        self.assertEqual(model._opts.model, "gemini-3.8-live")
        self.assertEqual(model._opts.voice, "Puck")
        self.assertEqual(model._opts.response_modalities, [types.Modality.AUDIO])
        self.assertFalse(is_given(model._opts.thinking_config))
        self.assertIsNotNone(model._opts.output_audio_transcription)
        schema = self.agents.ToolContext(self.provider._agent.tools).parse_function_tools("openai", strict=True)
        tools = {item["function"]["name"]: item["function"]["parameters"]["properties"] for item in schema}
        self.assertEqual(set(tools), {"submit_intent", "desktop_action", "task_control"})
        self.assertEqual(set(tools["submit_intent"]), set(BRIEF) | {"project_name", "new_project"})
        for parameters in tools.values():
            self.assertNotIn("context", parameters)
        with patch.object(self.RealtimeSession, "_main_task", new=AsyncMock()):
            realtime = model.session()
            try:
                config = realtime._build_connect_config()
                self.assertIsNone(config.thinking_config)
            finally:
                await realtime.aclose()

    async def test_real_google_tool_events_bind_original_turn_after_barge_in(self):
        from google.genai import types
        with patch.object(self.RealtimeSession, "_main_task", new=AsyncMock()):
            realtime = self.provider._session.llm.session()
        self.addAsyncCleanup(realtime.aclose)
        generations = []
        realtime.on("generation_created", generations.append)
        realtime._start_new_generation()
        realtime._handle_server_content(types.LiveServerContent(input_transcription=types.Transcription(text="Use Hermes to create page.html")))
        realtime._handle_tool_calls(types.LiveServerToolCall(function_calls=[types.FunctionCall(id="first-call", name="submit_intent", args=BRIEF)]))
        first_identity = realtime.chat_ctx.items[0].id
        # A complete later generation arrives before the original stream is consumed.
        realtime._start_new_generation()
        realtime._handle_server_content(types.LiveServerContent(input_transcription=types.Transcription(text="Tell me a joke"), turn_complete=True))
        calls = [call async for call in generations[0].function_stream]
        self.assertEqual([call.call_id for call in calls], ["first-call"])
        self.assertEqual(self.provider._tool_turns["first-call"], first_identity)
        self.assertEqual(self.events[-1]["text"], "Use Hermes to create page.html")

    async def test_real_google_call_without_transcript_cannot_submit(self):
        from google.genai import types
        with patch.object(self.RealtimeSession, "_main_task", new=AsyncMock()):
            realtime = self.provider._session.llm.session()
        self.addAsyncCleanup(realtime.aclose)
        generations = []
        realtime.on("generation_created", generations.append)
        realtime._start_new_generation()
        realtime._handle_tool_calls(types.LiveServerToolCall(function_calls=[types.FunctionCall(id="unbound-call", name="submit_intent", args=BRIEF)]))
        _calls = [call async for call in generations[0].function_stream]
        self.assertNotIn("unbound-call", self.provider._tool_turns)

    async def test_task_review_response_never_claims_started(self):
        self.provider._started = True
        self.provider._tool_turns["review-call"] = "turn-one"
        self.provider._submit_callback.return_value = {"state": "proposed", "selected_agent": "hermes"}
        context = SimpleNamespace(function_call=SimpleNamespace(call_id="review-call"), speech_handle=SimpleNamespace(interrupted=False))
        result = await self.provider._agent.submit_intent(context, **BRIEF)
        self.assertIn("No work has started", result)

    async def test_safe_layer_errors_never_include_private_diagnostics(self):
        for status, expected in ((401, "GEMINI_AUTH_FAILED"), (429, "GEMINI_USAGE_LIMIT"), (404, "GEMINI_MODEL_UNAVAILABLE")):
            cause = SimpleNamespace(status_code=status, message="secret-value-at-private-endpoint")
            error = self.provider._public_error(cause)
            self.assertEqual(error.code, expected)
            self.assertNotIn("secret-value", error.message)


class GeminiServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.values = {}
        self.credentials = AsyncMock()
        self.credentials.get.side_effect = lambda name: self.values.get(name, "")
        self.credentials.set.side_effect = lambda name, value: self.values.__setitem__(name, value)
        self.credentials.delete.side_effect = lambda name: self.values.pop(name, None)
        self.service = VoiceService(self.root / "state", self.root / "runtime", credentials=self.credentials)

    async def asyncTearDown(self):
        await self.service.end_voice()
        self.service.store.close()
        self.temp.cleanup()

    async def test_default_new_install_and_preserved_existing_provider(self):
        self.assertEqual(self.service.settings.value["mode"], "gemini_live")
        self.assertEqual(self.service.settings.value["default_coder"], "auto")
        self.service.settings.update({"mode": "livekit"})
        self.assertEqual(Settings(self.root / "state").value["mode"], "livekit")
        provider = create_provider(dict(DEFAULTS), {}, AsyncMock(), AsyncMock())
        self.assertIsInstance(provider, LiveKitGeminiProvider)

    async def test_first_status_reports_configured_conversation_ready(self):
        try:
            from livekit.plugins import google
        except ImportError:
            self.skipTest("Google LiveKit plugin is not installed")
        self.values["google"] = "fake-google"
        self.service.hermes_ready = AsyncMock(return_value=False)
        result = await self.service.dispatch({"action": "status"})
        self.assertTrue(result["snapshot"]["readiness"]["conversation"]["ready"])
        self.assertIsNone(self.service.provider)

    async def test_new_install_accepts_google_only_without_livekit(self):
        result = await self.service.dispatch({"action": "configure_gemini_live", "google_api_key": "fake-google-key"})
        self.assertEqual(result, {"gemini_live_saved": True})
        self.assertEqual(self.values, {"google": "fake-google-key"})
        self.assertEqual(self.service.settings.value["livekit_url"], "")
        self.assertTrue(self.service.readiness["conversation"]["ready"])
        self.assertFalse({"livekit_key", "livekit_secret"} & {call.args[0] for call in self.credentials.get.await_args_list})

    async def test_google_only_preserves_optional_livekit_and_retains_google(self):
        self.service.settings.update({"mode": "livekit", "livekit_url": "wss://saved.invalid"})
        self.values.update(google="old-google", livekit_key="old-key", livekit_secret="old-secret")
        before = dict(self.values)
        result = await self.service.dispatch({"action": "configure_gemini_live", "url": " ", "api_key": "", "api_secret": " ", "google_api_key": ""})
        self.assertEqual(result, {"gemini_live_saved": True})
        self.assertEqual(self.values, before)
        self.assertEqual(self.service.settings.value["livekit_url"], "wss://saved.invalid")
        self.assertFalse({"livekit_key", "livekit_secret"} & {call.args[0] for call in self.credentials.get.await_args_list})
        self.credentials.set.assert_not_called()

    async def test_partial_livekit_rotation_resolves_saved_trio(self):
        self.service.settings.update({"livekit_url": "wss://saved.invalid"})
        self.values.update(google="old-google", livekit_key="old-key", livekit_secret="old-secret")
        await self.service.dispatch({"action": "configure_gemini_live", "api_key": "new-key"})
        self.assertEqual(self.values, {"google": "old-google", "livekit_key": "new-key", "livekit_secret": "old-secret"})
        self.assertEqual(self.service.settings.value["livekit_url"], "wss://saved.invalid")

    async def test_partial_new_livekit_setup_is_rejected_before_any_mutation(self):
        before = dict(self.service.settings.value)
        for fields in ({"api_key": "new-key"}, {"url": "wss://new.invalid"}, {"api_secret": "new-secret"}):
            with self.assertRaises(VoiceError) as caught:
                await self.service.dispatch({"action": "configure_gemini_live", "google_api_key": "new-google", **fields})
            self.assertEqual(caught.exception.code, "LIVEKIT_SETUP_INCOMPLETE")
        self.credentials.set.assert_not_called()
        self.assertEqual(self.service.settings.value, before)

    async def test_google_only_save_failure_restores_old_key_and_optional_setup(self):
        self.service.settings.update({"mode": "livekit", "livekit_url": "wss://saved.invalid"})
        self.values.update(google="old-google", livekit_key="old-key", livekit_secret="old-secret")
        before_values = dict(self.values)
        before_settings = dict(self.service.settings.value)
        with patch.object(self.service.settings, "update", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                await self.service.dispatch({"action": "configure_gemini_live", "google_api_key": "new-google"})
        self.assertEqual(self.values, before_values)
        self.assertEqual(self.service.settings.value, before_settings)
        self.assertTrue(all(call.args[0] == "google" for call in self.credentials.set.await_args_list))

    async def test_google_key_required_if_none_saved(self):
        with self.assertRaises(VoiceError) as caught:
            await self.service.dispatch({"action": "configure_gemini_live"})
        self.assertEqual(caught.exception.code, "GEMINI_SETUP_INCOMPLETE")
        self.credentials.set.assert_not_called()

    async def test_atomic_setup_saves_google_only_in_keyring(self):
        result = await self.service.dispatch({"action": "configure_gemini_live", "url": "wss://voice.invalid", "api_key": "fake-lk-key",
            "api_secret": "fake-lk-secret", "google_api_key": "fake-google-key"})
        self.assertEqual(result, {"gemini_live_saved": True})
        self.assertEqual(self.values["google"], "fake-google-key")
        self.assertEqual(await self.service.selected_secrets(), {"google": "fake-google-key"})
        public = json.dumps(self.service.snapshot()) + self.service.settings.path.read_text()
        for secret in self.values.values():
            self.assertNotIn(secret, public)

    async def test_atomic_setup_restores_all_credentials_when_settings_fail(self):
        self.values.update(google="old-google", livekit_key="old-key", livekit_secret="old-secret")
        before = dict(self.values)
        with patch.object(self.service.settings, "update", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                await self.service.dispatch({"action": "configure_gemini_live", "url": "wss://voice.invalid", "api_key": "new-key",
                    "api_secret": "new-secret", "google_api_key": "new-google"})
        self.assertEqual(self.values, before)

    async def test_audio_energy_and_user_transcripts_do_not_extend_idle(self):
        self.service.last_activity = 5
        await self.service.provider_event({"type": "level", "level": 1})
        await self.service.provider_event({"type": "transcript", "role": "user", "text": "nearby speech", "final": True})
        self.assertEqual(self.service.last_activity, 5)
        await self.service.provider_event({"type": "transcript", "role": "assistant", "text": "Completed response", "final": True})
        self.assertGreater(self.service.last_activity, 5)
        self.service.session_started = 10
        self.service.last_activity = 1809
        self.service.voice["speaking"] = True
        self.assertTrue(self.service.session_expired(1810))

    async def test_missing_agent_does_not_disable_ready_conversation(self):
        self.values["google"] = "fake-google"
        self.service.hermes_ready = AsyncMock(return_value=False)
        with patch("maslow_voice.execution.ExecutionManager.readiness", new=AsyncMock(return_value={"codex": {"ready": False}, "claude": {"ready": False}})):
            result = await self.service.check_readiness()
        try:
            from livekit.plugins import google
        except ImportError:
            self.skipTest("Google LiveKit plugin is not installed")
        self.assertTrue(result["readiness"]["conversation"]["ready"])
        self.assertTrue(result["readiness"]["ready"])
        self.assertFalse(result["readiness"]["tasks"]["ready"])


class SessionAuditTests(unittest.TestCase):
    def test_audit_excludes_payloads_and_uses_private_file(self):
        from maslow_voice.audit import SessionAudit
        with tempfile.TemporaryDirectory() as directory:
            audit = SessionAudit(directory)
            audit.record("usage", session_id="session", provider="gemini_live", input_tokens=12,
                         audio="raw-audio", transcript="private-conversation", google_api_key="private-key")
            record = json.loads(audit.path.read_text())
            self.assertEqual(record["input_tokens"], 12)
            self.assertFalse({"audio", "transcript", "google_api_key"} & record.keys())
            self.assertEqual(audit.path.stat().st_mode & 0o777, 0o600)

    def test_audit_does_not_follow_symlink(self):
        from maslow_voice.audit import SessionAudit
        with tempfile.TemporaryDirectory() as directory:
            audit = SessionAudit(directory)
            target = Path(directory) / "other"
            target.write_text("unchanged")
            audit.path.symlink_to(target)
            audit.record("session_started", provider="gemini_live")
            self.assertEqual(target.read_text(), "unchanged")


class ReviewPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = TaskStore(self.temp.name)
        self.manager = TaskManager(self.store, AsyncMock(), AsyncMock())
        self.manager._start = Mock()

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def test_review_proposal_survives_restart_and_starts_only_on_explicit_start(self):
        task = await self.manager.submit("review-task", BRIEF, self.temp.name, "gemini_live", "Use Hermes to create a page", "codex", policy="review")
        self.assertEqual(task["state"], "proposed")
        self.assertEqual(task["selected_agent"], "hermes")
        self.manager._start.assert_not_called()
        await self.manager.recover()
        self.manager._start.assert_not_called()
        result = await self.manager.action(task["id"], "start")
        self.assertEqual(result["state"], "queued")
        self.manager._start.assert_called_once()

    async def test_lab_auto_starts_and_direct_recovery_never_replays(self):
        task = await self.manager.submit("lab-task", dict(BRIEF, tool_preference="codex"), self.temp.name, "gemini_live", "Use Codex to create a page")
        self.manager._start.assert_called_once()
        self.manager._start.reset_mock()
        self.store.update(task["id"], state="submitting")
        await self.manager.recover()
        self.manager._start.assert_not_called()
        self.assertEqual(self.store.get(task["id"])["state"], "interrupted")
