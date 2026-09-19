"""GPT-Live audio adapter with host-owned client delegation.

Live sends continuous audio and transcript fragments, not Realtime items or
safe work intents. The host owns interpretation, authorization and backend task
lifetime.
"""
from __future__ import annotations

import asyncio
import base64
import json
import math
import uuid
from typing import Any

from maslow_voice.audio import PCM24K, PcmFrame, resample_pcm16
from maslow_voice.voices import LIVE_VOICES
from .base import ProviderError, VoiceProvider
from .openai_realtime import OpenAIRealtimeProvider, _default_socket_factory

CLOSE_REASONS = {"close_requested", "expired", "content", "remote_hangup", "connection_lost"}


class OpenAILiveProvider(VoiceProvider):
    def __init__(self, **kwargs: Any):
        # submit is accepted for compatibility, but never called by this adapter.
        kwargs.setdefault("submit", self._reject_submit)
        super().__init__(**kwargs)
        self._socket_factory = self.config.get("socket_factory", _default_socket_factory)
        # Graceful close can spend up to 15 seconds waiting for the provider's
        # terminal usage event, followed by bounded socket cleanup.
        self.cleanup_timeout = 25
        self._socket = None
        self._reader = self._playback_task = self._silence_task = None
        self._write_lock = None
        self._stop_lock = None
        self._ready = None
        self._finalized = None
        self._session_started = False
        self._closing = False
        self._failure = None
        self._speaking = False
        self._input_silence = bool(self.config.get("live_input_silence", False))
        self._queue = None
        self._queued_bytes = 0
        self._max_audio_bytes = PCM24K * 2 * 60
        self._generation = 0
        self._delegations = set()
        self._pending_context = {}
        self._metrics = self._new_metrics()

    @staticmethod
    async def _reject_submit(*_args):
        raise ProviderError("GPT-Live delegation must be reviewed by the host backend.", "LIVE_HOST_REQUIRED")

    @staticmethod
    def _new_metrics():
        return {"session_started": False, "input_packets": 0, "input_samples": 0,
                "output_packets": 0, "output_samples": 0, "audible_output_samples": 0,
                "input_transcript_deltas": 0, "output_transcript_deltas": 0,
                "delegations": 0, "context_appends": 0, "context_acks": 0, "errors": 0,
                "usage_updates": 0, "usage_seconds": None, "finalized": False,
                "closed_reason": None, "last_error_code": None}

    def metrics_snapshot(self):
        """No account values, session/delegation IDs, raw events or transcript."""
        return dict(self._metrics)

    @staticmethod
    def _public_error(error):
        return OpenAIRealtimeProvider._public_error(error)

    def _session_config(self):
        voice = self.config.get("live_voice", "marin")
        if voice not in LIVE_VOICES:
            raise ProviderError("Choose an available GPT-Live voice.", "LIVE_VOICE_INVALID")
        instructions = self.config.get("live_instructions", (
            "You are Maslow's concise English voice coordinator. Converse naturally. "
            "Delegate requests that need research, reasoning or actions to the client backend. "
            "Never claim that work completed until the backend confirms it. "
            "Speaking interruptions do not cancel backend work."
        ))
        if not isinstance(instructions, str) or not instructions.strip() or len(instructions.encode("utf-8")) > 8000:
            raise ProviderError("Provide concise GPT-Live conversation instructions.", "LIVE_INSTRUCTIONS_INVALID")
        return {"model": "gpt-live-1", "instructions": instructions, "store": False,
                "audio": {"format": {"type": "audio/pcm", "rate": PCM24K}, "output": {"voice": voice}},
                "delegation": {"type": "client"}}

    async def start(self, audio=True):
        if self._started:
            return
        self._ready = asyncio.Event()
        self._finalized = asyncio.Event()
        self._queue = asyncio.Queue(maxsize=6000)
        self._closing = self._session_started = False
        self._failure = None
        self._muted = self._speaking = False
        self._metrics = self._new_metrics()
        self._delegations.clear()
        self._pending_context.clear()
        await self._voice_state("connecting")
        try:
            session = self._session_config()
            key = self.secrets.get("openai", "")
            if not key:
                raise ProviderError("Save an OpenAI account before starting GPT-Live.", "OPENAI_AUTH_FAILED")
            self._socket = await self._socket_factory("wss://api.openai.com/v1/live/sessions", {"Authorization": f"Bearer {key}"})
            # Register the receiver before commands so terminal events cannot race it.
            self._reader = asyncio.create_task(self._read_events())
            await self._send({"type": "session.start", "event_id": uuid.uuid4().hex, "session": session})
            await asyncio.wait_for(self._ready.wait(), 20)
            if self._failure:
                raise self._failure
            if self._closing or self._finalized.is_set():
                raise asyncio.CancelledError()
            self._started = True
            self._audio_enabled = bool(audio and not self._input_silence)
            if audio and self.audio_transport is not None:
                await self.audio_transport.set_muted(False)
                await self.audio_transport.start(self._on_audio)
                self._playback_task = asyncio.create_task(self._play_audio())
            self._silence_task = asyncio.create_task(self._pace_silence())
            await self._voice_state()
        except asyncio.CancelledError:
            await self.stop()
            raise
        except Exception as error:
            public = self._public_error(error)
            if self._failure is None:
                self._metrics["errors"] += 1
                self._metrics["last_error_code"] = public.code
            await self.stop()
            await self._error(public)
            raise public from error

    async def _voice_state(self, state=None):
        listening = bool(self._started and not self._closing)
        await self._event({"type": "voice_state", "state": state or ("speaking" if self._speaking else "listening" if listening else "disabled"),
                           "listening": listening, "speaking": bool(self._speaking and listening),
                           "microphone": bool(listening and self._audio_enabled and not self._muted)})

    async def _send(self, event):
        if self._socket is None:
            raise ProviderError("Start GPT-Live before sending an update.", "LIVE_NOT_STARTED")
        if self._write_lock is None:
            self._write_lock = asyncio.Lock()
        async with self._write_lock:
            await asyncio.wait_for(self._socket.send(json.dumps(event, separators=(",", ":"))), 10)

    async def _on_audio(self, frame):
        if not self._started or self._closing:
            return
        if self._muted or self._input_silence:
            return  # The independent paced-zero task preserves frame progress.
        await self._level(frame)
        await self._send_pcm(resample_pcm16(frame, PCM24K))

    async def _send_pcm(self, frame):
        if frame.pcm and self._started and not self._closing:
            await self._send({"type": "session.input_audio.append", "audio": base64.b64encode(frame.pcm).decode("ascii")})
            self._metrics["input_packets"] += 1
            self._metrics["input_samples"] += len(frame.pcm) // 2

    async def _pace_silence(self):
        try:
            frame = PcmFrame(b"\0" * 960, PCM24K)  # 20 ms, never sent as a burst.
            while self._started and not self._closing:
                if self._input_silence or self._muted:
                    await self._send_pcm(frame)
                await asyncio.sleep(.02)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._fail(error)

    async def append_context(self, kind, content, delegation_id=None):
        if not self._started or self._closing:
            raise ProviderError("This GPT-Live session has ended. Keep task results in the host.", "LIVE_SESSION_ENDED")
        if kind not in {"thinking", "commentary", "instructions"}:
            raise ProviderError("Choose thinking, commentary or instructions for this update.", "LIVE_CONTEXT_INVALID")
        # A conservative UTF-8 byte limit stays within 500 tokens without a new
        # tokenizer dependency. The host can split longer verified summaries.
        if not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > 500:
            raise ProviderError("Keep each GPT-Live update within 500 UTF-8 bytes.", "LIVE_CONTEXT_TOO_LONG")
        if delegation_id is not None and (not isinstance(delegation_id, str) or delegation_id not in self._delegations):
            raise ProviderError("That update does not belong to a known client delegation.", "LIVE_DELEGATION_UNKNOWN")
        if len(self._pending_context) >= 64:
            raise ProviderError("Wait for pending GPT-Live context updates to be acknowledged.", "LIVE_CONTEXT_BUSY")
        event_id = uuid.uuid4().hex
        self._pending_context[event_id] = kind
        try:
            await self._send({"type": f"session.{kind}.append", "event_id": event_id, "delegation_id": delegation_id, "content": content})
        except asyncio.CancelledError:
            self._pending_context.pop(event_id, None)
            raise
        except Exception as error:
            self._pending_context.pop(event_id, None)
            raise self._public_error(error) from error
        except BaseException:
            self._pending_context.pop(event_id, None)
            raise
        self._metrics["context_appends"] += 1
        return event_id

    async def text(self, text, context=""):
        raise ProviderError("Send typed requests to the host backend; GPT-Live has no text-turn API.", "LIVE_HOST_REQUIRED")

    async def mute(self, muted):
        if not self._started or self._closing:
            return
        self._muted = bool(muted)
        if self.audio_transport is not None:
            await self.audio_transport.set_muted(self._muted)
        await self._send({"type": "session.input_audio.mute" if muted else "session.input_audio.unmute", "event_id": uuid.uuid4().hex})
        await self._voice_state()  # Local capture state; server acknowledgment is separate.

    async def silence(self):
        # No response.cancel exists here: speech and host task lifetime differ.
        self._clear_output()
        self._speaking = False
        if self.audio_transport is not None:
            await self.audio_transport.clear_playback()
        if self._started and not self._closing:
            await self._voice_state()

    def _clear_output(self):
        self._generation += 1
        if self._queue is None:
            self._queued_bytes = 0
            return
        while not self._queue.empty():
            self._queue.get_nowait()
            self._queue.task_done()
        self._queued_bytes = 0

    async def _play_audio(self):
        try:
            while self._started and not self._closing:
                generation, pcm = await self._queue.get()
                self._queued_bytes -= len(pcm)
                try:
                    if generation != self._generation:
                        continue
                    audible = any(abs(value) > 50 for value in memoryview(pcm).cast("h"))
                    if audible != self._speaking:
                        if not audible:
                            await self.audio_transport.wait_playback()
                        if generation != self._generation:
                            continue
                        self._speaking = audible
                        await self._voice_state()
                    await self.audio_transport.play(PcmFrame(pcm, PCM24K))
                finally:
                    self._queue.task_done()
                if self._queue.empty():
                    await self.audio_transport.wait_playback()
                    if self._queue.empty() and generation == self._generation and self._speaking:
                        self._speaking = False
                        await self._voice_state()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._fail(error)

    async def wait_playback(self):
        if self._queue is not None:
            await self._queue.join()
        if self.audio_transport is not None:
            await self.audio_transport.wait_playback()
        if self._failure:
            raise self._failure

    async def _read_events(self):
        try:
            while self._socket is not None and self._finalized is not None and not self._finalized.is_set():
                raw = await self._socket.recv()
                await self._handle_event(json.loads(raw))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if self._finalized is None or not self._finalized.is_set():
                await self._fail(error)

    @staticmethod
    def _time(value):
        return value if type(value) in {int, float} and math.isfinite(value) and value >= 0 else None

    def _usage(self, event):
        seconds = self._time((event.get("usage") or {}).get("seconds"))
        if seconds is not None:
            self._metrics["usage_seconds"] = seconds  # Cumulative snapshot, never sum.

    async def _handle_event(self, event):
        kind = event.get("type")
        if kind == "session.started":
            self._session_started = True
            self._metrics["session_started"] = True
            if self._ready is not None:
                self._ready.set()
        elif kind == "session.output_audio.delta" and self._started and not self._closing:
            pcm = base64.b64decode(event.get("delta", ""), validate=True)
            if len(pcm) % 2:
                raise ProviderError("GPT-Live sent an invalid audio frame.", "LIVE_AUDIO_INVALID")
            self._metrics["output_packets"] += 1
            self._metrics["output_samples"] += len(pcm) // 2
            self._metrics["audible_output_samples"] += sum(abs(value) > 50 for value in memoryview(pcm).cast("h"))
            if pcm and self._playback_task is not None:
                if self._queue.full() or self._queued_bytes + len(pcm) > self._max_audio_bytes:
                    await self._fail(ProviderError("GPT-Live audio exceeded the bounded playback buffer.", "LIVE_AUDIO_BACKLOG"))
                    return
                self._queued_bytes += len(pcm)
                self._queue.put_nowait((self._generation, pcm))
        elif kind in {"session.input_transcript.delta", "session.output_transcript.delta"}:
            role = "user" if kind == "session.input_transcript.delta" else "assistant"
            delta = event.get("delta")
            if isinstance(delta, str):
                counter = "input_transcript_deltas" if role == "user" else "output_transcript_deltas"
                self._metrics[counter] += 1
                await self._event({"type": "transcript_delta", "role": role, "delta": delta,
                                   "start_ms": self._time(event.get("start_ms")), "end_ms": self._time(event.get("end_ms"))})
        elif kind == "session.delegation.created":
            delegation = event.get("delegation") or {}
            identity = delegation.get("id")
            if delegation.get("target") == "client" and isinstance(identity, str) and 0 < len(identity) <= 256 and identity not in self._delegations:
                if len(self._delegations) >= 512:
                    await self._fail(ProviderError("This GPT-Live session reached its delegation limit. Start a new session.", "LIVE_DELEGATION_LIMIT"))
                    return
                self._delegations.add(identity)
                self._metrics["delegations"] += 1
                if not self._closing:
                    await self._event({"type": "delegation", "delegation_id": identity, "offset_ms": self._time(event.get("offset_ms"))})
        elif kind in {"session.thinking.appended", "session.commentary.appended", "session.instructions.appended"}:
            identity = event.get("client_event_id")
            context_kind = self._pending_context.pop(identity, None)
            if context_kind:
                self._metrics["context_acks"] += 1
                await self._event({"type": "context_ack", "kind": context_kind, "client_event_id": identity, "accepted": True,
                                   "start_ms": self._time(event.get("start_ms")), "end_ms": self._time(event.get("end_ms"))})
        elif kind in {"session.input_audio.muted", "session.input_audio.unmuted"}:
            await self._event({"type": "input_control_ack", "muted": kind.endswith(".muted")})
        elif kind == "session.usage.updated":
            self._metrics["usage_updates"] += 1
            self._usage(event)
        elif kind == "session.closed":
            self._usage(event)
            self._metrics["finalized"] = True
            reason = event.get("reason")
            self._metrics["closed_reason"] = reason if reason in CLOSE_REASONS else "other"
            if self._finalized is not None:
                self._finalized.set()
            if self._ready is not None:
                self._ready.set()
            self._started = self._audio_enabled = self._speaking = False
            self._clear_output()
            await self._event({"type": "closed", "finalized": True, "reason": self._metrics["closed_reason"], "usage_seconds": self._metrics["usage_seconds"]})
            if not self._closing:
                if self.audio_transport is not None:
                    await self.audio_transport.stop()
                await self._voice_state("disabled")
        elif kind == "error":
            error = event.get("error") or {}
            public = self._public_error(error)
            identity = error.get("client_event_id")
            context_kind = self._pending_context.pop(identity, None)
            if not self._session_started:
                await self._fail(public)
            else:
                self._metrics["errors"] += 1
                self._metrics["last_error_code"] = public.code
                if context_kind:
                    await self._event({"type": "context_ack", "kind": context_kind, "client_event_id": identity, "accepted": False,
                                       "code": public.code, "message": public.message})
                else:
                    # A command/moderation error need not close Live. Only the
                    # terminal event or transport failure establishes that boundary.
                    await self._event({"type": "notice", "code": public.code, "message": public.message})

    async def _fail(self, error):
        if self._failure:
            return
        self._failure = self._public_error(error)
        self._metrics["errors"] += 1
        self._metrics["last_error_code"] = self._failure.code
        self._started = self._audio_enabled = self._speaking = False
        if self._ready is not None:
            self._ready.set()
        self._clear_output()
        try:
            if self.audio_transport is not None:
                await self.audio_transport.stop()
        except Exception:
            pass
        await self._error(self._failure)

    async def stop(self):
        if self._stop_lock is None:
            self._stop_lock = asyncio.Lock()
        async with self._stop_lock:
            self._closing = True
            self._started = self._audio_enabled = self._speaking = False
            if self._ready is not None:
                self._ready.set()
            if self._silence_task is not None:
                self._silence_task.cancel()
                await asyncio.gather(self._silence_task, return_exceptions=True)
                self._silence_task = None
            try:
                if self.audio_transport is not None:
                    await asyncio.wait_for(self.audio_transport.stop(), 2)
            except Exception:
                pass
            try:
                if self._socket is not None and self._session_started and self._finalized is not None and not self._finalized.is_set() and not self._failure:
                    await asyncio.wait_for(self._send({"type": "session.close", "event_id": uuid.uuid4().hex}), 2)
                    await asyncio.wait_for(self._finalized.wait(), self.config.get("live_close_timeout", 15))
            except Exception:
                pass
            finally:
                owned = [task for task in (self._reader, self._playback_task) if task is not None and task is not asyncio.current_task()]
                for task in owned:
                    task.cancel()
                await asyncio.gather(*owned, return_exceptions=True)
                self._reader = self._playback_task = None
                self._clear_output()
                self._pending_context.clear()
                self._delegations.clear()
                if self._socket is not None:
                    socket, self._socket = self._socket, None
                    try:
                        await asyncio.wait_for(socket.close(), 3)
                    except Exception:
                        pass
                await self._voice_state("disabled")
                if self._session_started and self._finalized is not None and not self._finalized.is_set():
                    await self._event({"type": "closed", "finalized": False, "reason": "unconfirmed", "usage_seconds": self._metrics["usage_seconds"]})
