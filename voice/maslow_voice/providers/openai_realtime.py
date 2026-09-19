"""Direct OpenAI Realtime WebSocket provider.

The adapter uses the protocol directly so microphone PCM, cancellation, and
truncation are observable and testable instead of being hidden behind a UI SDK.
"""

from __future__ import annotations

import asyncio
import base64
import json
import uuid
from urllib.parse import urlencode
from collections.abc import AsyncIterator
from typing import Any, Protocol

from maslow_voice.audio import PCM24K, PcmFrame, resample_pcm16
from maslow_voice.voices import OPENAI_VOICES

from .base import ProviderError, VoiceProvider, validate_intent


class RealtimeSocket(Protocol):
    async def send(self, message: str) -> None: ...
    async def recv(self) -> str | bytes: ...
    async def close(self) -> None: ...


class SocketFactory(Protocol):
    async def __call__(self, url: str, headers: dict[str, str]) -> RealtimeSocket: ...


INTENT_TOOL = {
    "type": "function",
    "name": "submit_intent",
    "description": "Submit a safe work intent. Never perform work or call any other tool.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "required": ["objective", "summary", "constraints", "requested_output", "tool_preference", "unresolved_questions"],
        "properties": {
            "objective": {"type": "string"},
            "summary": {"type": "string"},
            "constraints": {"type": "array", "items": {"type": "string"}},
            "requested_output": {"type": "string"},
            "tool_preference": {"type": "string", "enum": ["auto", "codex", "claude", "hermes"]},
            "unresolved_questions": {"type": "array", "items": {"type": "string"}},
        },
    },
}


async def _default_socket_factory(url: str, headers: dict[str, str]) -> RealtimeSocket:
    try:
        from websockets.asyncio.client import connect
    except ImportError as error:
        raise ProviderError("OpenAI Realtime support is not installed") from error
    return await connect(url, additional_headers=headers)


