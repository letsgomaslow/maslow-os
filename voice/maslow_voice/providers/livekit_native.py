"""Native local-audio LiveKit Expressive provider.

The normal LiveKit room provider remains available for the private Mac tester.
This class is selected only by the production provider factory once enabled.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .base import PAUSE_CANCEL_TIMEOUT_SECONDS, ProviderError
from .livekit_expressive import LiveKitExpressiveProvider


class LiveKitNativeExpressiveProvider(LiveKitExpressiveProvider):
    """Run the existing LiveKit inference session over local custom audio I/O."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._native_input: Any = None
        self._native_output: Any = None
        self._native_ready = False

    def _agent_session_options(self) -> dict[str, Any]:
        # Agents 1.8.1 documents this explicit opt-out. PortAudio still runs
        # local APM; physical acoustic-echo validation remains a separate gate.
        # Gateway STT finals can be sentence fragments or empty. Let local VAD
        # end native turns, retaining the SDK's pause and interruption defaults.
        return {"aec_warmup_duration": 0.0, "turn_detection": "vad"}

    def _agent_state(self, event: Any) -> None:
        # AgentSession announces listening before custom device startup is
        # complete. The provider's final startup event is authoritative until
        # input/output readiness and the microphone flag agree.
        if not self._native_ready:
            return
        super()._agent_state(event)

    async def start(self, audio: bool = True) -> None:
        if self._started:
            return
        self._native_ready = False
        self._closing = False
        self._failure = None
        self._muted = False
        self._paused = False
        await self._state_event("connecting", microphone=False)
        try:
            _rtc, _api, agents = self._imports()
            _url, key, secret = self._settings()
            self._session = self._create_agent_session(agents, key, secret)
            self._session.on("agent_state_changed", self._agent_state)
            self._session.on("user_input_transcribed", self._user_transcript)
            self._session.on("conversation_item_added", self._conversation_item)
            self._session.on("error", self._session_error)
            self._session.on("close", self._session_closed)
            self._session.on("metrics_collected", self._metrics_collected)
            if audio:
                if self.audio_transport is None:
                    raise ProviderError("Native LiveKit audio transport is unavailable")
                # This optional-SDK import is intentionally inside audio start.
                from .livekit_native_audio import NativeAgentAudioInput, NativeAgentAudioOutput, NativeAgentAudioSource

                self._native_input = NativeAgentAudioInput()
                self._native_output = NativeAgentAudioOutput(self.audio_transport)
                self._native_output.on("playback_finished", self._playback_finished)
                self._source = NativeAgentAudioSource(self._native_input)
                self._session.input.audio = self._native_input
                self._session.output.audio = self._native_output
            self._started = True
            # Custom endpoints prevent AgentSession from creating RoomIO.
            await self._session.start(agent=self._agent, record=False)
            if self._failure:
                raise self._failure
            if audio and self.audio_transport is not None:
                gate = getattr(self.audio_transport, "set_paused", None)
                if gate is not None:
                    gate(False)
                await self.audio_transport.set_muted(False)
                await self.audio_transport.start(self._on_audio)
            if self._failure:
                raise self._failure
            self._audio_enabled = audio
            self._native_ready = True
            await self._state_event("listening", microphone=audio)
        except asyncio.CancelledError:
            await self.stop()
            raise
        except Exception as error:
            try:
                await self.stop()
            except Exception:
                pass
            if isinstance(error, ProviderError):
                public_error = error
            else:
                public_error = self._public_error(error)
            await self._error(public_error)
            raise public_error from error

    def _fail(self, error: ProviderError) -> None:
        if self._closing or self._failure is not None:
            return
        self._native_ready = False
        if self._native_input is not None:
            self._native_input.close()
        if self._native_output is not None:
            self._native_output.clear_buffer()
        session_input = getattr(getattr(self, "_session", None), "input", None)
        if session_input is not None:
            session_input.set_audio_enabled(False)
        super()._fail(error)

    async def stop(self) -> None:
        self._native_ready = False
        await super().stop()

    async def mute(self, muted: bool) -> None:
        # Typed-only sessions have no capture endpoint. Unmuting is distinct
        # from starting audio, which the daemon owns through start_voice.
        if not muted and self._native_input is None:
            return
        session_input = getattr(getattr(self, "_session", None), "input", None)
        if muted or self._paused:
            if self._native_input is not None:
                self._native_input.discard()
            if session_input is not None:
                session_input.set_audio_enabled(False)
            await super().mute(muted)
            return
        await super().mute(False)
        if session_input is not None:
            session_input.set_audio_enabled(True)

    async def pause(self, paused: bool) -> None:
        if self._paused == paused:
            return
        if paused:
            gate = getattr(self.audio_transport, "set_paused", None)
            if gate is not None:
                gate(True)
            if self._native_input is not None:
                self._native_input.set_paused(True)
            if self._native_output is not None:
                self._native_output.set_paused(True)
            session_input = getattr(self._session, "input", None)
            if session_input is not None:
                session_input.set_audio_enabled(False)
            await super().pause(True)
        else:
            # Typed replies may still be generating while paused. Finish their
            # cancellation with both local endpoints gated, then enable capture.
            await asyncio.wait_for(self.silence(), PAUSE_CANCEL_TIMEOUT_SECONDS)
            if self._native_output is not None:
                self._native_output.set_paused(False)
            if self._native_input is not None:
                self._native_input.set_paused(False)
            await super().pause(False)
            session_input = getattr(self._session, "input", None)
            if session_input is not None and self._native_input is not None:
                session_input.set_audio_enabled(not self._muted)

    async def silence(self) -> None:
        # Flush physical output before asking the SDK to cancel its generation.
        if self._native_output is not None:
            self._native_output.clear_buffer()
            if self._native_output._clear_task is not None:
                await asyncio.shield(self._native_output._clear_task)
        elif self.audio_transport is not None:
            await self.audio_transport.clear_playback()
        await self._event({"type": "interrupted"})
        if self._session is not None:
            session_interrupt = getattr(self._session, "interrupt", None)
            if session_interrupt is not None:
                await session_interrupt(force=True)
            else:
                self._interrupt_current_speech()
        if self._started:
            await self._state_event("listening", microphone=self._audio_enabled and not self._muted)

    def _playback_finished(self, event: Any) -> None:
        if event.interrupted:
            self._queue_event({"type": "interrupted"})

    def _interrupt_current_speech(self) -> None:
        if self._session is not None:
            handle = getattr(self._session, "current_speech", None)
            interrupt = getattr(handle, "interrupt", None)
            if interrupt is not None:
                interrupt()

    async def _disconnect(self) -> None:
        """Close direct endpoints, then always close the inherited owned session."""

        errors: list[BaseException] = []
        if self._native_input is not None:
            try:
                self._native_input.close()
            except Exception as error:
                errors.append(error)
            finally:
                self._native_input = None
        if self._native_output is not None:
            try:
                await self._native_output.aclose()
            except Exception as error:
                errors.append(error)
            finally:
                self._native_output = None
        try:
            await super()._disconnect()
        except Exception as error:
            errors.append(error)
        if errors:
            raise errors[0]
