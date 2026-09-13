"""LiveKit Expressive provider with a local named Agent worker.

Two local room participants are used deliberately: the desktop participant owns
the microphone/speakers, while the named agent participant runs the inference
pipeline. The project key and secret sign short-lived room tokens locally and
are never sent to the desktop UI or included in emitted events.
"""

from __future__ import annotations

import asyncio
import secrets as secure_secrets
from typing import Any

from maslow_voice.audio import PcmFrame, resample_pcm16

from .base import ProviderError, VoiceProvider


class LiveKitExpressiveProvider(VoiceProvider):
    """Run Deepgram/Gemma/Inworld inference in a locally named LiveKit agent."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client_room: Any = None
        self._worker_room: Any = None
        self._source: Any = None
        self._session: Any = None
        self._agent: Any = None
        self._http_session: Any = None
        self._inference_clients: list[Any] = []
        self._audio_tasks: set[asyncio.Task[None]] = set()
        self._event_tasks: set[asyncio.Task[None]] = set()
        self.room_name: str | None = None
        self.agent_name = str(self.config.get("livekit_agent_name", "maslow-voice-agent"))
        self._tool_turns = {}
        self._known_turns = set()

    async def start(self, audio: bool = True) -> None:
        if self._started:
            return
        await self._state_event("connecting", microphone=False)
        try:
            rtc, api, agents = self._imports()
            url, key, secret = self._settings()
            self.room_name = str(self.config.get("livekit_room", f"maslow-voice-{secure_secrets.token_urlsafe(12)}"))
            client_identity = f"maslow-voice-client-{secure_secrets.token_urlsafe(8)}"
            client_token = self._token(api, key, secret, client_identity)
            worker_token = self._token(api, key, secret, self.agent_name)
            self._client_room = rtc.Room()
            self._worker_room = rtc.Room()
            self._client_room.on("track_subscribed", self._on_track_subscribed)
            await self._client_room.connect(url, client_token)
            await self._worker_room.connect(url, worker_token)
            self._source = rtc.AudioSource(48_000, 1)
            track = rtc.LocalAudioTrack.create_audio_track("maslow-voice-microphone", self._source)
            await self._client_room.local_participant.publish_track(
                track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
            self._session = self._create_agent_session(agents, key, secret)
            self._session.on("agent_state_changed", self._agent_state)
            self._session.on("user_input_transcribed", self._user_transcript)
            self._session.on("conversation_item_added", self._conversation_item)
            self._started = True
            await self._session.start(agent=self._agent, room=self._worker_room, record=False,
                                      room_options=agents.room_io.RoomOptions(participant_identity=client_identity,
                                                                             audio_input=audio, audio_output=audio, video_input=False))
            self._started = True
            self._audio_enabled = audio
            if audio and self.audio_transport is not None:
                await self.audio_transport.start(self._on_audio)
            await self._state_event("listening", microphone=audio)
        except asyncio.CancelledError:
            await self.stop()
            raise
        except Exception as error:
            try:
                await self.stop()
            except Exception:
                # Cleanup attempts every owned resource. Preserve the original
                # connection error if one of those resources also fails to close.
                pass
            await self._raise_start_error(error, "LiveKit Voice could not connect")

    def _imports(self) -> tuple[Any, Any, Any]:
        try:
            from livekit import api, rtc
            from livekit import agents
        except ImportError as error:
            raise ProviderError("LiveKit Voice support is not installed") from error
        return rtc, api, agents

    def _settings(self) -> tuple[str, str, str]:
        url = str(self.config.get("livekit_url", "")).strip()
        key = self.secrets.get("livekit_key", "")
        secret = self.secrets.get("livekit_secret", "")
        if not url or not key or not secret:
            raise ProviderError("LiveKit project credentials are unavailable")
        return url, key, secret

    def _token(self, api: Any, key: str, secret: str, identity: str) -> str:
        token = api.AccessToken(key, secret).with_identity(identity).with_name(identity)
        is_agent = identity == self.agent_name
        token.with_grants(api.VideoGrants(room_join=True, room=self.room_name, agent=is_agent))
        # The local agent, not the desktop client, is permitted to invoke the
        # user's selected LiveKit inference models.
        if is_agent:
            token.with_kind("agent")
            token.with_inference_grants(api.InferenceGrants(perform=True))
        return token.to_jwt()

    def _create_agent_session(self, agents: Any, key: str, secret: str) -> Any:
        try:
            inference = agents.inference
        except AttributeError as error:
            raise ProviderError("Installed LiveKit Agents version lacks inference support") from error
        provider = self
        function_tool = agents.function_tool

        class IntentAgent(agents.Agent):
            def __init__(self) -> None:
                super().__init__(instructions=(
                    "You are Maslow's concise English voice coordinator. "
                    "You may only prepare a work intent with submit_intent. "
                    "Never execute tools, commands, or permissions."
                ))

            async def llm_node(self, chat_ctx, tools, model_settings):
                # Bind calls while their generation context is immutable. Looking
                # at session.chat_ctx later can select a newer barge-in instead.
                message = next((item for item in reversed(chat_ctx.items)
                                if getattr(item, "role", None) == "user"), None)
                turn_id = message.id if message else None
                if message and turn_id not in provider._known_turns:
                    await provider._user_turn(message.text_content or "", turn_id)
                    provider._known_turns.add(turn_id)
                async for chunk in agents.Agent.default.llm_node(self, chat_ctx, tools, model_settings):
                    for call in getattr(getattr(chunk, "delta", None), "tool_calls", []):
                        provider._tool_turns[call.call_id] = turn_id
                        if len(provider._tool_turns) > 100:
                            provider._tool_turns.pop(next(iter(provider._tool_turns)))
                    yield chunk

            async def submit_intent(
                self,
                context,
                objective: str,
                summary: str,
                constraints: list[str],
                requested_output: str,
                tool_preference: str,
                unresolved_questions: list[str],
            ) -> str:
                try:
                    turn_id = provider._tool_turns.pop(context.function_call.call_id, None)
                    if not turn_id or context.speech_handle.interrupted:
                        raise ProviderError("This conversation turn has ended. Please repeat the request.")
                    await provider._submit_intent({
                        "objective": objective,
                        "summary": summary,
                        "constraints": constraints,
                        "requested_output": requested_output,
                        "tool_preference": tool_preference,
                        "unresolved_questions": unresolved_questions,
                    }, turn_id)
                    return "The work request was submitted for the host to review."
                except Exception:
                    return "The work request needs clarification."

        # The SDK injects RunContext; it is deliberately absent from the model's
        # tool arguments. Bind the actual optional SDK type before decoration.
        IntentAgent.submit_intent.__annotations__["context"] = agents.RunContext
        IntentAgent.submit_intent = function_tool(IntentAgent.submit_intent)
        import aiohttp
        from livekit.plugins import silero
        # This agent runs inside the desktop daemon, outside LiveKit's job
        # worker. Its lazy STT/TTS streams therefore need an explicitly owned
        # HTTP session instead of relying on the worker's context variable.
        self._http_session = aiohttp.ClientSession()
        stt = inference.STT(model="deepgram/nova-3", language="en", api_key=key, api_secret=secret,
                            http_session=self._http_session)
        self._inference_clients.append(stt)
        llm = inference.LLM(model="google/gemma-4-31b-it", api_key=key, api_secret=secret)
        self._inference_clients.append(llm)
        tts = inference.TTS(model="inworld/inworld-tts-2", voice="Ashley", api_key=key, api_secret=secret,
                            http_session=self._http_session)
        self._inference_clients.append(tts)
        session = agents.AgentSession(
            stt=stt,
            llm=llm,
            tts=tts,
            expressive=True,
            vad=silero.VAD.load(),
            turn_detection="stt",
        )
        self._agent = IntentAgent()
        return session

    def _queue_event(self, event):
        task = asyncio.create_task(self._event(event))
        self._event_tasks.add(task)
        task.add_done_callback(self._event_tasks.discard)

    def _agent_state(self, event):
        state = str(event.new_state)
        if state in {"listening", "thinking", "speaking"}:
            self._queue_event({"type": "voice_state", "state": state, "microphone": self._audio_enabled and not self._muted,
                               "speaking": state == "speaking"})

    def _user_transcript(self, event):
        # llm_node receives the final transcript with its SDK ChatMessage.id.
        # This STT notification has no authoritative generation identity.
        pass

    def _conversation_item(self, event):
        if event.item.role == "assistant" and event.item.text_content:
            self._queue_event({"type": "transcript", "role": "assistant", "text": event.item.text_content, "final": True})

    async def _on_audio(self, frame: PcmFrame) -> None:
        if not self._started or self._muted or self._source is None:
            return
        await self._level(frame)
        rtc, _api, _agents = self._imports()
        frame = resample_pcm16(frame, 48_000)
        rtc_frame = rtc.AudioFrame(
            data=frame.pcm,
            sample_rate=frame.sample_rate,
            num_channels=1,
            samples_per_channel=len(frame.pcm) // 2,
        )
        await self._source.capture_frame(rtc_frame)

    def _on_track_subscribed(self, track: Any, _publication: Any, participant: Any) -> None:
        # The named worker's remote output is the only audio rendered locally.
        rtc, _api, _agents = self._imports()
        if getattr(participant, "identity", "") != self.agent_name or getattr(track, "kind", None) != rtc.TrackKind.KIND_AUDIO:
            return
        task = asyncio.create_task(self._play_remote_track(track))
        self._audio_tasks.add(task)
        task.add_done_callback(self._audio_tasks.discard)

    async def _play_remote_track(self, track: Any) -> None:
        try:
            rtc, _api, _agents = self._imports()
            stream = rtc.AudioStream(track)
            async for event in stream:
                if not self._started or self.audio_transport is None:
                    break
                frame = event.frame
                pcm = bytes(frame.data)
                await self.audio_transport.play(PcmFrame(pcm, frame.sample_rate, frame.num_channels))
                await self._state_event("speaking", microphone=False, speaking=True)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if self._started:
                await self._error(error, "LiveKit audio stream failed")

    async def text(self, text: str, context: str = "") -> None:
        if not self._started or self._session is None:
            await self._error(ProviderError("Start Voice before sending a message"))
            return
        value = text.strip()
        if not value:
            return
        _rtc, _api, agents = self._imports()
        message = agents.llm.ChatMessage(role="user", content=[value if not context else f"Context: {context}\n\nUser: {value}"])
        await self._user_turn(value, message.id)
        self._known_turns.add(message.id)
        await self._state_event("thinking", microphone=False)
        # AgentSession owns its chat context; adding a reply instruction is the
        # supported typed-turn bridge without synthesising microphone audio.
        await self._session.generate_reply(user_input=message)

    async def silence(self) -> None:
        if self._session is not None:
            handle = getattr(self._session, "current_speech", None)
            if handle is not None:
                interrupt = getattr(handle, "interrupt", None)
                if interrupt is not None:
                    interrupt()
        await super().silence()
        if self._started:
            await self._state_event("listening", microphone=self._audio_enabled and not self._muted)

    async def stop(self) -> None:
        self._started = False
        self._tool_turns.clear()
        self._known_turns.clear()
        self._audio_enabled = False
        errors = []
        if self.audio_transport is not None:
            try:
                await self.audio_transport.stop()
            except Exception as error:
                errors.append(error)
        for task in tuple(self._audio_tasks):
            task.cancel()
        if self._audio_tasks:
            await asyncio.gather(*self._audio_tasks, return_exceptions=True)
        for task in tuple(self._event_tasks):
            task.cancel()
        await asyncio.gather(*self._event_tasks, return_exceptions=True)
        try:
            await self._disconnect()
        except Exception as error:
            errors.append(error)
        await self._state_event("disabled", microphone=False)
        if errors:
            raise errors[0]

    async def _disconnect(self) -> None:
        errors = []
        if self._session is not None:
            close = getattr(self._session, "aclose", None)
            try:
                if close is not None:
                    await close()
            except Exception as error:
                errors.append(error)
            finally:
                self._session = None
        # AgentSession closes its streams, but the inference clients belong to
        # us. LLM owns a separate httpx client; STT/TTS share our aiohttp session.
        for client in self._inference_clients:
            try:
                await client.aclose()
            except Exception as error:
                errors.append(error)
        self._inference_clients.clear()
        if self._http_session is not None:
            try:
                await self._http_session.close()
            except Exception as error:
                errors.append(error)
            finally:
                self._http_session = None
        for room_name in ("_client_room", "_worker_room"):
            room = getattr(self, room_name)
            if room is not None:
                disconnect = getattr(room, "disconnect", None)
                try:
                    if disconnect is not None:
                        await disconnect()
                except Exception as error:
                    errors.append(error)
                finally:
                    setattr(self, room_name, None)
        if self._source is not None:
            try:
                await self._source.aclose()
            except Exception as error:
                errors.append(error)
        self._source = None
        self._agent = None
        if errors:
            raise errors[0]
