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

    async def test_stop_clears_unconsumed_typed_item_marker(self):
        self.provider._pending_typed_items.add("typed request")
        with patch("maslow_voice.providers.livekit_native.LiveKitNativeExpressiveProvider.stop", new=AsyncMock()):
            await self.provider.stop()

        self.assertEqual(self.provider._pending_typed_items, set())


if __name__ == "__main__":
    unittest.main()
