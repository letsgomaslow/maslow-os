"""Focused contracts for the optional native LiveKit audio path."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.providers.livekit_expressive import LiveKitExpressiveProvider
from maslow_voice.providers.livekit_native import LiveKitNativeExpressiveProvider


class LazyNativeSdkImportTests(unittest.TestCase):
    def test_provider_import_does_not_load_native_audio_module(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import maslow_voice.providers.livekit_native; "
                "assert 'maslow_voice.providers.livekit_native_audio' not in sys.modules",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class OptionalNativeSdkTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        try:
            from livekit import rtc
            from maslow_voice.providers.livekit_native_audio import NativeAgentAudioInput, NativeAgentAudioOutput
        except ImportError:
            self.skipTest("LiveKit optional SDK is not installed")
        self.rtc = rtc
        self.NativeAgentAudioInput = NativeAgentAudioInput
        self.NativeAgentAudioOutput = NativeAgentAudioOutput

    def frame(self, samples: int = 960):
        return self.rtc.AudioFrame(b"\0\0" * samples, 48_000, 1, samples)


class NativeInputOutputTests(OptionalNativeSdkTest):
    async def test_input_backpressure_mute_and_close_invalidate_stale_frames(self):
        source = self.NativeAgentAudioInput()
        self.assertTrue(await source.push_frame(self.frame()))
        self.assertTrue(await source.push_frame(self.frame()))
        blocked = asyncio.create_task(source.push_frame(self.frame()))
        await asyncio.sleep(0)
        self.assertFalse(blocked.done())
        source.discard()
        self.assertFalse(await blocked)
        self.assertTrue(await source.push_frame(self.frame()))
        self.assertTrue(await source.push_frame(self.frame()))
        closing = asyncio.create_task(source.push_frame(self.frame()))
        await asyncio.sleep(0)
        source.close()
        with self.assertRaises(asyncio.CancelledError):
            await closing

    async def test_exact_fractional_sample_completion_uses_public_transport_cursor(self):
        transport = _Transport()
        output = self.NativeAgentAudioOutput(transport)
        finished = []
        output.on("playback_finished", finished.append)
        await output.capture_frame(self.frame(985))
        output.flush()
        transport.played_samples = 985
        await output._flush_task
        self.assertEqual(len(finished), 1)
        self.assertFalse(finished[0].interrupted)
        self.assertEqual(finished[0].playback_position, 985 / 48_000)
        await output.aclose()

    async def test_clear_reset_completes_one_interrupted_segment_with_snapshot_position(self):
        transport = _Transport()
        output = self.NativeAgentAudioOutput(transport)
        finished = []
        output.on("playback_finished", finished.append)
        await output.capture_frame(self.frame())
        output.flush()
        transport.played_samples = 480
        output.clear_buffer()
        output.clear_buffer()
        await output._flush_task
        await output._clear_task
        self.assertEqual(len(finished), 1)
        self.assertTrue(finished[0].interrupted)
        self.assertEqual(finished[0].playback_position, 0.01)
        self.assertEqual(transport.clear_calls, 1)
        await output.aclose()

    async def test_stopped_device_and_clear_failure_do_not_leave_playback_waiting(self):
        transport = _Transport(clear_error=RuntimeError("fixture clear failure"))
        output = self.NativeAgentAudioOutput(transport)
        finished = []
        output.on("playback_finished", finished.append)
        await output.capture_frame(self.frame())
        output.flush()
        transport.played_samples = 480
        output.clear_buffer()
        with self.assertRaisesRegex(RuntimeError, "fixture clear failure"):
            await output.aclose()
        self.assertEqual(len(finished), 1)
        self.assertTrue(finished[0].interrupted)
        self.assertEqual(finished[0].playback_position, 0.01)

    async def test_capture_waiting_on_pending_segment_cannot_revive_after_close(self):
        transport = _Transport()
        output = self.NativeAgentAudioOutput(transport)
        finished = []
        output.on("playback_finished", finished.append)
        await output.capture_frame(self.frame(985))
        output.flush()
        pending_next = asyncio.create_task(output.capture_frame(self.frame(985)))
        await asyncio.sleep(0)
        self.assertFalse(pending_next.done())
        await output.aclose()
        await pending_next
        self.assertEqual(len(transport.played), 1)
        self.assertEqual(len(finished), 1)
        self.assertTrue(finished[0].interrupted)


class _Transport:
    def __init__(self, *, clear_error: Exception | None = None) -> None:
        self.played_samples = 0
        self.output_latency_seconds = 0.020
        self.clear_error = clear_error
        self.played = []
        self.clear_calls = 0

    async def play(self, frame):
        self.played.append(frame)

    async def clear_playback(self):
        self.clear_calls += 1
        self.played_samples = 0
        if self.clear_error is not None:
            raise self.clear_error


class NativeProviderTests(unittest.IsolatedAsyncioTestCase):
    def provider(self, audio=None):
        async def emit(_event):
            return None
        async def submit(_intent, _turn):
            return {"id": "task"}
        return LiveKitNativeExpressiveProvider(
            config={"mode": "livekit", "livekit_url": "wss://voice.invalid"},
            secrets={"livekit_key": "a" * 32, "livekit_secret": "b" * 32},
            emit=emit,
            submit=submit,
            audio_transport=audio,
        )

    async def test_audio_false_starts_agent_session_without_device_or_native_io(self):
        audio = SimpleNamespace(start=AsyncMock(), stop=AsyncMock(), set_muted=AsyncMock())
        provider = self.provider(audio)
        session = _Session()
        provider._imports = Mock(return_value=(None, None, SimpleNamespace()))
        provider._settings = Mock(return_value=("wss://voice.invalid", "key", "secret"))
        provider._create_agent_session = Mock(return_value=session)
        provider._agent = object()
        await provider.start(audio=False)
        self.assertEqual(session.start.await_args.kwargs, {"agent": provider._agent, "record": False})
        audio.start.assert_not_awaited()
        self.assertIsNone(provider._native_input)
        self.assertIsNone(provider._native_output)
        await provider.stop()

    async def test_native_start_uses_custom_io_and_zero_aec_option(self):
        try:
            from maslow_voice.providers.livekit_native_audio import NativeAgentAudioInput, NativeAgentAudioOutput
        except ImportError:
            self.skipTest("LiveKit optional SDK is not installed")
        audio = _Transport()
        audio.start = AsyncMock()
        audio.stop = AsyncMock()
        audio.set_muted = AsyncMock()
        provider = self.provider(audio)
        session = _Session()
        provider._imports = Mock(return_value=(None, None, SimpleNamespace()))
        provider._settings = Mock(return_value=("wss://voice.invalid", "key", "secret"))
        provider._create_agent_session = Mock(return_value=session)
        provider._agent = object()
        await provider.start(audio=True)
        self.assertIsInstance(provider._native_input, NativeAgentAudioInput)
        self.assertIsInstance(provider._native_output, NativeAgentAudioOutput)
        self.assertIs(session.input.audio, provider._native_input)
        self.assertIs(session.output.audio, provider._native_output)
        self.assertEqual(session.start.await_args.kwargs, {"agent": provider._agent, "record": False})
        audio.start.assert_awaited_once_with(provider._on_audio)
        self.assertEqual(provider._agent_session_options(), {"aec_warmup_duration": 0.0})
        self.assertEqual(LiveKitExpressiveProvider._agent_session_options(provider), {})
        await provider.stop()

    async def test_mute_retires_input_generation_and_notifies_agent_session(self):
        audio = SimpleNamespace(set_muted=AsyncMock())
        provider = self.provider(audio)
        provider._started = provider._audio_enabled = True
        provider._native_input = SimpleNamespace(discard=Mock())
        provider._session = _Session()
        await provider.mute(True)
        provider._native_input.discard.assert_called_once()
        provider._session.input.set_audio_enabled.assert_called_once_with(False)
        audio.set_muted.assert_awaited_once_with(True)
        await provider.mute(False)
        self.assertEqual(provider._session.input.set_audio_enabled.call_args_list[-1].args, (True,))

    async def test_disconnect_attempts_inherited_owned_resources_after_native_output_failure(self):
        audio = SimpleNamespace(stop=AsyncMock())
        provider = self.provider(audio)
        session = provider._session = _Session()
        source = provider._source = SimpleNamespace(aclose=AsyncMock())
        native_input = provider._native_input = SimpleNamespace(close=Mock())
        native_output = provider._native_output = SimpleNamespace(aclose=AsyncMock(side_effect=RuntimeError("native output failure")))
        provider._http_session = SimpleNamespace(close=AsyncMock())
        client = SimpleNamespace(aclose=AsyncMock())
        provider._inference_clients = [client]
        with self.assertRaisesRegex(RuntimeError, "native output failure"):
            await provider.stop()
        native_input.close.assert_called_once()
        native_output.aclose.assert_awaited_once()
        session.aclose.assert_awaited_once()
        source.aclose.assert_awaited_once()
        client.aclose.assert_awaited_once()
        provider._http_session = None
        audio.stop.assert_awaited_once()

    async def test_fail_closes_direct_input_disables_session_audio_and_retires_output(self):
        provider = self.provider()
        provider._started = True
        provider._native_input = SimpleNamespace(close=Mock())
        provider._native_output = SimpleNamespace(clear_buffer=Mock())
        provider._session = _Session()
        from maslow_voice.providers.base import ProviderError

        provider._fail(ProviderError("fixture failure"))
        provider._native_input.close.assert_called_once()
        provider._native_output.clear_buffer.assert_called_once()
        provider._session.input.set_audio_enabled.assert_called_once_with(False)
        self.assertFalse(provider._started)
        await asyncio.gather(*provider._event_tasks)

    async def test_restart_replaces_closed_native_input_without_stale_generation(self):
        try:
            from livekit import rtc
            from maslow_voice.providers.livekit_native_audio import NativeAgentAudioInput
        except ImportError:
            self.skipTest("LiveKit optional SDK is not installed")
        audio = _Transport()
        audio.start = AsyncMock()
        audio.stop = AsyncMock()
        audio.set_muted = AsyncMock()
        provider = self.provider(audio)
        first, second = _Session(), _Session()
        provider._imports = Mock(return_value=(None, None, SimpleNamespace()))
        provider._settings = Mock(return_value=("wss://voice.invalid", "key", "secret"))
        provider._create_agent_session = Mock(side_effect=(first, second))
        provider._agent = object()
        await provider.start(audio=True)
        first_input = provider._native_input
        await provider.mute(True)
        await provider.stop()
        self.assertTrue(first_input._closed)
        with self.assertRaises(asyncio.CancelledError):
            await first_input.push_frame(rtc.AudioFrame(b"\0\0" * 960, 48_000, 1, 960))
        await provider.start(audio=True)
        self.assertIsInstance(provider._native_input, NativeAgentAudioInput)
        self.assertIsNot(provider._native_input, first_input)
        self.assertTrue(await provider._native_input.push_frame(rtc.AudioFrame(b"\0\0" * 960, 48_000, 1, 960)))
        await provider.stop()

    async def test_real_agents_constructor_receives_explicit_zero_aec_warmup(self):
        try:
            from livekit import agents
        except ImportError:
            self.skipTest("LiveKit optional SDK is not installed")
        provider = self.provider()
        with patch.object(agents.inference.LLM, "prewarm"):
            session = provider._create_agent_session(agents, "a" * 32, "b" * 32)
        provider._session = session
        self.addAsyncCleanup(provider._disconnect)
        self.assertEqual(session._opts.aec_warmup_duration, 0.0)


class _Session:
    def __init__(self) -> None:
        self.input = SimpleNamespace(audio=None, set_audio_enabled=Mock())
        self.output = SimpleNamespace(audio=None)
        self.start = AsyncMock()
        self.aclose = AsyncMock()
        self.on = Mock()
