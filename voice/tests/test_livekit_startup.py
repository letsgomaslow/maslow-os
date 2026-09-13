"""Exercise the installed LiveKit SDK without accounts, sockets or audio devices."""
from __future__ import annotations

import asyncio
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.providers.base import ProviderError
from maslow_voice.providers.livekit_expressive import LiveKitExpressiveProvider


class LiveKitStartupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        try:
            import aiohttp
            import httpx
            from livekit import agents, api, rtc
        except ImportError:
            self.skipTest("LiveKit provider dependencies are not installed")
        self.agents, self.api, self.rtc = agents, api, rtc
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        # SDK construction may prewarm clients. No request belongs in these
        # tests; exercise lazy acquisition and transport routing locally.
        self.patches.enter_context(patch.object(agents.inference.LLM, "prewarm"))
        self.patches.enter_context(patch.object(agents.inference.TTS, "prewarm"))
        self.aiohttp_request = self.patches.enter_context(patch.object(aiohttp.ClientSession, "_request", side_effect=AssertionError("unexpected HTTP request")))
        self.httpx_send = self.patches.enter_context(patch.object(httpx.AsyncClient, "send", side_effect=AssertionError("unexpected HTTP request")))
        self.events = []
        async def emit(event):
            self.events.append(event)
        self.audio = SimpleNamespace(start=AsyncMock(), stop=AsyncMock(), play=AsyncMock())
        self.provider = LiveKitExpressiveProvider(
            config={"mode": "livekit", "livekit_url": "wss://voice.invalid"},
            secrets={"livekit_key": "a" * 32, "livekit_secret": "b" * 32},
            emit=emit, submit=AsyncMock(), audio_transport=self.audio)
        self.addAsyncCleanup(self.provider.stop)

    async def asyncTearDown(self):
        self.aiohttp_request.assert_not_called()
        self.httpx_send.assert_not_called()

    def fake_room_transport(self):
        rooms = [SimpleNamespace(on=Mock(), connect=AsyncMock(), disconnect=AsyncMock(),
                 local_participant=SimpleNamespace(publish_track=AsyncMock())) for _ in range(2)]
        source = SimpleNamespace(aclose=AsyncMock())
        track = object()
        self.patches.enter_context(patch.object(self.rtc, "Room", side_effect=rooms))
        self.patches.enter_context(patch.object(self.rtc, "AudioSource", return_value=source))
        self.patches.enter_context(patch.object(self.rtc.LocalAudioTrack, "create_audio_track", return_value=track))
        return rooms, source, track

    async def test_real_sdk_starts_outside_worker_and_lazy_http_clients_close(self):
        from livekit.agents.utils import http_context
        with self.assertRaisesRegex(RuntimeError, "outside of a job context"):
            http_context.http_session()
        session = self.provider._create_agent_session(self.agents, "a" * 32, "b" * 32)
        self.provider._session = session
        # Real SDK startup with no room or audio device does not need a job
        # worker. Replace only the STT node's external events; exercise the
        # real lazy HTTP acquisition explicitly below without opening a socket.
        async def no_external_transcripts(*args, **kwargs):
            if False:
                yield
        with patch.object(self.provider._agent, "stt_node", no_external_transcripts):
            await session.start(agent=self.provider._agent, record=False)
        owned_http = self.provider._http_session
        llm_client = session.llm._client
        self.assertIs(session.stt._ensure_session(), owned_http)
        self.assertIs(session.tts._ensure_session(), owned_http)
        self.assertFalse(owned_http.closed)
        self.assertFalse(llm_client.is_closed())
        await self.provider.stop()
        self.assertTrue(owned_http.closed)
        self.assertTrue(llm_client.is_closed())
        self.assertIsNone(self.provider._http_session)
        self.assertEqual(self.provider._inference_clients, [])

    async def test_start_publishes_actual_sdk_microphone_source_and_stop_closes_rooms(self):
        rooms, source, track = self.fake_room_transport()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", new_callable=AsyncMock))
        await self.provider.start()
        args = rooms[0].local_participant.publish_track.call_args.args
        self.assertIs(args[0], track)
        self.assertIsInstance(args[1], self.rtc.TrackPublishOptions)
        self.assertEqual(args[1].source, self.rtc.TrackSource.SOURCE_MICROPHONE)
        owned_http = self.provider._http_session
        await self.provider.stop()
        self.assertTrue(owned_http.closed)
        for room in rooms:
            room.disconnect.assert_awaited_once()
        source.aclose.assert_awaited_once()
        self.audio.stop.assert_awaited_once()

    async def test_actual_audio_enum_routes_only_named_agent_playback(self):
        track = SimpleNamespace(kind=self.rtc.TrackKind.KIND_AUDIO)
        playback = AsyncMock()
        self.provider._play_remote_track = playback
        self.provider._on_track_subscribed(track, None, SimpleNamespace(identity=self.provider.agent_name))
        await asyncio.gather(*self.provider._audio_tasks)
        playback.assert_awaited_once_with(track)
        self.provider._on_track_subscribed(track, None, SimpleNamespace(identity="someone-else"))
        self.provider._on_track_subscribed(SimpleNamespace(kind=self.rtc.TrackKind.KIND_VIDEO), None,
                                           SimpleNamespace(identity=self.provider.agent_name))
        await asyncio.sleep(0)
        playback.assert_awaited_once()

    async def test_failed_start_closes_http_inference_rooms_and_microphone(self):
        rooms, source, _track = self.fake_room_transport()
        owned = {}
        async def fail_start(*args, **kwargs):
            owned["http"] = self.provider._http_session
            owned["llm"] = self.provider._session.llm._client
            raise RuntimeError("fixture connection failure")
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", side_effect=fail_start))
        with self.assertRaises(ProviderError):
            await self.provider.start()
        self.assertTrue(owned["http"].closed)
        self.assertTrue(owned["llm"].is_closed())
        self.assertFalse(self.provider._started)
        self.assertEqual(self.events[-1]["state"], "error")
        for room in rooms:
            room.disconnect.assert_awaited_once()
        source.aclose.assert_awaited_once()
        self.audio.stop.assert_awaited_once()

    async def test_cancelled_start_closes_owned_http_and_rooms(self):
        rooms, _source, _track = self.fake_room_transport()
        owned = []
        async def cancel_start(*args, **kwargs):
            owned.append(self.provider._http_session)
            raise asyncio.CancelledError()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", side_effect=cancel_start))
        with self.assertRaises(asyncio.CancelledError):
            await self.provider.start()
        self.assertTrue(owned[0].closed)
        for room in rooms:
            room.disconnect.assert_awaited_once()
        self.assertFalse(self.provider._started)

    async def test_session_close_failure_does_not_leak_other_owned_resources(self):
        rooms, source, _track = self.fake_room_transport()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", new_callable=AsyncMock))
        await self.provider.start()
        owned_http = self.provider._http_session
        llm_client = self.provider._session.llm._client
        self.provider._session.aclose = AsyncMock(side_effect=RuntimeError("fixture close failure"))
        with self.assertRaisesRegex(RuntimeError, "fixture close failure"):
            await self.provider.stop()
        self.assertTrue(owned_http.closed)
        self.assertTrue(llm_client.is_closed())
        for room in rooms:
            room.disconnect.assert_awaited_once()
        source.aclose.assert_awaited_once()
        self.assertEqual(self.events[-1]["state"], "disabled")


if __name__ == "__main__":
    unittest.main()
