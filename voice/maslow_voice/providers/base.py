"""Shared contracts and safety checks for Voice providers."""

from __future__ import annotations

import asyncio
import math
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, Final, Literal, TypedDict

from maslow_voice.audio import PcmFrame
from maslow_voice.errors import VoiceError

VoiceState = Literal["connecting", "listening", "thinking", "speaking", "disabled", "error"]
ToolPreference = Literal["auto", "codex", "claude", "hermes"]
Emit = Callable[[dict[str, Any]], Awaitable[None]]
Submit = Callable[[dict[str, Any], str], Awaitable[dict[str, Any]]]


class Intent(TypedDict):
    objective: str
    summary: str
    constraints: list[str]
    requested_output: str
    tool_preference: ToolPreference
    unresolved_questions: list[str]


INTENT_KEYS: Final = frozenset(Intent.__annotations__)
TOOL_PREFERENCES: Final = frozenset({"auto", "codex", "claude", "hermes"})


class ProviderError(VoiceError):
    """An error that is safe to communicate to the person using Voice."""

    def __init__(self, message: str, code: str = "VOICE_PROVIDER_ERROR") -> None:
        super().__init__(code, message)


def sanitize_error(error: BaseException | str, default: str = "Voice connection failed") -> str:
    """Return a useful public message without endpoints, tokens, or tracebacks."""

    value = str(error).replace("\n", " ").strip()
    lower = value.lower()
    if any(word in lower for word in ("token", "api key", "authorization", "secret", "credential")):
        return "Voice credentials were rejected or are unavailable"
    if any(word in lower for word in ("timed out", "timeout", "network", "connect", "dns")):
        return "Voice service could not be reached"
    if isinstance(error, ProviderError) and value:
        return value[:180]
    return default


def validate_intent(value: object) -> Intent:
    """Validate the deliberately small, non-executable intent boundary."""

    if not isinstance(value, dict) or set(value) != INTENT_KEYS:
        raise ProviderError("Voice could not form a safe work request")
    if not all(isinstance(value[key], str) for key in ("objective", "summary", "requested_output")):
        raise ProviderError("Voice could not form a safe work request")
    if not value["objective"].strip() or not value["summary"].strip():
        raise ProviderError("Voice could not form a safe work request")
    if value["tool_preference"] not in TOOL_PREFERENCES:
        raise ProviderError("Voice could not form a safe work request")
    for key in ("constraints", "unresolved_questions"):
        if not isinstance(value[key], list) or not all(isinstance(item, str) for item in value[key]):
            raise ProviderError("Voice could not form a safe work request")
    # The host attaches project/session/transcript metadata after this boundary.
    return {
        "objective": value["objective"].strip(),
        "summary": value["summary"].strip(),
        "constraints": [item.strip() for item in value["constraints"] if item.strip()],
        "requested_output": value["requested_output"].strip(),
        "tool_preference": value["tool_preference"],
        "unresolved_questions": [item.strip() for item in value["unresolved_questions"] if item.strip()],
    }


class VoiceProvider(ABC):
    """The daemon-facing provider contract.

    Providers only generate transcripts and constrained intents. They neither
    invoke tools nor retain raw PCM outside live bounded queues.
    """

    def __init__(
        self,
        *,
        config: dict[str, Any],
        secrets: dict[str, str],
        emit: Emit,
        submit: Submit,
        audio_transport: Any = None,
    ) -> None:
        self.config = config
        self.secrets = secrets
        self._emit_callback = emit
        self._submit_callback = submit
        self.audio_transport = audio_transport
        self._started = False
        self._audio_enabled = False
        self._muted = False
        self._state: VoiceState = "disabled"
        # Provider objects may be constructed while configuration is loaded,
        # before the daemon has entered its event loop (notably on Python 3.9).
        self._emit_lock: asyncio.Lock | None = None

    @abstractmethod
    async def start(self, audio: bool = True) -> None:
        """Begin an explicitly requested session."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop microphone, playback, and provider connection."""

    @abstractmethod
    async def text(self, text: str, context: str = "") -> None:
        """Send a typed turn without requiring microphone capture."""

    async def mute(self, muted: bool) -> None:
        self._muted = muted
        if self.audio_transport is not None:
            await self.audio_transport.set_muted(muted)
        if self._started:
            await self._state_event("listening", microphone=self._audio_enabled and not muted)

    async def silence(self) -> None:
        """Interrupt local playback. Cloud providers extend this to cancel output."""

        if self.audio_transport is not None:
            await self.audio_transport.clear_playback()
        if self._started:
            await self._state_event("listening", microphone=self._audio_enabled and not self._muted)

    async def _event(self, event: dict[str, Any]) -> None:
        # Serialising events retains a truthful state sequence on fast VAD turns.
        if self._emit_lock is None:
            self._emit_lock = asyncio.Lock()
        async with self._emit_lock:
            await self._emit_callback(event)

    async def _state_event(self, state: VoiceState, *, microphone: bool, speaking: bool = False) -> None:
        self._state = state
        if state not in {"connecting", "disabled", "error"}:
            microphone = self._audio_enabled and not self._muted
        await self._event({"type": "voice_state", "state": state, "microphone": microphone, "speaking": speaking})

    async def _error(self, error: BaseException | str, default: str = "Voice connection failed") -> None:
        message = sanitize_error(error, default)
        code = error.code if isinstance(error, ProviderError) else "VOICE_PROVIDER_ERROR"
        await self._event({"type": "error", "code": code, "message": message})
        await self._state_event("error", microphone=False, speaking=False)

    async def _raise_start_error(self, error: BaseException | str, default: str) -> None:
        """Emit the safe failure and keep the daemon's readiness state truthful."""

        message = sanitize_error(error, default)
        await self._error(ProviderError(message), default)
        if isinstance(error, BaseException):
            raise ProviderError(message) from error
        raise ProviderError(message)

    async def _user_turn(self, text: str, turn_id: str | None = None) -> str:
        identity = turn_id or str(uuid.uuid4())
        await self._event({"type": "transcript", "role": "user", "text": text, "final": True, "turn_id": identity})
        return identity

    async def _submit_intent(self, value: object, turn_id: str) -> dict[str, Any]:
        if not self._started or not turn_id:
            raise ProviderError("This conversation turn has ended. Please repeat the request.")
        intent = validate_intent(value)
        return await self._submit_callback(intent, turn_id)

    async def _on_audio(self, frame: PcmFrame) -> None:
        """Override in providers that accept native PCM input."""

    async def _level(self, frame: PcmFrame) -> None:
        if not frame.pcm:
            return
        samples = memoryview(frame.pcm).cast("h")
        if not samples:
            return
        mean_square = sum(sample * sample for sample in samples) / len(samples)
        level = min(1.0, math.sqrt(mean_square) / 32768.0)
        # Meter readings are independent of ordered transcript/state delivery.
        # A slow UI consumer of those events must not hold microphone ingestion.
        await self._emit_callback({"type": "level", "level": round(level, 4)})
