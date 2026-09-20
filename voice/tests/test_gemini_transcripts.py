"""Transcript identity regressions that do not require a live Gemini connection."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from maslow_voice.config import DEFAULTS
from maslow_voice.providers.livekit_gemini import LiveKitGeminiProvider


class GeminiTypedTranscriptTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.events = []
        self.provider = LiveKitGeminiProvider(
            config=dict(DEFAULTS), secrets={},
            emit=AsyncMock(side_effect=self.events.append),
            submit=AsyncMock(),
        )

    async def test_generated_conversation_item_does_not_duplicate_typed_transcript(self):
        typed = "Context: Keep it short.\n\nUser: Create the page"
        self.provider._pending_typed_items.add(typed)

        self.provider._conversation_item(SimpleNamespace(item=SimpleNamespace(
            role="user", id="sdk-generated-id", text_content=typed,
        )))
        await asyncio.sleep(0)

        self.assertEqual(self.events, [])
        self.assertEqual(self.provider._pending_typed_items, set())

    async def test_unrelated_user_conversation_item_is_still_registered(self):
        self.provider._conversation_item(SimpleNamespace(item=SimpleNamespace(
            role="user", id="spoken-turn", text_content="Create the page",
        )))
        await asyncio.gather(*self.provider._event_tasks)

        self.assertEqual(self.events, [{
            "type": "transcript", "role": "user", "text": "Create the page",
            "final": True, "turn_id": "spoken-turn",
        }])

    async def test_typed_item_marker_is_cleared_when_reply_start_fails(self):
        class Message:
            def __init__(self, role, content):
                self.id = "typed-turn"
                self.raw_text_content = content[0]

        agents = SimpleNamespace(llm=SimpleNamespace(ChatMessage=Message))
        self.provider._started = True
        self.provider._imports = lambda: (None, None, agents)
        self.provider._session = SimpleNamespace(generate_reply=AsyncMock(side_effect=RuntimeError("offline")))

        with self.assertRaisesRegex(RuntimeError, "offline"):
            await self.provider.text("Create the page", "Keep it short.")

        self.assertEqual(self.provider._pending_typed_items, set())

    async def test_typed_reply_never_claims_speaker_playback_and_returns_ready(self):
        self.provider._native_ready = True
        self.provider._agent_state(SimpleNamespace(new_state="speaking"))
        self.provider._conversation_item(SimpleNamespace(item=SimpleNamespace(role="assistant", id="reply", text_content="Four.")))
        await asyncio.gather(*self.provider._event_tasks)
        states = [event for event in self.events if event["type"] == "voice_state"]
        self.assertEqual([event["state"] for event in states], ["thinking", "listening"])
        self.assertTrue(all(not event["speaking"] and not event["microphone"] for event in states))

    async def test_typed_notice_uses_finished_handle_instead_of_stale_sdk_state(self):
        self.provider._started = True
        reply = AsyncMock()
        self.provider._session = SimpleNamespace(agent_state="speaking", current_speech=None, generate_reply=reply)
        self.assertTrue(await self.provider.notify_task("Completed"))
        self.provider._typed_turn = "active-input"
        self.assertFalse(await self.provider.notify_task("Completed"))
        self.assertEqual(reply.await_count, 1)
        self.provider._typed_turn = None
        self.provider._session.current_speech = SimpleNamespace(done=lambda: False)
        self.assertFalse(await self.provider.notify_task("Completed"))
        self.provider._session.current_speech = SimpleNamespace(done=lambda: True)
        self.assertTrue(await self.provider.notify_task("Completed"))
        self.assertEqual(reply.await_count, 2)

    async def test_stop_clears_unconsumed_typed_item_marker(self):
        self.provider._pending_typed_items.add("typed request")
        with patch("maslow_voice.providers.livekit_native.LiveKitNativeExpressiveProvider.stop", new=AsyncMock()):
            await self.provider.stop()

        self.assertEqual(self.provider._pending_typed_items, set())


if __name__ == "__main__":
    unittest.main()


class GeminiGenerationIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_late_final_transcript_stays_with_its_original_generation(self):
        provider = LiveKitGeminiProvider(config=dict(DEFAULTS), secrets={}, emit=AsyncMock(), submit=AsyncMock())
        handlers = {}
        session = SimpleNamespace(on=lambda name, callback: handlers.__setitem__(name, callback))
        provider._bind_realtime_session(session)

        async def calls(identity):
            yield SimpleNamespace(call_id=identity)

        events = []
        for response_id, input_id, call_id in (("A", "input-A", "call-A"), ("B", "input-B", "call-B")):
            session._current_generation = SimpleNamespace(response_id=response_id, input_id=input_id)
            event = SimpleNamespace(response_id=response_id, user_initiated=False, function_stream=calls(call_id))
            handlers["generation_created"](event)
            events.append(event)
        handlers["input_audio_transcription_completed"](SimpleNamespace(item_id="input-A", transcript="Open browser", is_final=True))
        for event in events:
            async for _call in event.function_stream:
                pass
        self.assertEqual(provider._tool_turns, {"call-A": "input-A"})
        self.assertNotIn("call-B", provider._tool_turns)
