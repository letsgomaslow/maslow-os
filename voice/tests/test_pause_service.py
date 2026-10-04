import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.ipc import ControlServer
from test_service import FakeProvider


class PauseServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.service = VoiceService(self.root / "state", self.root / "runtime",
                                    provider_factory=FakeProvider, credentials=AsyncMock())
        self.service.tasks._start = lambda task: None

    async def asyncTearDown(self):
        await self.service.end_voice()
        self.service.store.close()
        self.temporary.cleanup()

    async def start(self, mode="gemini_live"):
        self.service.settings.update({"mode": mode})
        await self.service.dispatch({"action": "toggle_voice", "extended": False,
                                     "project": str(self.project), "context": "Keep context"})
        return self.service.provider

    async def test_supported_shortcuts_pause_resume_same_session_and_keep_tasks(self):
        for mode in ("gemini_live", "livekit", "openai"):
            with self.subTest(mode=mode):
                provider = await self.start(mode)
                session_id = self.service.session["id"]
                started = self.service.session_started
                await self.service.dispatch({"action": "submit_text", "text": "Explain"})
                transcript = list(self.service.session["transcript"])
                task = await self.service.tasks.submit(mode, {"objective": "Work", "summary": "Work"},
                                                       str(self.project), mode, "Work", "codex")
                await self.service.dispatch({"action": "toggle_voice", "extended": False})
                self.assertTrue(provider.paused)
                self.assertTrue(self.service.voice["enabled"])
                self.assertEqual(self.service.voice["state"], "paused")
                self.assertFalse(self.service.voice["microphone"])
                await self.service.dispatch({"action": "submit_text", "text": "Typed while paused"})
                self.assertTrue(self.service.voice["paused"])
                self.assertFalse(self.service.voice["microphone"])
                self.assertFalse(self.service.voice["speaking"])
                await self.service.dispatch({"action": "toggle_voice", "extended": False})
                self.assertFalse(provider.paused)
                self.assertIs(self.service.provider, provider)
                self.assertEqual(self.service.session["id"], session_id)
                self.assertEqual(self.service.session_started, started)
                self.assertEqual(self.service.session["transcript"][:len(transcript)], transcript)
                self.assertEqual(self.service.project, str(self.project))
                self.assertEqual(self.service.context, "Keep context")
                self.assertEqual(self.service.store.get(task["id"])["state"], "queued")
                await self.service.end_voice()
                self.service.store.update(task["id"], state="completed")

    async def test_pause_is_idempotent_and_late_states_and_levels_stay_paused(self):
        provider = await self.start()
        provider.pause = AsyncMock(wraps=provider.pause)
        for _ in range(2):
            await self.service.dispatch({"action": "pause_voice", "paused": True})
        provider.pause.assert_awaited_once_with(True)
        for state in ("listening", "thinking", "speaking"):
            await provider.emit({"type": "voice_state", "state": state, "microphone": True, "speaking": True})
        await provider.emit({"type": "level", "level": .7})
        await provider.emit({"type": "playback_level", "playback_level": .8})
        self.assertEqual(self.service.voice["state"], "paused")
        for field in ("microphone", "speaking", "level", "input_level", "playback_level"):
            self.assertFalse(self.service.voice[field])
        provider.mute = AsyncMock()
        await self.service.dispatch({"action": "start_voice"})
        await self.service.dispatch({"action": "mute", "muted": False})
        provider.mute.assert_not_awaited()
        for _ in range(2):
            await self.service.dispatch({"action": "pause_voice", "paused": False})
        self.assertEqual(provider.pause.await_count, 2)
        self.assertFalse(self.service.voice["paused"])

    async def test_pause_resume_preserves_existing_microphone_mute(self):
        provider = await self.start()
        async def mute(muted):
            await provider.emit({"type": "voice_state", "state": "listening", "microphone": not muted})
        provider.mute = mute
        await self.service.dispatch({"action": "mute", "muted": True})
        await self.service.pause_voice(True)
        await self.service.pause_voice(False)
        self.assertFalse(self.service.voice["paused"])
        self.assertFalse(self.service.voice["microphone"])

    async def test_paused_idle_suspension_and_mode_switch_preserve_original_limit(self):
        await self.start()
        self.service.session_started = self.service.last_activity = 0
        self.assertTrue(self.service.session_expired(61))
        await self.service.pause_voice(True)
        self.assertFalse(self.service.session_expired(1799))
        await self.service.toggle_voice(True)
        self.assertTrue(self.service.voice["paused"])
        self.assertEqual(self.service.session_started, 0)
        self.assertTrue(self.service.session_expired(1800))
        await self.service.toggle_voice(False)
        self.assertFalse(self.service.voice["extended"])
        self.assertTrue(self.service.voice["paused"])
        await self.service.pause_voice(False)
        self.assertEqual(self.service.session_started, 0)
        self.assertTrue(self.service.session_expired(1800))

    async def test_screen_lock_ends_paused_conversation(self):
        await self.start()
        await self.service.pause_voice(True)
        process = AsyncMock()
        process.returncode = 0
        process.communicate.return_value = (b'{"secure":true}', b'')
        with patch("maslow_voice.daemon.asyncio.create_subprocess_exec", return_value=process), \
             patch("maslow_voice.daemon.asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            with self.assertRaises(asyncio.CancelledError):
                await self.service.maintenance()
        self.assertIsNone(self.service.provider)
        self.assertFalse(self.service.voice["paused"])
        self.assertFalse(self.service.voice["microphone"])

    async def test_meter_fields_share_bounded_publisher_and_interruption_stops_output(self):
        await self.start()
        self.service.publish = AsyncMock()
        await self.service.provider_event({"type": "level", "level": .2})
        publisher = self.service.level_publish_task
        await self.service.provider_event({"type": "playback_level", "playback_level": .8})
        self.assertIs(self.service.level_publish_task, publisher)
        self.assertEqual(self.service.voice["input_level"], .2)
        self.assertEqual(self.service.voice["level"], .2)
        self.assertEqual(self.service.voice["playback_level"], .8)
        await asyncio.sleep(.07)
        self.service.publish.assert_awaited_once()
        before = self.service.voice["interruption_sequence"]
        await self.service.provider_event({"type": "interrupted"})
        self.assertEqual(self.service.voice["interruption_sequence"], before + 1)
        self.assertEqual(self.service.voice["playback_level"], 0)

    async def test_interruption_settles_listening_and_preserves_microphone_state(self):
        await self.start()
        for microphone in (True, False):
            self.service.voice.update(state="speaking", speaking=True, microphone=microphone, playback_level=.8)
            self.service.last_activity = 0
            await self.service.provider_event({"type": "interrupted"})
            self.assertEqual(self.service.voice["state"], "listening")
            self.assertEqual(self.service.voice["microphone"], microphone)
            self.assertFalse(self.service.voice["speaking"])
            self.assertEqual(self.service.voice["playback_level"], 0)
            self.assertGreater(self.service.last_activity, 0)
        for state in ("paused", "connecting", "disabled", "error"):
            self.service.voice.update(state=state, paused=state == "paused", microphone=False)
            await self.service.provider_event({"type": "interrupted"})
            self.assertEqual(self.service.voice["state"], state)
            self.assertFalse(self.service.voice["microphone"])
        self.service.voice.update(state="speaking", paused=False, error="Connection failed", microphone=False)
        await self.service.provider_event({"type": "interrupted"})
        self.assertEqual(self.service.voice["state"], "speaking")
        self.assertFalse(self.service.voice["microphone"])

    async def test_end_during_pause_revokes_late_resume_and_restart_is_disabled(self):
        provider = await self.start()
        entered, release = asyncio.Event(), asyncio.Event()
        async def pause(paused):
            entered.set()
            await release.wait()
            await provider.emit({"type": "voice_state", "state": "listening", "microphone": True})
        provider.pause = pause
        pausing = asyncio.create_task(self.service.pause_voice(True))
        await entered.wait()
        self.assertTrue(self.service.voice["paused"])
        await self.service.end_voice()
        release.set()
        await pausing
        self.assertEqual(self.service.voice["state"], "disabled")
        self.assertFalse(self.service.voice["microphone"])
        restarted = VoiceService(self.root / "state", self.root / "new-runtime", credentials=AsyncMock())
        try:
            self.assertFalse(restarted.voice["enabled"])
            self.assertFalse(restarted.voice["paused"])
            self.assertFalse(restarted.voice["microphone"])
        finally:
            restarted.store.close()

    async def test_rapid_pause_resume_controls_are_serialized(self):
        provider = await self.start()
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        published = asyncio.Event()
        async def publish():
            if self.service.voice["paused"]:
                published.set()
        self.service.publish = publish
        async def pause(paused):
            calls.append(paused)
            if paused:
                entered.set()
                await release.wait()
        provider.pause = pause
        pausing = asyncio.create_task(self.service.dispatch({"action": "toggle_voice", "extended": False}))
        await entered.wait()
        await asyncio.wait_for(published.wait(), .5)
        resuming = asyncio.create_task(self.service.dispatch({"action": "toggle_voice", "extended": False}))
        await asyncio.sleep(0)
        self.assertEqual(calls, [True])
        self.assertTrue(self.service.voice["paused"])
        release.set()
        await asyncio.gather(pausing, resuming)
        self.assertEqual(calls, [True, False])
        self.assertFalse(self.service.voice["paused"])
        self.assertTrue(self.service.voice["microphone"])

    async def test_end_cancels_pending_pause_without_reactivating_new_session(self):
        provider = await self.start()
        entered = asyncio.Event()
        async def pause(paused):
            entered.set()
            await asyncio.Event().wait()
        provider.pause = pause
        pausing = asyncio.create_task(self.service.dispatch({"action": "pause_voice", "paused": True}))
        await entered.wait()
        await asyncio.wait_for(self.service.dispatch({"action": "end_voice"}), 1)
        with self.assertRaises(asyncio.CancelledError):
            await pausing
        self.assertFalse(self.service.voice["microphone"])
        self.assertFalse(self.service.voice["paused"])
        await self.start()
        self.assertIsNot(self.service.provider, provider)
        self.assertTrue(self.service.voice["microphone"])

    async def test_same_watch_socket_second_activation_cancels_connecting(self):
        entered = asyncio.Event()
        class SlowProvider(FakeProvider):
            async def start(self, audio=True):
                entered.set()
                await asyncio.Event().wait()
        self.service.provider_factory = SlowProvider
        self.service.control = ControlServer(self.root / "toggle.sock", self.service.dispatch,
                                            self.service.snapshot, peer_check=lambda writer: True)
        await self.service.control.start()
        reader, writer = await asyncio.open_unix_connection(str(self.service.control.path))
        try:
            writer.write(b'{"action":"watch"}\n{"action":"toggle_voice","extended":false}\n')
            await writer.drain()
            await asyncio.wait_for(entered.wait(), 1)
            writer.write(b'{"action":"toggle_voice","extended":false}\n')
            await writer.drain()
            replies = []
            async def receive():
                while len(replies) < 2:
                    item = json.loads(await reader.readline())
                    if "ok" in item:
                        replies.append(item)
            await asyncio.wait_for(receive(), 1)
            self.assertTrue(all(reply["ok"] for reply in replies))
            self.assertEqual(sum(bool(reply.get("cancelled")) for reply in replies), 1)
            self.assertIsNone(self.service.provider)
            self.assertFalse(self.service.voice["microphone"])
            self.assertEqual(self.service.voice["state"], "disabled")
        finally:
            writer.close()
            await writer.wait_closed()
            await self.service.control.close()

    async def test_invalid_pause_is_rejected_and_experimental_toggle_retains_end(self):
        await self.start()
        with self.assertRaises(VoiceError):
            await self.service.pause_voice("yes")
        self.assertFalse(self.service.voice["paused"])
        await self.service.end_voice()
        await self.start("gpt_live")
        with self.assertRaises(VoiceError):
            await self.service.pause_voice(True)
        await self.service.toggle_voice(False)
        self.assertIsNone(self.service.provider)
