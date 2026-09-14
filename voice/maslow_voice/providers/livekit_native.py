"""Native local-audio LiveKit Expressive provider.

The normal LiveKit room provider remains available for the private Mac tester.
This class is selected only by the production provider factory once enabled.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .base import ProviderError
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
        return {"aec_warmup_duration": 0.0}

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
            if audio:
                if self.audio_transport is None:
                    raise ProviderError("Native LiveKit audio transport is unavailable")
                # This optional-SDK import is intentionally inside audio start.
                from .livekit_native_audio import NativeAgentAudioInput, NativeAgentAudioOutput, NativeAgentAudioSource

                self._native_input = NativeAgentAudioInput()
                self._native_output = NativeAgentAudioOutput(self.audio_transport)
                self._source = NativeAgentAudioSource(self._native_input)
                self._session.input.audio = self._native_input
                self._session.output.audio = self._native_output
            self._started = True
            # Custom endpoints prevent AgentSession from creating RoomIO.
            await self._session.start(agent=self._agent, record=False)
            if self._failure:
                raise self._failure
            if audio and self.audio_transport is not None:
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
        session_input = getattr(getattr(self, "_session", None), "input", None)
        if muted:
            if self._native_input is not None:
                self._native_input.discard()
            if session_input is not None:
                session_input.set_audio_enabled(False)
            await super().mute(True)
            return
        await super().mute(False)
        if session_input is not None:
            session_input.set_audio_enabled(True)

    async def silence(self) -> None:
        if self._session is not None:
            handle = getattr(self._session, "current_speech", None)
            interrupt = getattr(handle, "interrupt", None)
            if interrupt is not None:
                interrupt()
        if self._native_output is not None:
            self._native_output.clear_buffer()
        elif self.audio_transport is not None:
            await self.audio_transport.clear_playback()
        if self._started:
            await self._state_event("listening", microphone=self._audio_enabled and not self._muted)

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
