from __future__ import annotations

import asyncio
import base64
import json
import unittest
from array import array
from typing import Any

from maslow_voice.audio import PCM48K, PcmFrame
from maslow_voice.providers import create_provider
from maslow_voice.providers.base import ProviderError, validate_intent
from maslow_voice.providers.livekit_expressive import LiveKitExpressiveProvider
from maslow_voice.errors import VoiceError


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False

    async def send(self, message: str) -> None:
        event = json.loads(message)
        self.sent.append(event)
        if event.get("type") == "session.update":
            await self.inbox.put(json.dumps({"type": "session.updated"}))

    async def recv(self) -> str:
        return await self.inbox.get()

    async def close(self) -> None:
        self.closed = True


class FakeAudio:
    def __init__(self) -> None:
        self.handler: Any = None
        self.played: list[PcmFrame] = []
        self.cleared = 0
        self.stopped = False
        self.muted = False
        self.played_ms = 10

    async def start(self, handler: Any) -> None:
        self.handler = handler

    async def feed(self, frame: PcmFrame) -> None:
        await self.handler(frame)

    async def play(self, frame: PcmFrame) -> None:
        self.played.append(frame)

    async def clear_playback(self) -> None:
        self.cleared += 1

    async def set_muted(self, muted: bool) -> None:
        self.muted = muted

    async def stop(self) -> None:
        self.stopped = True


VALID_INTENT = {
    "objective": "Prepare a rollout plan",
    "summary": "Plan the rollout",
    "constraints": ["Keep it small"],
    "requested_output": "A short plan",
    "tool_preference": "auto",
    "unresolved_questions": [],
}


class ProviderContractTests(unittest.TestCase):
    def test_factory_is_strict_and_intents_have_no_execution_fields(self) -> None:
        with self.assertRaises(VoiceError):
            create_provider({"mode": "unknown"}, {}, _async_noop, _submit)
        self.assertEqual(validate_intent(VALID_INTENT)["objective"], "Prepare a rollout plan")
        unsafe = {**VALID_INTENT, "command": "rm -rf /"}
        with self.assertRaises(ProviderError):
            validate_intent(unsafe)

    def test_livekit_agent_token_gets_inference_grant_without_exposing_secret(self) -> None:
        class Token:
            def __init__(self, *_args: str) -> None:
                self.calls: list[tuple[str, Any]] = []

            def with_identity(self, value: str) -> "Token":
                self.calls.append(("identity", value))
                return self

            def with_name(self, value: str) -> "Token":
                self.calls.append(("name", value))
                return self

            def with_grants(self, value: Any) -> "Token":
                self.calls.append(("room", value))
                return self

            def with_kind(self, value: str) -> "Token":
                self.calls.append(("kind", value))
                return self

            def with_inference_grants(self, value: Any) -> "Token":
                self.calls.append(("inference", value))
                return self

            def to_jwt(self) -> str:
                return "signed-local-token"

        class Api:
            AccessToken = Token

            class VideoGrants:
                def __init__(self, **kwargs: Any) -> None:
                    self.kwargs = kwargs

            class InferenceGrants:
                def __init__(self, **kwargs: Any) -> None:
                    self.kwargs = kwargs

        provider = LiveKitExpressiveProvider(
            config={"mode": "livekit", "livekit_agent_name": "agent"},
            secrets={},
            emit=_async_noop,
            submit=_submit,
        )
        provider.room_name = "room-1"
        self.assertEqual(provider._token(Api, "project-key", "project-secret", "agent"), "signed-local-token")


class OpenAIRealtimeProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.intents: list[dict[str, Any]] = []
        self.socket = FakeSocket()
        self.audio = FakeAudio()

        async def factory(url: str, headers: dict[str, str]) -> FakeSocket:
            self.url, self.headers = url, headers
            return self.socket

        async def emit(event: dict[str, Any]) -> None:
            self.events.append(event)

        async def submit(intent: dict[str, Any], turn_id: str) -> dict[str, Any]:
            self.intents.append(intent)
            return {"id": "task-1"}

        self.provider = create_provider(
            {"mode": "openai", "socket_factory": factory},
            {"openai": "test-key"},
            emit,
            submit,
            self.audio,
        )
        await self.provider.start(audio=True)

    async def asyncTearDown(self) -> None:
        await self.provider.stop()

    async def test_serializes_24khz_pcm_and_truncates_on_vad_interrupt(self) -> None:
        update = self.socket.sent[0]
        self.assertEqual(update["type"], "session.update")
        self.assertEqual(update["session"]["audio"]["input"]["format"]["rate"], 24_000)
        self.assertEqual(update["session"]["tools"][0]["name"], "submit_intent")

        samples = array("h", range(960))
        await self.audio.feed(PcmFrame(samples.tobytes(), PCM48K))
        append = self.socket.sent[-1]
        self.assertEqual(append["type"], "input_audio_buffer.append")
        self.assertEqual(len(base64.b64decode(append["audio"])), 480 * 2)

        self.audio.played_ms = 0
        await self.socket.inbox.put(json.dumps({"type": "response.output_item.added", "item": {"id": "assistant-1", "role": "assistant"}}))
        await self.socket.inbox.put(json.dumps({"type": "response.output_audio.delta", "delta": base64.b64encode(b"\0\0" * 240).decode()}))
        await asyncio.sleep(0)
        await self.provider.wait_playback()
        self.assertEqual(len(self.audio.played), 1)
        self.audio.played_ms = 10

        await self.socket.inbox.put(json.dumps({"type": "input_audio_buffer.speech_started"}))
        await asyncio.sleep(0)
        sent_types = [event["type"] for event in self.socket.sent]
        self.assertIn("response.cancel", sent_types)
        truncate = next(event for event in self.socket.sent if event["type"] == "conversation.item.truncate")
        self.assertEqual(truncate["item_id"], "assistant-1")
        self.assertEqual(truncate["audio_end_ms"], 10)
        self.assertEqual(self.audio.cleared, 1)

    async def test_submits_only_valid_function_intent(self) -> None:
        await self.provider._handle_event({"type": "input_audio_buffer.committed", "item_id": "audio-1"})
        await self.provider._handle_event({"type": "conversation.item.input_audio_transcription.completed", "item_id": "audio-1", "transcript": "Fix it"})
        await self.provider._handle_event({"type": "response.created", "response": {"id": "response-1", "metadata": {"maslow_turn_id": "audio-1"}}})
        await self.provider._handle_intent_tool({
            "type": "response.function_call_arguments.done",
            "response_id": "response-1",
            "name": "submit_intent",
            "call_id": "call-1",
            "arguments": json.dumps(VALID_INTENT),
        })
        await asyncio.sleep(0)
        self.assertEqual(self.intents, [VALID_INTENT])
        output = next(event for event in self.socket.sent if event["type"] == "conversation.item.create" and event["item"]["type"] == "function_call_output")
        self.assertEqual(json.loads(output["item"]["output"])["accepted"], True)

    async def test_interleaved_audio_responses_retain_original_turn_and_reject_cancelled(self):
        captured = []
        async def submit(intent, turn_id):
            captured.append(turn_id)
            return {"id": "task-1"}
        self.provider._submit_callback = submit
        for index in (1, 2):
            await self.provider._handle_event({"type": "input_audio_buffer.committed", "item_id": f"audio-{index}"})
            await self.provider._handle_event({"type": "response.created", "response": {"id": f"response-{index}", "metadata": {"maslow_turn_id": f"audio-{index}"}}})
            await self.provider._handle_event({"type": "conversation.item.input_audio_transcription.completed", "item_id": f"audio-{index}", "transcript": f"Request {index}"})
        event = {"type": "response.function_call_arguments.done", "name": "submit_intent", "response_id": "response-1",
                 "call_id": "call-1", "arguments": json.dumps(VALID_INTENT)}
        await self.provider._handle_intent_tool(event)
        self.assertEqual(captured, ["audio-1"])
        await self.provider.silence()
        await self.provider._handle_intent_tool(dict(event, response_id="response-2", call_id="call-2"))
        self.assertEqual(captured, ["audio-1"])

    async def test_typed_response_waits_and_uses_echoed_input_identity(self):
        pending = asyncio.create_task(self.provider.text("Fix the tests"))
        await asyncio.sleep(0)
        self.assertFalse(pending.done())
        created = next(event for event in reversed(self.socket.sent) if event["type"] == "response.create")
        metadata = created["response"]["metadata"]
        await self.provider._handle_event({"type": "response.created", "response": {"id": "typed-response", "metadata": metadata}})
        self.assertEqual(self.provider._response_turns["typed-response"], metadata["maslow_turn_id"])
        await self.provider._handle_event({"type": "response.done", "response": {"id": "typed-response", "status": "completed"}})
        await pending

    async def test_tool_waits_for_its_late_audio_transcript_without_blocking_reader(self):
        await self.provider._handle_event({"type": "input_audio_buffer.committed", "item_id": "late-audio"})
        await self.provider._handle_event({"type": "response.created", "response": {"id": "late-response", "metadata": {"maslow_turn_id": "late-audio"}}})
        await self.provider._handle_event({"type": "response.function_call_arguments.done", "name": "submit_intent",
            "response_id": "late-response", "call_id": "late-call", "arguments": json.dumps(VALID_INTENT)})
        await asyncio.sleep(0)
        self.assertEqual(self.intents, [])
        await self.provider._handle_event({"type": "conversation.item.input_audio_transcription.completed",
            "item_id": "late-audio", "transcript": "Fix it"})
        await asyncio.gather(*self.provider._tool_tasks)
        self.assertEqual(self.intents, [VALID_INTENT])

    async def test_start_failure_is_raised_after_a_sanitized_event(self) -> None:
        events: list[dict[str, Any]] = []

        async def emit(event: dict[str, Any]) -> None:
            events.append(event)

        provider = create_provider({"mode": "openai"}, {}, emit, _submit)
        with self.assertRaises(ProviderError):
            await provider.start()
        self.assertEqual(events[0]["type"], "error")
        self.assertEqual(events[1]["state"], "error")


async def _async_noop(_event: dict[str, Any]) -> None:
    return None


async def _submit(_intent: dict[str, Any], turn_id: str) -> dict[str, Any]:
    return {}
