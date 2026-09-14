"""Ephemeral, bounded PCM capture and playback.

The PortAudio callbacks only copy samples and schedule bounded queue work. All
networking, provider calls, transcription, and event delivery happen outside
real-time audio callbacks.
"""

from __future__ import annotations

import asyncio
import math
from array import array
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

PCM48K = 48_000
PCM24K = 24_000
PCM16K = 16_000
CHANNELS = 1


@dataclass(frozen=True)
class PcmFrame:
    pcm: bytes
    sample_rate: int = PCM48K
    channels: int = CHANNELS

    def __post_init__(self) -> None:
        if self.sample_rate <= 0 or self.channels != 1 or len(self.pcm) % 2:
            raise ValueError("PCM must be signed 16-bit mono audio")


def resample_pcm16(frame: PcmFrame, sample_rate: int) -> PcmFrame:
    """Linearly resample mono PCM without retaining the source audio."""

    if frame.sample_rate == sample_rate:
        return frame
    if not frame.pcm:
        return PcmFrame(b"", sample_rate)
    output_count = max(1, round(len(frame.pcm) // 2 * sample_rate / frame.sample_rate))
    if not any(frame.pcm):
        return PcmFrame(b"\0" * output_count * 2, sample_rate)
    source = array("h")
    source.frombytes(frame.pcm)
    ratio, remainder = divmod(frame.sample_rate, sample_rate)
    if remainder == 0:
        return PcmFrame(source[:output_count * ratio:ratio].tobytes(), sample_rate)
    target = array("h")
    for index in range(output_count):
        position = index * frame.sample_rate / sample_rate
        left = min(int(position), len(source) - 1)
        right = min(left + 1, len(source) - 1)
        fraction = position - left
        target.append(round(source[left] + (source[right] - source[left]) * fraction))
    return PcmFrame(target.tobytes(), sample_rate)


AudioHandler = Callable[[PcmFrame], Awaitable[None]]


class PortAudioTransport:
    """Raw PortAudio PCM transport with bounded input/output buffers.

    ``sounddevice`` is loaded only when physical audio was explicitly requested,
    keeping typed sessions and tests free from an audio-server dependency.
    ``capture=False`` opens only the speaker for microphone-free previews.
    """

    def __init__(
        self,
        *,
        sample_rate: int = PCM48K,
        blocksize: int = 960,
        queue_frames: int = 32,
        microphone_device: str | int | None = None,
        speaker_device: str | int | None = None,
        on_error: Callable[[], Awaitable[None]] | None = None,
        capture: bool = True,
    ) -> None:
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.microphone_device = microphone_device or None
        self.speaker_device = speaker_device or None
        self._queue: asyncio.Queue[PcmFrame] = asyncio.Queue(maxsize=queue_frames)
        self._output: deque[bytes] = deque(maxlen=queue_frames)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._handler: AudioHandler | None = None
        self._stream: Any = None
        self._pump: asyncio.Task[None] | None = None
        self._muted = False
        self._running = False
        self._played_samples = 0
        self._generation = 0
        self._apm = None
        self._on_error = on_error
        self._capture = capture

    @property
    def played_ms(self):
        return self._played_samples * 1000 // self.sample_rate

    @property
    def played_samples(self) -> int:
        """Exact callback-consumed samples since the last playback clear."""
        return self._played_samples

    @property
    def output_latency_seconds(self) -> float:
        """Bounded callback-to-speaker estimate, with one device block as fallback.

        Some virtual ALSA devices report unsigned-counter underflow as a delay
        of many hours. Such metadata must not prevent a reply from finishing.
        This is a timing estimate, not confirmation of physical speaker output.
        """
        value = getattr(self._stream, "latency", None)
        if isinstance(value, (tuple, list)):
            value = value[-1] if value else None
        block_seconds = self.blocksize / self.sample_rate
        if type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 1:
            return max(block_seconds, float(value))
        return block_seconds

    async def start(self, handler: AudioHandler) -> None:
        if self._running:
            return
        try:
            import sounddevice as sounddevice
            if self._capture:
                from livekit import rtc
        except ImportError as error:
            raise RuntimeError("PortAudio support is not installed") from error
        if self._capture:
            self._apm = rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=True, high_pass_filter=True)
            self._apm.set_stream_delay_ms(30)
            self._loop = asyncio.get_running_loop()
            self._handler = handler
        self._running = True

        def input_callback(indata: Any, rendered: bytes, frames: int) -> None:
            # The callback may never await, perform I/O, or call a provider.
            if self._muted or not self._running or self._loop is None:
                return
            pcm = bytes(indata)
            self._loop.call_soon_threadsafe(self._put_input, (PcmFrame(pcm, self.sample_rate), rendered))

        def output_callback(outdata: Any, frames: int, _time: Any, _status: Any) -> None:
            required = frames * 2
            data = bytearray(required)
            written = 0
            # RTC packets may be shorter than the device callback (10 ms vs
            # 20 ms). Join available PCM before padding a genuine underrun.
            while written < required:
                try:
                    chunk = self._output.popleft()
                except IndexError:
                    break
                count = min(len(chunk), required - written)
                data[written:written + count] = chunk[:count]
                written += count
                if count < len(chunk):
                    self._output.appendleft(chunk[count:])
            self._played_samples += written // 2
            outdata[:] = data
            return bytes(data)

        def callback(indata, outdata, frames, time, status):
            rendered = output_callback(outdata, frames, time, status)
            input_callback(indata, rendered, frames)

        try:
            stream_type = sounddevice.RawStream if self._capture else sounddevice.RawOutputStream
            self._stream = stream_type(
                samplerate=self.sample_rate,
                blocksize=self.blocksize,
                channels=1,
                dtype="int16",
                device=(self.microphone_device, self.speaker_device) if self._capture else self.speaker_device,
                callback=callback if self._capture else output_callback,
            )
            self._stream.start()
        except BaseException:
            self._running = False
            if self._stream is not None:
                self._stream.close()
            self._stream = None
            raise
        if self._capture:
            self._pump = asyncio.create_task(self._run_input())

    def _put_input(self, frame: PcmFrame) -> None:
        if self._capture and self._running and not self._muted and not self._queue.full():
            self._queue.put_nowait(frame)

    async def _run_input(self) -> None:
        try:
            await self._drain_input()
        except asyncio.CancelledError:
            raise
        except Exception:
            # An APM or provider-input failure must not leave physical capture
            # running with a dead consumer or expose raw SDK diagnostics.
            try:
                await self.stop()
            except Exception:
                # stop already attempts close even when the driver rejects it.
                pass
            if self._on_error is not None:
                await self._on_error()

    async def _drain_input(self) -> None:
        while self._running:
            frame, rendered = await self._queue.get()
            if self._handler is not None and not self._muted:
                from livekit import rtc
                # WebRTC APM consumes exactly 10 ms frames. Feed the samples
                # actually sent to the speaker, not a synthesized text estimate.
                size = self.sample_rate // 100 * 2
                cleaned = bytearray()
                for offset in range(0, len(frame.pcm), size):
                    near, far = frame.pcm[offset:offset + size], rendered[offset:offset + size]
                    if len(near) != size or len(far) != size:
                        continue
                    source = rtc.AudioFrame(far, self.sample_rate, 1, size // 2)
                    target = rtc.AudioFrame(near, self.sample_rate, 1, size // 2)
                    self._apm.process_reverse_stream(source)
                    self._apm.process_stream(target)
                    cleaned.extend(bytes(target.data))
                await self._handler(PcmFrame(bytes(cleaned), self.sample_rate))

    async def play(self, frame: PcmFrame) -> None:
        if self._running:
            pcm = resample_pcm16(frame, self.sample_rate).pcm
            generation = self._generation
            size = self.blocksize * 2
            for offset in range(0, len(pcm), size):
                while self._running and generation == self._generation and len(self._output) >= self._output.maxlen:
                    await asyncio.sleep(0.01)
                if not self._running or generation != self._generation:
                    return
                self._output.append(pcm[offset:offset + size])

    async def wait_playback(self):
        while self._running and self._output:
            await asyncio.sleep(0.01)

    async def clear_playback(self) -> None:
        self._generation += 1
        self._output.clear()
        self._played_samples = 0

    async def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if muted:
            while not self._queue.empty():
                self._queue.get_nowait()

    async def stop(self) -> None:
        self._running = False
        self._generation += 1
        self._output.clear()
        while not self._queue.empty():
            self._queue.get_nowait()
        if self._pump is not None:
            if self._pump is not asyncio.current_task():
                self._pump.cancel()
                try:
                    await self._pump
                except asyncio.CancelledError:
                    pass
            self._pump = None
        if self._stream is not None:
            stream, self._stream = self._stream, None
            try:
                stream.stop()
            finally:
                stream.close()
