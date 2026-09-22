import asyncio
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.voice_preview import play_sample, SAMPLE


class PreviewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.service = VoiceService(root / "state", root / "run", credentials=AsyncMock())
        self.service.credentials.get.return_value = "private-test-key"

    async def asyncTearDown(self):
        await self.service.end_voice()
        self.service.store.close()
        self.temp.cleanup()

    async def test_preview_is_ephemeral_exclusive_and_stoppable(self):
        before = dict(self.service.settings.value)
        with patch("maslow_voice.daemon.play_sample", new=AsyncMock(side_effect=lambda *a, **k: None)) as play:
            # Block after startup to verify exclusivity.
            entered = asyncio.Event()
            async def wait(*args, **kwargs):
                entered.set()
                await asyncio.Event().wait()
            play.side_effect = wait
            await self.service.dispatch({"action": "preview_gemini_voice", "voice": "Zephyr"})
            await entered.wait()
            for action in ({"action": "start_voice"}, {"action": "submit_text", "text": "Build an app"},
                           {"action": "configure", "settings": {"gemini_live_voice": "Kore"}},
                           {"action": "preview_gemini_voice", "voice": "Kore"}):
                with self.assertRaises(VoiceError):
                    await self.service.dispatch(action)
            await self.service.dispatch({"action": "stop_gemini_voice_preview"})
        self.assertIsNone(self.service.preview_task)
        self.assertEqual(self.service.voice_preview["state"], "idle")
        self.assertEqual(self.service.settings.value, before)
        self.assertEqual(self.service.store.list(), [])
        self.assertFalse(self.service.voice["microphone"])

    async def test_rejects_invalid_voice_busy_provider_tasks_and_missing_auth(self):
        for voice in ("shell; command", None, []):
            with self.assertRaises(VoiceError):
                await self.service.dispatch({"action": "preview_gemini_voice", "voice": voice})
        self.service.provider = object()
        with self.assertRaises(VoiceError):
            await self.service.start_preview("Puck")
        self.service.provider = None
        with patch.object(self.service.store, "active", return_value=[{}]):
            with self.assertRaises(VoiceError):
                await self.service.start_preview("Puck")
        self.service.credentials.get.return_value = ""
        await self.service.start_preview("Puck")
        await self.service.preview_task
        self.assertEqual(self.service.voice_preview["state"], "error")
        self.assertIn("Google", self.service.voice_preview["error"])

    async def test_completion_errors_and_end_voice_cleanup(self):
        for fail in (False, True):
            with patch("maslow_voice.daemon.play_sample", new=AsyncMock(side_effect=RuntimeError("secret") if fail else None)):
                await self.service.start_preview("Puck")
                await self.service.preview_task
                self.assertEqual(self.service.voice_preview["state"], "error" if fail else "idle")
                self.assertNotIn("secret", self.service.voice_preview["error"])
        await self.service.start_preview("Puck")
        await self.service.end_voice()
        self.assertIsNone(self.service.preview_task)
        self.assertEqual(self.service.voice_preview["state"], "idle")

    async def test_stop_speech_also_stops_preview(self):
        with patch("maslow_voice.daemon.play_sample", new=AsyncMock()):
            await self.service.start_preview("Puck")
            await self.service.dispatch({"action": "silence"})
        self.assertIsNone(self.service.preview_task)

    async def test_real_sdk_request_output_only_and_cleanup(self):
        from google.genai import types
        session = SimpleNamespace(send_client_content=AsyncMock())
        async def receive():
            yield types.LiveServerMessage(server_content=types.LiveServerContent(
                model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\0\0" * 24, mime_type="audio/pcm;rate=24000"))]),
                turn_complete=True))
        session.receive = receive
        captured = {}
        @asynccontextmanager
        async def connect(**kwargs):
            captured.update(kwargs)
            yield session
        client = SimpleNamespace(aio=SimpleNamespace(live=SimpleNamespace(connect=connect), aclose=AsyncMock()))
        transport = SimpleNamespace(start=AsyncMock(), play=AsyncMock(), wait_playback=AsyncMock(),
                                    stop=AsyncMock(), output_latency_seconds=0)
        factory = Mock(return_value=transport)
        playing = AsyncMock()
        await play_sample(self.service.settings.value, "fake-key", "Zephyr", playing,
                          transport_factory=factory, client_factory=Mock(return_value=client))
        factory.assert_called_once_with(capture=False, speaker_device="")
        self.assertEqual(captured["model"], self.service.settings.value["gemini_live_model"])
        config = captured["config"]
        self.assertEqual(config.speech_config.voice_config.prebuilt_voice_config.voice_name, "Zephyr")
        self.assertFalse(config.tools)
        self.assertIn(SAMPLE, str(session.send_client_content.call_args))
        playing.assert_awaited_once()
        self.assertEqual(transport.play.call_args.args[0].sample_rate, 24000)
        transport.stop.assert_awaited_once()
        client.aio.aclose.assert_awaited_once()
