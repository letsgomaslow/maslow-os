"""Gemini native speech over LiveKit Agents and the owned local audio endpoints.

Google AI Studio is the inference connection. No LiveKit room or inference
credential is consumed by this mode; the saved project also serves Expressive.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .base import ProviderError
from .livekit_native import LiveKitNativeExpressiveProvider


class LiveKitGeminiProvider(LiveKitNativeExpressiveProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._turn_registration = asyncio.Lock()

    async def _register_turn(self, text, identity):
        async with self._turn_registration:
            if identity not in self._known_turns:
                await self._user_turn(text, identity)
                self._known_turns.add(identity)

    def _settings(self) -> tuple[str, str, str]:
        if not self.secrets.get("google"):
            raise ProviderError("Connect your Google AI Studio account in Voice Settings.", "GEMINI_AUTH_REQUIRED")
        return "", "", ""

    def _create_agent_session(self, agents: Any, key: str, secret: str) -> Any:
        try:
            from google.genai import types
            from livekit.plugins import google
        except ImportError as error:
            raise ProviderError("Gemini Voice support is not installed. Repair Voice through Hub.", "LOCAL_DEPENDENCY_MISSING") from error
        provider = self

        class BoundRealtimeModel(google.realtime.RealtimeModel):
            def session(self, **kwargs):
                session = super().session(**kwargs)
                provider._bind_realtime_session(session)
                return session

        # Gemini 3.8 Live explicitly rejects thinking_config. Its default is
        # the low-latency conversation model; do not send the 3.1-only setting.
        model = BoundRealtimeModel(
            api_key=self.secrets["google"], vertexai=False,
            model=self.config.get("gemini_live_model") or "gemini-3.8-live",
            voice=self.config.get("gemini_live_voice") or "Puck",
            modalities=[types.Modality.AUDIO],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )
        self._inference_clients.append(model)
        self._agent = self._create_intent_agent(agents)
        return agents.AgentSession(llm=model, turn_detection="realtime_llm", aec_warmup_duration=0.0)

    def _bind_realtime_session(self, session: Any) -> None:
        """Bind tool calls to their generation's final transcript before dispatch.

        Native realtime bypasses Agent.llm_node. Wrap the SDK's public generation
        stream, keeping a separate binding per response so a later barge-in can
        never replace the source of an earlier task. The Google 1.8.2 plugin
        finalizes input transcription before yielding its tool-call stream.
        """
        active = None

        def generation(event):
            nonlocal active
            binding = {"turn_id": None, "text": "", "final": False}
            if event.user_initiated:
                binding.update(turn_id=getattr(self, "_typed_turn", None), final=True)
            active = binding
            original_stream = event.function_stream

            async def bound_calls():
                async for call in original_stream:
                    if binding["final"] and binding["turn_id"]:
                        identity = binding["turn_id"]
                        await self._register_turn(binding["text"], identity)
                        self._tool_turns[call.call_id] = identity
                        if len(self._tool_turns) > 100:
                            self._tool_turns.pop(next(iter(self._tool_turns)))
                    yield call
            event.function_stream = bound_calls()

        def transcript(event):
            if active is not None and event.is_final:
                active.update(turn_id=event.item_id, text=event.transcript, final=True)

        session.on("generation_created", generation)
        session.on("input_audio_transcription_completed", transcript)

    def _conversation_item(self, event):
        item = event.item
        if item.role == "user" and item.text_content and item.id not in self._known_turns:
            task = asyncio.create_task(self._register_turn(item.text_content, item.id))
            self._event_tasks.add(task)
            task.add_done_callback(self._event_tasks.discard)
        else:
            super()._conversation_item(event)

    async def text(self, text: str, context: str = "") -> None:
        if not self._started or self._session is None:
            raise ProviderError("Start Voice before sending a message")
        value = text.strip()
        if not value:
            return
        _rtc, _api, agents = self._imports()
        message = agents.llm.ChatMessage(role="user", content=[value if not context else f"Context: {context}\n\nUser: {value}"])
        await self._user_turn(value, message.id)
        self._known_turns.add(message.id)
        self._typed_turn = message.id
        try:
            await self._state_event("thinking", microphone=False)
            await self._session.generate_reply(user_input=message)
        finally:
            self._typed_turn = None

    @staticmethod
    def _public_error(error: Any) -> ProviderError:
        cause = getattr(error, "error", error)
        if isinstance(cause, ProviderError):
            return cause
        status = getattr(cause, "status_code", None) or getattr(cause, "code", None)
        if status in {401, 403}:
            return ProviderError("Google denied access. Check the Google AI Studio account in Voice Settings.", "GEMINI_AUTH_FAILED")
        if status in {402, 429}:
            return ProviderError("Gemini usage is unavailable. Check Google billing and quota, then try again.", "GEMINI_USAGE_LIMIT")
        if status in {400, 404}:
            return ProviderError("Gemini could not start the selected model. Check the model in Advanced Settings.", "GEMINI_MODEL_UNAVAILABLE")
        if isinstance(cause, ImportError):
            return ProviderError("Gemini Voice support is not installed. Repair Voice through Hub.", "LOCAL_DEPENDENCY_MISSING")
        if type(cause).__name__ == "PortAudioError":
            return ProviderError("Microphone or speaker access failed. Check the selected audio devices.", "AUDIO_UNAVAILABLE")
        return ProviderError("Gemini Voice disconnected. Check internet access and Google AI Studio availability, then try again.", "GEMINI_CONNECTION_FAILED")
