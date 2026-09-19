"""OpenAI tester boundaries without cloud calls or physical audio."""

import asyncio
import unittest
from unittest.mock import AsyncMock

from aiohttp.test_utils import TestClient, TestServer

from livekit_mac import create_app, ORIGIN, TOKEN, Session, SAMPLE_TEXT
from maslow_voice.providers.base import ProviderError
from test_livekit_mac import FakeProvider


class OpenAITesterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeProvider.instances = []
        self.session = Session(FakeProvider, kind="openai")
        self.app = create_app(self.session)
        self.client = TestClient(TestServer(self.app, host="127.0.0.1"))
        await self.client.start_server()
        self.origin = str(self.client.make_url("/")).rstrip("/")
        self.app[ORIGIN] = self.origin
        self.headers = {"Origin": self.origin, "X-Maslow-Test": self.app[TOKEN]}

    async def asyncTearDown(self):
        await self.client.close()

    async def test_key_is_write_only_and_does_not_start_audio(self):
        key = "synthetic-openai-test-key"
        response = await self.client.post("/action/save", json={"key": key}, headers=self.headers)
        self.assertEqual(response.status, 200)
        for path in ("/", "/status", "/view"):
            response = await self.client.get(path, headers=self.headers)
            self.assertNotIn(key, await response.text())
        self.assertFalse(FakeProvider.instances)
        self.assertFalse(self.session.microphone)
        for fields in ({"key": ""}, {"key": "new", "secret": "unexpected"}, {"key": "bad\r\nvalue"}):
            response = await self.client.post("/action/save", json=fields, headers=self.headers)
            self.assertEqual(response.status, 400)
            self.assertEqual(self.session.credentials, {"openai": key})

    async def test_same_private_boundary_guards_openai(self):
        for headers in ({}, {"Origin": "https://elsewhere.test", "X-Maslow-Test": self.app[TOKEN]},
                        {**self.headers, "Host": "elsewhere.test"}):
            response = await self.client.post("/action/save", json={"key": "synthetic"}, headers=headers)
            self.assertEqual(response.status, 403)
        self.assertFalse(self.session.credentials)

    async def test_openai_voice_passes_to_real_provider_contract(self):
        self.session.save({"key": "synthetic"})
        self.session.start("conversation", "marin")
        await asyncio.sleep(.02)
        provider = FakeProvider.instances[0]
        self.assertEqual(provider.config["mode"], "openai")
        self.assertEqual(provider.config["realtime_voice"], "marin")
        self.assertTrue(self.session.microphone)
        await self.session.end()
        self.assertTrue(provider.stopped)
        self.assertFalse(provider.secrets)
        self.assertFalse(self.session.microphone)

    async def test_provider_catalogs_cannot_be_mixed(self):
        self.session.save({"key": "synthetic"})
        for voice in ("Ashley", "nova", "custom", []):
            with self.assertRaises(ProviderError):
                self.session.start("audition", voice)
        self.assertEqual(self.session.selected_voice, "cedar")
        self.assertEqual(len(self.session.status()["voices"]), 10)
        self.assertFalse(FakeProvider.instances)

    async def test_openai_preview_uses_realtime_and_never_captures_microphone(self):
        class PreviewProvider(FakeProvider):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.text = AsyncMock()
                self.wait_playback = AsyncMock()
        self.session.provider_factory = PreviewProvider
        self.session.save({"key": "synthetic"})
        self.session.start("audition", "marin")
        await asyncio.wait_for(self.session.job, 1)
        provider = FakeProvider.instances[0]
        self.assertFalse(provider.transport._capture)
        self.assertEqual(provider.config["realtime_voice"], "marin")
        provider.text.assert_awaited_once()
        self.assertIn(SAMPLE_TEXT, provider.text.call_args.args[0])
        provider.wait_playback.assert_awaited_once()
        self.assertEqual(self.session.error["code"], "VOICE_SAMPLE_EMPTY")
        self.assertFalse(self.session.microphone)

    async def test_streaming_transcript_is_one_turn_and_clears(self):
        async def emit(text, final):
            await self.session.emit({"type": "transcript", "role": "assistant", "text": text, "final": final})
        await emit("Hello ", False)
        await emit("there", False)
        self.assertEqual(self.session.transcripts, [{"role": "assistant", "text": "Hello there"}])
        self.assertEqual(self.session.turns["assistant"], 0)
        await emit("Hello there.", True)
        self.assertEqual(self.session.transcripts, [{"role": "assistant", "text": "Hello there."}])
        self.assertEqual(self.session.turns["assistant"], 1)
        await emit("Next ", False)
        self.assertEqual(len(self.session.transcripts), 2)
        await self.session.end()
        self.assertFalse(self.session.transcripts)
        self.assertFalse(self.session._partial)


if __name__ == "__main__":
    unittest.main()
