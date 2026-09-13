from __future__ import annotations

import unittest
import asyncio
from array import array
from types import SimpleNamespace
from unittest.mock import patch

from maslow_voice.audio import PCM16K, PCM24K, PCM48K, PcmFrame, PortAudioTransport, resample_pcm16


class PcmResamplingTests(unittest.TestCase):
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


class PlaybackTransportTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_duplex_callback_feeds_rendered_speaker_pcm_to_aec_in_ten_ms_frames(self):
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
                await transport.play(PcmFrame(speaker))
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
