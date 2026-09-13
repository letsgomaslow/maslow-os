"""Private tester boundary tests; no network providers or audio devices."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from aiohttp.test_utils import TestClient, TestServer

from livekit_mac import create_app, ORIGIN, TOKEN, SESSION, Session


class FakeProvider:
    instances = []

    def __init__(self, **kwargs):
        self.secrets = kwargs["secrets"]
        self.config = kwargs["config"]
        self.transport = kwargs["audio_transport"]
        self._session = SimpleNamespace(say=AsyncMock())
        self.emit = kwargs["emit"]
        self.started = False
        self.stopped = False
        self.instances.append(self)

    async def start(self, audio=True):
        self.started = audio
        await self.emit({"type": "voice_state", "state": "listening", "microphone": audio})

    async def stop(self):
        self.stopped = True
        await self.emit({"type": "voice_state", "state": "disabled", "microphone": False})


class TesterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeProvider.instances = []
        self.app = create_app(Session(FakeProvider))
        self.client = TestClient(TestServer(self.app, host="127.0.0.1"))
        await self.client.start_server()
        self.origin = str(self.client.make_url("/")).rstrip("/")
        self.app[ORIGIN] = self.origin
        self.headers = {"Origin": self.origin, "X-Maslow-Test": self.app[TOKEN]}
        self.fields = {"url": "wss://example.livekit.cloud", "key": "sentinel-project-key", "secret": "sentinel-private-secret"}

    async def asyncTearDown(self):
        await self.client.close()

    async def post(self, name, fields=None):
        return await self.client.post("/action/" + name, json={} if fields is None else fields, headers=self.headers)

    async def test_save_never_starts_audio_or_echoes_credentials(self):
        response = await self.post("save", self.fields)
        self.assertEqual(response.status, 200)
        for path in ("/", "/status", "/view"):
            response = await self.client.get(path, headers=self.headers)
            text = await response.text()
            for value in self.fields.values():
                self.assertNotIn(value, text)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(FakeProvider.instances, [])
        self.assertFalse(self.app[SESSION].microphone)

    async def test_cross_origin_forgery_and_rebinding_rejected(self):
        for headers in ({}, {"Origin": "https://other.test", "X-Maslow-Test": self.app[TOKEN]},
                        {"Origin": self.origin, "X-Maslow-Test": "wrong"},
                        {**self.headers, "Host": "other.test"}):
            response = await self.client.post("/action/save", json=self.fields, headers=headers)
            self.assertEqual(response.status, 403)
        self.assertFalse(self.app[SESSION].credentials)
        response = await self.client.get("/view")
        self.assertEqual(response.status, 403)

    async def test_invalid_save_preserves_previous_connection(self):
        await self.post("save", self.fields)
        response = await self.post("save", {**self.fields, "url": "https://key:secret@example.test"})
        self.assertEqual(response.status, 400)
        self.assertEqual(self.app[SESSION].url, self.fields["url"])
        response = await self.post("save", {**self.fields, "secret": ""})
        self.assertEqual(response.status, 400)
        self.assertEqual(self.app[SESSION].credentials["livekit_secret"], self.fields["secret"])

    async def test_explicit_start_and_end_close_capture_and_clear_transcript(self):
        await self.post("save", self.fields)
        self.assertEqual((await self.post("conversation")).status, 200)
        await asyncio.sleep(.02)
        provider = FakeProvider.instances[0]
        self.assertTrue(provider.started)
        self.assertTrue(self.app[SESSION].microphone)
        await self.app[SESSION].emit({"type": "transcript", "role": "user", "text": "private sentence"})
        self.assertNotIn("private sentence", await (await self.client.get("/status")).text())
        self.assertEqual((await self.post("save", self.fields)).status, 400)
        await self.post("end")
        self.assertTrue(provider.stopped)
        self.assertFalse(provider.secrets)
        self.assertFalse(self.app[SESSION].microphone)
        self.assertFalse(self.app[SESSION].transcripts)
        await self.post("forget")
        self.assertFalse(self.app[SESSION].credentials)

    async def test_provider_error_stops_conversation_without_click(self):
        await self.post("save", self.fields)
        await self.post("conversation")
        await asyncio.sleep(.02)
        await self.app[SESSION].emit({"type": "error", "code": "LIVEKIT_AUTH_FAILED", "message": "Access denied."})
        await asyncio.wait_for(self.app[SESSION].job, 1)
        self.assertTrue(FakeProvider.instances[0].stopped)
        self.assertEqual(self.app[SESSION].state, "error")
        self.assertFalse(self.app[SESSION].microphone)

    async def test_page_disappearing_stops_capture(self):
        self.app[SESSION].lease_seconds = .01
        await self.post("save", self.fields)
        await self.post("conversation")
        await asyncio.wait_for(self.app[SESSION].job, 1)
        self.assertTrue(FakeProvider.instances[0].stopped)
        self.assertEqual(self.app[SESSION].error["code"], "TEST_PAGE_CLOSED")
        self.assertFalse(self.app[SESSION].microphone)

    async def test_repeated_end_does_not_cancel_cleanup(self):
        await self.post("save", self.fields)
        await self.post("conversation")
        await asyncio.sleep(.02)
        provider = FakeProvider.instances[0]
        original_stop = provider.stop
        closing = asyncio.Event()
        async def slow_stop():
            closing.set()
            await asyncio.sleep(.08)
            await original_stop()
        provider.stop = slow_stop
        first = asyncio.create_task(self.app[SESSION].end())
        await closing.wait()
        second = asyncio.create_task(self.app[SESSION].end())
        await asyncio.gather(first, second)
        self.assertTrue(provider.stopped)
        self.assertFalse(provider.secrets)
        self.assertIsNone(self.app[SESSION].provider)

    async def test_voice_choice_reaches_preview_without_microphone_capture(self):
        await self.post("save", self.fields)
        response = await self.post("audition", {"voice": "Olivia"})
        self.assertEqual(response.status, 200)
        await asyncio.wait_for(self.app[SESSION].job, 1)
        provider = FakeProvider.instances[0]
        self.assertEqual(provider.config["livekit_voice"], "Olivia")
        self.assertFalse(provider.transport._capture)
        provider._session.say.assert_awaited_once()
        self.assertFalse(self.app[SESSION].microphone)
        # A stub that returns no audio must not claim a successful audition.
        self.assertEqual(self.app[SESSION].error["code"], "VOICE_SAMPLE_EMPTY")

    async def test_unlisted_voice_cannot_start_audio_or_change_selection(self):
        await self.post("save", self.fields)
        response = await self.post("audition", {"voice": "invented-voice"})
        self.assertEqual(response.status, 400)
        self.assertEqual(self.app[SESSION].selected_voice, "Ashley")
        self.assertEqual(FakeProvider.instances, [])


if __name__ == "__main__":
    unittest.main()