class OpenAIRealtimeProvider(VoiceProvider):
    """A native 24 kHz PCM OpenAI Realtime session with interrupt handling."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._socket_factory: SocketFactory = self.config.get("socket_factory", _default_socket_factory)
        self._socket: RealtimeSocket | None = None
        self._reader: asyncio.Task[None] | None = None
        self._write_lock = asyncio.Lock()
        self._assistant_item_id: str | None = None
        self._played_ms = 0
        self._ready = asyncio.Event()
        self._response_active = False
        self._start_failure = False
        self._response_turns = {}
        self._typed_waiters = {}
        self._cancelled_responses = set()
        self._active_response_id = None
        self._transcribed = {}
        self._tool_tasks = set()
        self._drain_tasks = set()
        self._stop_lock = asyncio.Lock()
        self._playback_queue = asyncio.Queue(maxsize=6000)
        self._playback_task = None
        self._queued_audio_bytes = 0
        # At 24 kHz mono PCM16 this retains at most 60 seconds of generated
        # audio while keeping socket/VAD/error handling independent of playback.
        self._max_audio_bytes = PCM24K * 2 * 60
        self._playback_item_id = None
        self._item_played_start = 0
        self._audio_generation = 0

    async def start(self, audio: bool = True) -> None:
        if self._started:
            return
        self._ready.clear()
        self._start_failure = None
        self._muted = False
        key = self.secrets.get("openai", "")
        if not key:
            await self._raise_start_error(ProviderError("OpenAI credentials are unavailable"), "OpenAI Voice is not ready")
        await self._state_event("connecting", microphone=False)
        model = str(self.config.get("realtime_model", "gpt-realtime-2.1"))
        url = "wss://api.openai.com/v1/realtime?" + urlencode({"model": model})
        try:
            session = self._session_config(model, audio)
            self._socket = await self._socket_factory(url, {"Authorization": f"Bearer {key}"})
            self._started = True
            await self._send({"type": "session.update", "session": session})
            self._reader = asyncio.create_task(self._read_events())
            await asyncio.wait_for(self._ready.wait(), 15)
            if self._start_failure:
                raise self._start_failure
            if not self._started:
                raise asyncio.CancelledError()
            if audio and self.audio_transport is not None:
                await self.audio_transport.set_muted(False)
                await self.audio_transport.start(self._on_audio)
                self._playback_task = asyncio.create_task(self._play_audio())
            self._audio_enabled = audio
            await self._state_event("listening", microphone=audio)
        except asyncio.CancelledError:
            try:
                await self.stop()
            except Exception:
                pass
            raise
        except Exception as error:
            public = self._public_error(error)
            try:
                await self.stop()
            except Exception:
                pass
            await self._error(public)
            raise public from error

    @staticmethod
    def _public_error(error: Any) -> ProviderError:
        if isinstance(error, ProviderError):
            return error
        detail = error if isinstance(error, dict) else {}
        status = getattr(error, "status_code", None) or getattr(getattr(error, "response", None), "status_code", None)
        codes = {value for value in (detail.get("code"), detail.get("type")) if isinstance(value, str)}
        if status in {401, 403} or codes & {"invalid_api_key", "invalid_authentication", "authentication_error", "permission_denied"}:
            return ProviderError("OpenAI denied access. Verify the saved account and project permissions in Settings.", "OPENAI_AUTH_FAILED")
        if status in {402, 429} or codes & {"insufficient_quota", "rate_limit_exceeded", "rate_limit_error", "billing_hard_limit_reached"}:
            return ProviderError("OpenAI usage is unavailable. Check project billing and usage limits, then try again.", "OPENAI_USAGE_LIMIT")
        if type(error).__name__ == "PortAudioError":
            return ProviderError("Microphone or speaker access failed. Check device selection and microphone permission, then try again.", "AUDIO_UNAVAILABLE")
        if codes & {"invalid_request_error", "model_not_found", "unsupported_value", "invalid_value", "unknown_parameter"}:
            if detail.get("param") == "item.id":
                return ProviderError("OpenAI rejected a message identifier. Update Voice and try again.", "OPENAI_ITEM_ID_INVALID")
            return ProviderError("OpenAI rejected the Voice setup. Check the selected model and voice in Settings.", "OPENAI_SETUP_FAILED")
        if codes & {"server_error", "internal_server_error"}:
            return ProviderError("OpenAI could not process this turn. Try again shortly.", "OPENAI_SERVICE_FAILED")
        if isinstance(error, (TypeError, AttributeError, ValueError, KeyError)):
            return ProviderError("OpenAI Voice encountered a local protocol error. Restart the tester after updating Voice.", "OPENAI_PROTOCOL_FAILED")
        return ProviderError("OpenAI Voice stopped. Check internet access and project setup, then start talking again.", "OPENAI_SESSION_FAILED")

    async def _fail(self, error: Any) -> None:
        if self._start_failure:
            return
        self._start_failure = self._public_error(error)
        self._started = False
        self._audio_enabled = False
        self._ready.set()
        self._clear_pending_audio()
        for waiter in self._typed_waiters.values():
            if not waiter.done():
                waiter.set_result(None)
        try:
            if self.audio_transport is not None:
                await self.audio_transport.stop()
        except Exception:
            pass
        await self._error(self._start_failure)

    def _session_config(self, model: str, audio: bool) -> dict[str, Any]:
        voice = self.config.get("realtime_voice", "cedar")
        if voice not in OPENAI_VOICES:
            raise ProviderError("Choose one of the available OpenAI voices.", "OPENAI_VOICE_INVALID")
        if not audio:
            return {
                "type": "realtime",
                "model": model,
                "output_modalities": ["text"],
                "tools": [INTENT_TOOL],
                "tool_choice": "auto",
                "instructions": self._instructions(),
            }
        return {
            "type": "realtime",
            "model": model,
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": PCM24K},
                    "transcription": {"model": "gpt-4o-mini-transcribe", "language": "en"},
                    "turn_detection": {"type": "server_vad", "create_response": False, "interrupt_response": False},
                },
                "output": {"format": {"type": "audio/pcm", "rate": PCM24K}, "voice": voice},
            },
            "tools": [INTENT_TOOL],
            "tool_choice": "auto",
            "instructions": self._instructions(),
        }

    @staticmethod
    def _instructions() -> str:
        return (
            "You coordinate work but never execute it. Speak concise English. "
            "Answer greetings and ordinary questions conversationally without creating tasks. "
            "Only when the user clearly asks to DO work, call submit_intent with all required fields. "
            "If work scope is ambiguous, ask a concise question first; do not submit unresolved questions. "
            "Use no other tools, commands, endpoints, permissions, or executable parameters. "
            "Ask a concise question when necessary information is missing."
        )

    async def stop(self) -> None:
        async with self._stop_lock:
            # Revoke capture and tool authority before awaiting any cleanup.
            self._started = False
            self._audio_enabled = False
            self._ready.set()
            errors = []
            if self.audio_transport is not None:
                try:
                    await self.audio_transport.stop()
                except Exception as error:
                    errors.append(error)
            owned = [task for task in (self._reader, self._playback_task, *self._tool_tasks, *self._drain_tasks)
                     if task is not None and task is not asyncio.current_task()]
            for task in owned:
                task.cancel()
            await asyncio.gather(*owned, return_exceptions=True)
            self._reader = self._playback_task = None
            self._tool_tasks.clear()
            self._drain_tasks.clear()
            self._clear_pending_audio()
            for waiter in self._typed_waiters.values():
                if not waiter.done():
                    waiter.set_result(None)
            self._typed_waiters.clear()
            self._response_turns.clear()
            self._transcribed.clear()
            self._cancelled_responses.clear()
            self._response_active = False
            self._active_response_id = None
            self._assistant_item_id = self._playback_item_id = None
            try:
                await self._close_socket()
            except Exception as error:
                errors.append(error)
            await self._state_event("disabled", microphone=False)
            if errors:
                raise self._public_error(errors[0])

    async def _close_socket(self) -> None:
        if self._socket is not None:
            try:
                await self._socket.close()
            finally:
                self._socket = None

    async def text(self, text: str, context: str = "") -> None:
        if not self._started:
            await self._error(ProviderError("Start Voice before sending a message"))
            return
        value = text.strip()
        if not value:
            return
        turn_id = await self._user_turn(value, uuid.uuid4().hex)
        self._transcribed.setdefault(turn_id, asyncio.Event()).set()
        await self._state_event("thinking", microphone=False)
        content = value if not context else f"Context: {context}\n\nUser: {value}"
        waiter = asyncio.get_running_loop().create_future()
        self._typed_waiters[turn_id] = waiter
        try:
            await self._send({"type": "conversation.item.create", "item": {"id": turn_id, "type": "message", "role": "user", "content": [{"type": "input_text", "text": content}]}})
            await self._create_response(turn_id)
            await asyncio.wait_for(waiter, 180)
            if self._start_failure:
                raise self._start_failure
        finally:
            self._typed_waiters.pop(turn_id, None)

    async def _create_response(self, turn_id):
        await self._send({"type": "response.create", "response": {"metadata": {"maslow_turn_id": turn_id}}})

    async def _on_audio(self, frame: PcmFrame) -> None:
        if not self._started or self._muted:
            return
        await self._level(frame)
        pcm = resample_pcm16(frame, PCM24K).pcm
        if pcm:
            await self._send({"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm).decode("ascii")})

    async def silence(self) -> None:
        item_id = self._playback_item_id or self._assistant_item_id
        played_ms = max(0, getattr(self.audio_transport, "played_ms", 0) - self._item_played_start) if self._playback_item_id else 0
        cancel_response = self._response_active
        self._response_active = False
        if self._active_response_id:
            self._cancelled_responses.add(self._active_response_id)
        # Stop local sound before network writes, including a producer currently
        # waiting for space in the transport queue.
        self._clear_pending_audio()
        await super().silence()
        if self._started:
            if cancel_response:
                await self._send({"type": "response.cancel"})
            if item_id is not None:
                await self._send({
                    "type": "conversation.item.truncate",
                    "item_id": item_id,
                    "content_index": 0,
                    "audio_end_ms": played_ms,
                })
        self._assistant_item_id = self._playback_item_id = None
        self._played_ms = 0

    def _clear_pending_audio(self):
        self._audio_generation += 1
        while not self._playback_queue.empty():
            self._playback_queue.get_nowait()
            self._playback_queue.task_done()
        self._queued_audio_bytes = 0

    async def _play_audio(self):
        try:
            while self._started:
                generation, item_id, pcm = await self._playback_queue.get()
                self._queued_audio_bytes -= len(pcm)
                try:
                    if generation != self._audio_generation:
                        continue
                    if item_id != self._playback_item_id:
                        # A prior item may still be queued in PortAudio. Its
                        # elapsed playback must not count toward this item.
                        wait = getattr(self.audio_transport, "wait_playback", None)
                        if wait is not None:
                            await wait()
                        if generation != self._audio_generation:
                            continue
                        self._playback_item_id = item_id
                        self._item_played_start = getattr(self.audio_transport, "played_ms", 0)
                    await self.audio_transport.play(PcmFrame(pcm, PCM24K))
                finally:
                    self._playback_queue.task_done()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if self._started:
                await self._fail(error)

    async def wait_playback(self):
        await self._playback_queue.join()
        wait = getattr(self.audio_transport, "wait_playback", None)
        if wait is not None:
            await wait()
        if self._start_failure:
            raise self._start_failure

    async def _finish_playback(self, generation, response_id):
        try:
            await self.wait_playback()
            if (self._started and generation == self._audio_generation
                    and response_id == self._active_response_id and not self._response_active):
                await self._state_event("listening", microphone=self._audio_enabled and not self._muted)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if self._started:
                await self._fail(error)

    async def _send(self, event: dict[str, Any]) -> None:
        if self._socket is None:
            raise ProviderError("OpenAI Realtime is not connected")
        async with self._write_lock:
            await self._socket.send(json.dumps(event, separators=(",", ":")))

    async def _read_events(self) -> None:
        try:
            while self._started and self._socket is not None:
                raw = await self._socket.recv()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                await self._handle_event(json.loads(raw))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if self._started:
                await self._fail(error)

    async def _handle_event(self, event: dict[str, Any]) -> None:
        if not self._started:
            return
        event_type = event.get("type")
        response_id = event.get("response_id")
        if response_id in self._cancelled_responses and event_type not in {"response.done", "response.cancelled"}:
            return
        if event_type == "session.updated":
            self._ready.set()
        elif event_type == "error":
            await self._fail(event.get("error") or {})
        elif event_type == "input_audio_buffer.speech_started":
            # VAD is factual: a user began speaking while output might be active.
            await self.silence()
        elif event_type == "input_audio_buffer.committed":
            # VAD still commits/transcribes audio; explicit response creation
            # echoes its exact input identity instead of guessing event order.
            item_id = event.get("item_id")
            if isinstance(item_id, str) and item_id:
                await self._create_response(item_id)
        elif event_type in {"response.created", "response.output_item.added"}:
            if event_type == "response.created":
                response = event.get("response") or {}
                response_id = response.get("id")
                self._active_response_id = response_id
                explicit_turn = (response.get("metadata") or {}).get("maslow_turn_id")
                if response_id and explicit_turn:
                    self._response_turns[response_id] = explicit_turn
                    if len(self._response_turns) > 100:
                        self._response_turns.pop(next(iter(self._response_turns)))
            self._response_active = True
            await self._state_event("thinking", microphone=False)
            item = event.get("item", {})
            if item.get("role") == "assistant":
                self._assistant_item_id = item.get("id")
        elif event_type in {"response.audio.delta", "response.output_audio.delta"}:
            encoded = event.get("delta", "")
            if isinstance(encoded, str) and self.audio_transport is not None and self._audio_enabled:
                pcm = base64.b64decode(encoded, validate=True)
                if not pcm:
                    return
                if len(pcm) % 2:
                    raise ProviderError("OpenAI sent an unsupported audio format. Start a new conversation.", "OPENAI_AUDIO_INVALID")
                if self._queued_audio_bytes + len(pcm) > self._max_audio_bytes or self._playback_queue.full():
                    await self._fail(ProviderError("OpenAI sent audio faster than it could be played. Start a new conversation.", "OPENAI_AUDIO_BACKLOG"))
                    return
                self._played_ms += len(pcm) * 1000 // (PCM24K * 2)
                self._queued_audio_bytes += len(pcm)
                self._playback_queue.put_nowait((self._audio_generation, event.get("item_id") or self._assistant_item_id, pcm))
            await self._state_event("speaking", microphone=False, speaking=True)
        elif event_type in {"response.audio_transcript.delta", "response.output_audio_transcript.delta", "response.output_text.delta"}:
            delta = event.get("delta", "")
            if delta:
                await self._event({"type": "transcript", "role": "assistant", "text": delta, "final": False})
        elif event_type in {"response.audio_transcript.done", "response.output_audio_transcript.done", "response.output_text.done"}:
            transcript = event.get("transcript", event.get("text", ""))
            if transcript:
                await self._event({"type": "transcript", "role": "assistant", "text": transcript, "final": True})
        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = event.get("transcript", "")
            if transcript and event.get("item_id"):
                await self._user_turn(transcript, event["item_id"])
                self._transcribed.setdefault(event["item_id"], asyncio.Event()).set()
        elif event_type == "response.function_call_arguments.done":
            # Input transcription is asynchronous and may follow the tool call.
            # Keep reading the socket while the handoff awaits its exact text.
            task = asyncio.create_task(self._handle_intent_tool(event))
            self._tool_tasks.add(task)
            task.add_done_callback(self._tool_tasks.discard)
        elif event_type in {"response.done", "response.cancelled"}:
            response = event.get("response") or {}
            response_id = response.get("id") or event.get("response_id")
            if response.get("status") in {"failed", "incomplete"}:
                await self._fail((response.get("status_details") or {}).get("error") or {})
                return
            turn_id = self._response_turns.get(response_id)
            waiter = self._typed_waiters.get(turn_id)
            has_call = any(item.get("type") == "function_call" for item in (event.get("response") or {}).get("output", []))
            if waiter and not waiter.done() and not has_call:
                waiter.set_result(None)
            if event_type == "response.cancelled" or (event.get("response") or {}).get("status") == "cancelled":
                self._cancelled_responses.add(response_id)
            if response_id == self._active_response_id or self._active_response_id is None:
                self._response_active = False
                if self._audio_enabled:
                    # response.done means generation ended, not that the last
                    # buffered sample reached the speaker. Keep reading VAD.
                    task = asyncio.create_task(self._finish_playback(self._audio_generation, self._active_response_id))
                    self._drain_tasks.add(task)
                    task.add_done_callback(self._drain_tasks.discard)
                else:
                    await self._state_event("listening", microphone=False)

    async def _handle_intent_tool(self, event: dict[str, Any]) -> None:
        if event.get("name") != "submit_intent":
            return
        try:
            response_id = event.get("response_id")
            turn_id = self._response_turns.get(response_id)
            if not turn_id or response_id in self._cancelled_responses:
                raise ProviderError("This conversation turn has ended. Please repeat the request.")
            await asyncio.wait_for(self._transcribed.setdefault(turn_id, asyncio.Event()).wait(), 15)
            if response_id in self._cancelled_responses:
                raise ProviderError("This conversation turn has ended. Please repeat the request.")
            arguments = json.loads(str(event.get("arguments", "{}")))
            result = await self._submit_intent(validate_intent(arguments), turn_id)
            output = {"accepted": True, "task": result}
        except Exception:
            output = {"accepted": False, "message": "The work request needs clarification."}
        call_id = event.get("call_id")
        if call_id:
            await self._send({"type": "conversation.item.create", "item": {"type": "function_call_output", "call_id": call_id, "output": json.dumps(output)}})
            if self._started and turn_id and response_id not in self._cancelled_responses:
                await self._create_response(turn_id)
