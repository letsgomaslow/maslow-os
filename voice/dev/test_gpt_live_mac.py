"""Private GPT-Live harness boundaries; no cloud or physical audio."""

import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from aiohttp.test_utils import TestClient, TestServer
from gpt_live_mac import LiveSession
from livekit_mac import create_app, ORIGIN, TOKEN


class LiveTesterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.session = LiveSession(scratch=self.temp.name)
        self.app = create_app(self.session, page_path=Path(__file__).with_name("gpt_live_mac.html"))
        self.client = TestClient(TestServer(self.app, host="127.0.0.1"))
        await self.client.start_server()
        self.origin = str(self.client.make_url("/")).rstrip("/")
        self.app[ORIGIN] = self.origin
        self.headers = {"Origin": self.origin, "X-Maslow-Test": self.app[TOKEN]}

    async def asyncTearDown(self):
        await self.client.close()
        self.temp.cleanup()

    async def test_private_boundary_includes_task_data(self):
        self.session.save({"key": "synthetic-private-key"})
        self.session.transcripts = [{"role": "user", "text": "private spoken words"}]
        status = await self.client.get("/status")
        public = await status.text()
        self.assertNotIn("private spoken words", public)
        self.assertNotIn("synthetic-private-key", public)
        self.assertEqual((await self.client.get("/view")).status, 403)
        response = await self.client.get("/view", headers=self.headers)
        self.assertIn("private spoken words", await response.text())
        for path in ("task", "task-action", "mute"):
            self.assertEqual((await self.client.post("/action/" + path, json={})).status, 403)

    async def test_active_provider_metrics_are_visible_before_audio_ends(self):
        self.session.provider = SimpleNamespace(metrics_snapshot=lambda: {"session_started": True})
        self.assertTrue(self.session.status()["metrics"]["session_started"])
        self.session.provider = None

    async def test_overlap_has_no_invented_final_turn_or_action(self):
        for role, delta in (("user", "Create "), ("assistant", "What kind?"), ("user", "a page")):
            await self.session.emit({"type": "transcript_delta", "role": role, "delta": delta, "start_ms": 100})
        self.assertEqual([item["text"] for item in self.session.transcripts], ["Create ", "What kind?", "a page"])
        self.assertFalse(self.session.notices)
        self.assertFalse(self.session.background)

    async def test_end_voice_does_not_cancel_accepted_background_work(self):
        gate = asyncio.Event()
        task = self.session.spawn(gate.wait())
        runtime = SimpleNamespace(close=AsyncMock())
        self.session.runtime = runtime
        await self.session.end()
        self.assertFalse(task.done())
        runtime.close.assert_not_awaited()
        gate.set()
        await task

    async def test_old_result_is_not_injected_into_new_conversation(self):
        old, new = SimpleNamespace(append_context=AsyncMock()), SimpleNamespace(append_context=AsyncMock())
        self.session.provider = new
        await self.session.context("commentary", "Old result", provider=old)
        await self.session.context("commentary", "Task started without voice", provider=None)
        new.append_context.assert_not_awaited()
        old.append_context.assert_not_awaited()
        await self.session.context("thinking", "Current result")
        new.append_context.assert_awaited_once()

    async def test_microphone_and_speech_are_independent(self):
        self.session.mode = "conversation"
        await self.session.emit({"type": "voice_state", "state": "speaking", "microphone": True, "speaking": True})
        self.assertTrue(self.session.microphone)
        self.assertTrue(self.session.speaking)
        await self.session.emit({"type": "voice_state", "state": "speaking", "microphone": False, "speaking": True})
        self.assertFalse(self.session.microphone)
        self.assertTrue(self.session.speaking)

    async def test_replayed_delegation_does_not_start_another_host_path(self):
        self.session.mode = "conversation"
        self.session.delegate = AsyncMock()
        event = {"type": "delegation", "delegation_id": "synthetic-delegation"}
        await self.session.emit(event)
        await asyncio.sleep(0)
        self.session.notices.clear()
        await self.session.emit(event)
        await asyncio.sleep(0)
        self.session.delegate.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
