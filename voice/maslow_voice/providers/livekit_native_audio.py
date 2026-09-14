"""Direct AgentSession audio I/O for the native LiveKit provider.

This module is imported only by ``LiveKitNativeExpressiveProvider.start(audio=True)``.
It deliberately owns no device: ``PortAudioTransport`` remains the sole physical
48 kHz duplex transport and retains WebRTC APM processing.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
import time
from typing import Any

from livekit import rtc
from livekit.agents.voice import io as voice_io

from maslow_voice.audio import PCM48K, PcmFrame
from maslow_voice.providers.base import ProviderError

INPUT_QUEUE_FRAMES = 2
MIN_OUTPUT_TAIL_SECONDS = 0.020


class NativeAgentAudioInput(voice_io.AudioInput):
    """A bounded input iterator with generation-safe mute and shutdown."""

    def __init__(self) -> None:
        super().__init__(label="Maslow native microphone")
        self._frames: asyncio.Queue[rtc.AudioFrame | None] = asyncio.Queue(maxsize=INPUT_QUEUE_FRAMES)
        self._space = asyncio.Event()
        self._space.set()
        self._closed = False
        self._generation = 0

    async def push_frame(self, frame: rtc.AudioFrame) -> bool:
        if frame.sample_rate != PCM48K or frame.num_channels != 1:
            raise ProviderError("Native LiveKit audio requires 48 kHz mono PCM")
        generation = self._generation
        while True:
            if self._closed:
                raise asyncio.CancelledError
            if generation != self._generation:
                return False
            if not self._frames.full():
                # The lifecycle validation and put are deliberately adjacent:
                # a muted generation can never enqueue a stale frame after wakeup.
                self._frames.put_nowait(frame)
                if self._frames.full():
                    self._space.clear()
                return True
            await self._space.wait()

    def discard(self) -> None:
        """Invalidate queued and blocked producer frames without blocking audio."""

        self._generation += 1
        while not self._frames.empty():
            self._frames.get_nowait()
        self._space.set()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.discard()
        self._frames.put_nowait(None)
        self._space.set()

    async def __anext__(self) -> rtc.AudioFrame:
        frame = await self._frames.get()
        self._space.set()
        if frame is None:
            raise StopAsyncIteration
        return frame


class NativeAgentAudioSource:
    """Source-shaped bridge that preserves the provider's normal APM callback."""

    def __init__(self, audio_input: NativeAgentAudioInput) -> None:
        self._input = audio_input

    @property
    def queued_duration(self) -> float:
        return self._input._frames.qsize() * 0.020

    async def capture_frame(self, frame: rtc.AudioFrame) -> None:
        await self._input.push_frame(frame)

    def clear_queue(self) -> None:
        self._input.discard()

    async def aclose(self) -> None:
        self._input.close()


@dataclass
class _Playback:
    start_played_samples: int
    samples: int = 0
    interrupted_played_samples: int | None = None


class NativeAgentAudioOutput(voice_io.AudioOutput):
    """PortAudio sink that reports exact playback completion to AgentSession."""

    def __init__(self, transport: Any) -> None:
        super().__init__(
            label="Maslow native speaker",
            capabilities=voice_io.AudioOutputCapabilities(pause=False),
            next_in_chain=None,
            sample_rate=PCM48K,
        )
        self._transport = transport
        self._playback: _Playback | None = None
        self._flushing: _Playback | None = None
        self._flush_task: asyncio.Task[None] | None = None
        self._clear_task: asyncio.Task[None] | None = None
        self._interrupted = asyncio.Event()
        self._closed = False

    def _played_samples(self) -> int:
        value = getattr(self._transport, "played_samples", None)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        raise ProviderError("Native LiveKit playback accounting is unavailable")

    def _tail_seconds(self) -> float:
        value = getattr(self._transport, "output_latency_seconds", None)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1:
            return max(MIN_OUTPUT_TAIL_SECONDS, float(value))
        return MIN_OUTPUT_TAIL_SECONDS

    async def capture_frame(self, frame: rtc.AudioFrame) -> None:
        if self._closed:
            return
        if frame.sample_rate != PCM48K or frame.num_channels != 1:
            raise ProviderError("Native LiveKit audio requires 48 kHz mono PCM")
        if self._flush_task is not None and not self._flush_task.done():
            await self._flush_task
        if self._clear_task is not None and not self._clear_task.done():
            await self._clear_task
        # aclose() may have completed while this call waited for a prior
        # segment. Do not let that stale producer start a new output segment.
        if self._closed:
            return
        await super().capture_frame(frame)
        if self._playback is None:
            self._playback = _Playback(start_played_samples=self._played_samples())
            self.on_playback_started(created_at=time.time())
        self._playback.samples += frame.samples_per_channel
        await self._transport.play(PcmFrame(bytes(frame.data), frame.sample_rate, frame.num_channels))

    def flush(self) -> None:
        super().flush()
        if self._closed or self._playback is None:
            return
        if self._flush_task is not None and not self._flush_task.done():
            return
        self._interrupted.clear()
        self._flushing, self._playback = self._playback, None
        self._flush_task = asyncio.create_task(self._finish_playback(self._flushing))

    def clear_buffer(self) -> None:
        """Interrupt one current segment and request an idempotent device clear."""

        if self._closed:
            return
        consumed_before_clear = self._played_samples()
        self._interrupted.set()
        for playback in (self._flushing, self._playback):
            if playback is not None and playback.interrupted_played_samples is None:
                playback.interrupted_played_samples = consumed_before_clear
        if self._clear_task is None or self._clear_task.done():
            self._clear_task = asyncio.create_task(self._clear_transport())
        if self._playback is not None and (self._flush_task is None or self._flush_task.done()):
            self._flushing, self._playback = self._playback, None
            self._flush_task = asyncio.create_task(self._finish_playback(self._flushing))
        super().flush()

    async def _clear_transport(self) -> None:
        await self._transport.clear_playback()

    async def _finish_playback(self, playback: _Playback) -> None:
        target_samples = playback.start_played_samples + playback.samples
        interrupted = False
        while True:
            if self._interrupted.is_set() or self._closed:
                interrupted = True
                break
            if self._played_samples() >= target_samples:
                try:
                    await asyncio.wait_for(self._interrupted.wait(), timeout=self._tail_seconds())
                    interrupted = True
                except TimeoutError:
                    pass
                break
            await asyncio.sleep(0.005)
        observed = playback.interrupted_played_samples if interrupted and playback.interrupted_played_samples is not None else self._played_samples()
        position = min(playback.samples / PCM48K, max(0.0, (observed - playback.start_played_samples) / PCM48K))
        self.on_playback_finished(playback_position=position, interrupted=interrupted)
        if self._flushing is playback:
            self._flushing = None
        self._interrupted.clear()

    async def aclose(self) -> None:
        if self._closed:
            return
        self.clear_buffer()
        self._closed = True
        errors: list[BaseException] = []
        for task in (self._flush_task, self._clear_task):
            if task is not None:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as error:
                    errors.append(error)
        if errors:
            raise errors[0]
