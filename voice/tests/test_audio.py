from __future__ import annotations

import unittest
import asyncio
import random
from array import array
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.audio import PCM16K, PCM24K, PCM48K, PcmFrame, PortAudioTransport, resample_pcm16


class PcmResamplingTests(unittest.TestCase):
    @staticmethod
    def reference_resample(frame, sample_rate):
        if frame.sample_rate == sample_rate:
            return frame
        if not frame.pcm:
            return PcmFrame(b"", sample_rate)
        source = array("h")
        source.frombytes(frame.pcm)
        output_count = max(1, round(len(source) * sample_rate / frame.sample_rate))
        target = array("h")
        for index in range(output_count):
            position = index * frame.sample_rate / sample_rate
            left = min(int(position), len(source) - 1)
            right = min(left + 1, len(source) - 1)
            fraction = position - left
            target.append(round(source[left] + (source[right] - source[left]) * fraction))
        return PcmFrame(target.tobytes(), sample_rate)

    def test_resamples_48khz_pcm_to_provider_rates(self) -> None:
        samples = array("h", range(480))
        frame = PcmFrame(samples.tobytes(), PCM48K)

        self.assertEqual(len(resample_pcm16(frame, PCM24K).pcm), 240 * 2)
        self.assertEqual(len(resample_pcm16(frame, PCM16K).pcm), 160 * 2)

    def test_rejects_non_mono_or_odd_pcm(self) -> None:
        with self.assertRaises(ValueError):
            PcmFrame(b"x", PCM48K)
        with self.assertRaises(ValueError):
            PcmFrame(b"\0\0", PCM48K, channels=2)

    def test_fast_paths_match_original_resampler_for_edges_and_random_pcm(self) -> None:
        rng = random.Random(8128)
        lengths = [0, 1, 2, 3, 4, 5, 7, 8, 479, 480, 959, 960, 961]
        for source_rate, target_rate in ((PCM48K, PCM24K), (PCM48K, PCM16K)):
            for length in lengths:
                values = array("h", (rng.randint(-32768, 32767) for _ in range(length)))
                if length >= 2:
                    values[0], values[-1] = -32768, 32767
                frame = PcmFrame(values.tobytes(), source_rate)
                with self.subTest(source_rate=source_rate, target_rate=target_rate, length=length):
                    self.assertEqual(resample_pcm16(frame, target_rate), self.reference_resample(frame, target_rate))

        for source_rate, target_rate in ((PCM24K, PCM48K), (PCM16K, PCM48K), (PCM48K, 44100)):
            for length in lengths:
                frame = PcmFrame(b"\0\0" * length, source_rate)
                with self.subTest(zero=True, source_rate=source_rate, target_rate=target_rate, length=length):
                    self.assertEqual(resample_pcm16(frame, target_rate), self.reference_resample(frame, target_rate))


class PlaybackTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_output_only_preview_joins_audio_without_opening_or_processing_microphone(self):
        stream = SimpleNamespace(start=Mock(), stop=Mock(), close=Mock())
        output_factory = Mock(return_value=stream)
        duplex_factory = Mock(side_effect=AssertionError("preview must not open a microphone"))
        processing_factory = Mock(side_effect=AssertionError("preview must not construct microphone processing"))
        sounddevice = SimpleNamespace(RawStream=duplex_factory, RawOutputStream=output_factory)
        rtc = SimpleNamespace(AudioProcessingModule=processing_factory)
        handler = AsyncMock()
        transport = PortAudioTransport(capture=False, microphone_device="do-not-open", speaker_device="preview-speaker")
        with patch.dict("sys.modules", {"sounddevice": sounddevice, "livekit": SimpleNamespace(rtc=rtc)}):
            await transport.start(handler)
            try:
                output_factory.assert_called_once()
                options = output_factory.call_args.kwargs
                self.assertEqual(options["device"], "preview-speaker")
                self.assertEqual(options["channels"], 1)
                self.assertEqual(options["dtype"], "int16")
                self.assertIsNone(transport._handler)
                self.assertIsNone(transport._pump)
                self.assertIsNone(transport._apm)
                self.assertIsNone(transport._loop)
                first, second = b"\x11\x00" * 480, b"\x22\x00" * 480
                for packet in (first, second):
                    await transport.play(PcmFrame(packet))
                # Microphone mute controls remain harmless for speaker previews.
                await transport.set_muted(True)
                rendered = bytearray(1920)
                options["callback"](rendered, 960, None, None)
                self.assertEqual(bytes(rendered), first + second)
                self.assertEqual(transport.played_ms, 20)
                await transport.set_muted(False)
                transport._put_input((PcmFrame(first), first))
                self.assertTrue(transport._queue.empty())
                await transport.play(PcmFrame(first))
                await transport.clear_playback()
                options["callback"](rendered, 960, None, None)
                self.assertEqual(bytes(rendered), b"\0" * 1920)
                self.assertEqual(transport.played_ms, 0)
                duplex_factory.assert_not_called()
                processing_factory.assert_not_called()
                handler.assert_not_called()
            finally:
                await transport.stop()
                await transport.stop()
            stream.start.assert_called_once()
            stream.stop.assert_called_once()
            stream.close.assert_called_once()

    async def test_output_only_start_failure_closes_speaker_and_leaves_no_input_pump(self):
        stream = SimpleNamespace(start=Mock(side_effect=RuntimeError("speaker unavailable")), close=Mock())
        sounddevice = SimpleNamespace(RawOutputStream=Mock(return_value=stream))
        transport = PortAudioTransport(capture=False)
        # Playback-only operation does not require the capture/AEC dependency.
        with patch.dict("sys.modules", {"sounddevice": sounddevice, "livekit": None}):
            with self.assertRaisesRegex(RuntimeError, "speaker unavailable"):
                await transport.start(AsyncMock())
        self.assertFalse(transport._running)
        self.assertIsNone(transport._stream)
        self.assertIsNone(transport._pump)
        stream.close.assert_called_once()
        await transport.stop()

    async def test_failed_input_pump_closes_device_and_reports_safe_failure(self):
        report = AsyncMock()
        transport = PortAudioTransport(on_error=report)
        transport._running = True
        stream = transport._stream = SimpleNamespace(stop=Mock(), close=Mock())
        transport._drain_input = AsyncMock(side_effect=RuntimeError("private diagnostic"))
        transport._pump = asyncio.create_task(transport._run_input())
        await transport._pump
        self.assertFalse(transport._running)
        self.assertIsNone(transport._pump)
        self.assertIsNone(transport._stream)
        stream.stop.assert_called_once()
        stream.close.assert_called_once()
        report.assert_awaited_once_with()

    async def test_mute_discards_queued_capture_and_late_callbacks_after_stop(self):
        transport = PortAudioTransport()
        transport._running = True
        frame = (PcmFrame(b"\x00\x00" * 960), b"\x00\x00" * 960)
        transport._put_input(frame)
        self.assertEqual(transport._queue.qsize(), 1)
        await transport.set_muted(True)
        transport._put_input(frame)
        self.assertTrue(transport._queue.empty())
        await transport.stop()
        await transport.set_muted(False)
        transport._put_input(frame)
        self.assertTrue(transport._queue.empty())

    async def test_clear_playback_aborts_a_producer_waiting_on_full_queue(self):
        transport = PortAudioTransport(blocksize=480, queue_frames=2)
        transport._running = True
        producer = asyncio.create_task(transport.play(PcmFrame(b"\x01\x00" * 480 * 5, PCM48K)))
        try:
            await asyncio.sleep(0)
            self.assertEqual(len(transport._output), 2)
            self.assertFalse(producer.done())
            await transport.clear_playback()
            await asyncio.wait_for(producer, 1)
            self.assertEqual(list(transport._output), [])
            # A new reply remains playable; only the interrupted producer ends.
            await transport.play(PcmFrame(b"\x02\x00" * 480, PCM48K))
            self.assertEqual(list(transport._output), [b"\x02\x00" * 480])
        finally:
            await transport.stop()
            producer.cancel()
            await asyncio.gather(producer, return_exceptions=True)

    async def test_duplex_callback_joins_two_ten_ms_packets_and_feeds_the_same_audio_to_aec(self):
        class Frame:
            def __init__(self, pcm, sample_rate, channels, samples):
                self.data = bytearray(pcm)
        class Processing:
            def __init__(self, **options):
                self.options, self.reverse, self.near = options, [], []
            def set_stream_delay_ms(self, value):
                self.delay = value
            def process_reverse_stream(self, frame):
                self.reverse.append(bytes(frame.data))
            def process_stream(self, frame):
                self.near.append(bytes(frame.data))
                frame.data[:] = b"\x34\x12" * (len(frame.data) // 2)
        class Stream:
            def __init__(self, **options):
                self.callback = options["callback"]
                self.closed = self.stopped = False
            def start(self): pass
            def stop(self): self.stopped = True
            def close(self): self.closed = True
        rtc = SimpleNamespace(AudioFrame=Frame, AudioProcessingModule=Processing)
        delivered = asyncio.Queue()
        transport = PortAudioTransport()
        with patch.dict("sys.modules", {"sounddevice": SimpleNamespace(RawStream=Stream), "livekit": SimpleNamespace(rtc=rtc)}):
            await transport.start(delivered.put)
            stream, processing = transport._stream, transport._apm
            try:
                speaker = b"\x11\x00" * 480 + b"\x22\x00" * 480
                microphone = b"\x33\x00" * 960
                await transport.play(PcmFrame(speaker[:960]))
                await transport.play(PcmFrame(speaker[960:]))
                rendered = bytearray(1920)
                stream.callback(microphone, rendered, 960, None, None)
                cleaned = await asyncio.wait_for(delivered.get(), 1)
                self.assertEqual(bytes(rendered), speaker)
                self.assertEqual(processing.reverse, [speaker[:960], speaker[960:]])
                self.assertEqual(processing.near, [microphone[:960], microphone[960:]])
                self.assertEqual(cleaned.pcm, b"\x34\x12" * 960)
                self.assertEqual(transport.played_ms, 20)
                self.assertTrue(processing.options["echo_cancellation"])
                await transport.set_muted(True)
                stream.callback(microphone, rendered, 960, None, None)
                await asyncio.sleep(0)
                self.assertTrue(delivered.empty())
            finally:
                await transport.stop()
            self.assertTrue(stream.stopped and stream.closed)

    async def test_callback_preserves_variable_packet_remainders_and_counts_only_queued_audio(self):
        class Stream:
            def __init__(self, **options):
                self.callback = options["callback"]
            def start(self): pass
            def stop(self): pass
            def close(self): pass
        transport = PortAudioTransport()
        rtc = SimpleNamespace(AudioProcessingModule=Mock())
        with patch.dict("sys.modules", {"sounddevice": SimpleNamespace(RawStream=Stream), "livekit": SimpleNamespace(rtc=rtc)}):
            await transport.start(AsyncMock())
            # Playback does not depend on microphone capture being enabled.
            await transport.set_muted(True)
            try:
                first = b"\x11\x00" * 240
                second = b"\x22\x00" * 960
                third = b"\x33\x00" * 480
                for packet in (first, second, third):
                    await transport.play(PcmFrame(packet))
                rendered = bytearray(1920)
                transport._stream.callback(b"\0" * 1920, rendered, 960, None, None)
                self.assertEqual(bytes(rendered), first + second[:1440])
                self.assertEqual(list(transport._output), [second[1440:], third])
                self.assertEqual(transport.played_ms, 20)

                transport._stream.callback(b"\0" * 1920, rendered, 960, None, None)
                self.assertEqual(bytes(rendered), second[1440:] + third + b"\0" * 480)
                self.assertFalse(transport._output)
                self.assertEqual(transport.played_ms, 35)

                transport._stream.callback(b"\0" * 1920, rendered, 960, None, None)
                self.assertEqual(bytes(rendered), b"\0" * 1920)
                self.assertEqual(transport.played_ms, 35)

                # Barge-in clears a partial remainder as well as whole packets.
                await transport.play(PcmFrame(second))
                short_output = bytearray(480)
                transport._stream.callback(b"\0" * 480, short_output, 240, None, None)
                self.assertEqual(bytes(short_output), second[:480])
                self.assertEqual(list(transport._output), [second[480:]])
                await transport.clear_playback()
                transport._stream.callback(b"\0" * 1920, rendered, 960, None, None)
                self.assertEqual(bytes(rendered), b"\0" * 1920)
                self.assertEqual(transport.played_ms, 0)
            finally:
                await transport.stop()

    async def test_installed_aec_accepts_duplex_ten_ms_pcm(self):
        try:
            from livekit import rtc
        except ImportError:
            self.skipTest("optional LiveKit audio processing library is absent")
        processing = rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=True, high_pass_filter=True)
        processing.set_stream_delay_ms(30)
        far = rtc.AudioFrame(b"\x01\x00" * 480, PCM48K, 1, 480)
        near = rtc.AudioFrame(b"\x02\x00" * 480, PCM48K, 1, 480)
        processing.process_reverse_stream(far)
        processing.process_stream(near)
        self.assertEqual(len(near.data), 480)
