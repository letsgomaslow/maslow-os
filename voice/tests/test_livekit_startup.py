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
        self.audio = SimpleNamespace(start=AsyncMock(), stop=AsyncMock(), play=AsyncMock(), set_muted=AsyncMock())
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

    async def test_audio_start_clears_prior_mute_before_capture_and_reports_microphone_on(self):
        self.fake_room_transport()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", new_callable=AsyncMock))
        self.provider._muted = True
        await self.provider.start()
        self.audio.set_muted.assert_awaited_once_with(False)
        self.audio.start.assert_awaited_once()
        self.assertEqual(self.events[-1], {"type": "voice_state", "state": "listening", "microphone": True, "speaking": False})

    async def test_selected_voice_reaches_the_real_inference_configuration(self):
        self.fake_room_transport()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", new_callable=AsyncMock))
        self.provider.config["livekit_voice"] = "Olivia"
        await self.provider.start()
        self.assertEqual(self.provider._session.tts._opts.voice, "Olivia")

    async def test_intent_tool_builds_strict_schema_without_injected_context(self):
        self.provider._create_agent_session(self.agents, "a" * 32, "b" * 32)
        schema = self.agents.ToolContext(self.provider._agent.tools).parse_function_tools("openai", strict=True)
        function = schema[0]["function"]
        parameters = function["parameters"]
        expected = {"objective", "summary", "constraints", "requested_output", "tool_preference", "unresolved_questions"}
        self.assertEqual(function["name"], "submit_intent")
        self.assertTrue(function["strict"])
        self.assertEqual(set(parameters["properties"]), expected)
        self.assertEqual(set(parameters["required"]), expected)
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(
            parameters["properties"]["tool_preference"]["enum"],
            ["auto", "codex", "claude", "hermes"],
        )

    async def test_fatal_sdk_error_is_actionable_safe_and_revokes_turns(self):
        from livekit.agents import APIStatusError
        self.fake_room_transport()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", new_callable=AsyncMock))
        await self.provider.start()
        failure = SimpleNamespace(error=APIStatusError("https://private.invalid?token=do-not-display", status_code=401), recoverable=False)
        self.provider._session.emit("error", SimpleNamespace(error=failure))
        await asyncio.gather(*self.provider._event_tasks)
        error = next(event for event in self.events if event["type"] == "error")
        self.assertEqual(error["code"], "LIVEKIT_AUTH_FAILED")
        self.assertIn("Settings", error["message"])
        self.assertNotIn("do-not-display", str(self.events))
        self.assertFalse(self.provider._started)
        with self.assertRaises(ProviderError):
            await self.provider._submit_intent({}, "old-turn")
        self.provider._agent_state(SimpleNamespace(new_state="listening"))
        self.assertEqual(self.events[-1]["state"], "error")

    async def test_recoverable_sdk_error_keeps_session_running(self):
        self.fake_room_transport()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", new_callable=AsyncMock))
        await self.provider.start()
        self.provider._session.emit("error", SimpleNamespace(error=SimpleNamespace(recoverable=True)))
        await asyncio.sleep(0)
        self.assertTrue(self.provider._started)
        self.assertFalse(any(event["type"] == "error" for event in self.events))

    async def test_room_disconnect_and_unexpected_session_close_emit_once_but_intentional_stop_does_not(self):
        rooms, _source, _track = self.fake_room_transport()
        self.patches.enter_context(patch.object(self.agents.AgentSession, "start", new_callable=AsyncMock))
        await self.provider.start()
        callbacks = dict(call.args for call in rooms[0].on.call_args_list)
        callbacks["disconnected"](None)
        self.provider._session.emit("close", SimpleNamespace(error=None))
        await asyncio.gather(*self.provider._event_tasks)
        errors = [event for event in self.events if event["type"] == "error"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["code"], "LIVEKIT_DISCONNECTED")
        await self.provider.stop()
        self.events.clear()
        self.provider._session_closed(SimpleNamespace(error=None))
        self.provider._room_disconnected(None)
        await asyncio.sleep(0)
        self.assertEqual(self.events, [])

    async def test_session_close_without_prior_error_is_not_silent(self):
        self.provider._started = True
        self.provider._session_closed(SimpleNamespace(error=None))
        await asyncio.gather(*self.provider._event_tasks)
        self.assertEqual(self.events[0]["code"], "LIVEKIT_SESSION_FAILED")

    async def test_usage_error_maps_status_without_returning_diagnostics(self):
        from livekit.agents import APIStatusError
        for status in (402, 429):
            public = self.provider._public_error(APIStatusError("private billing details", status_code=status))
            self.assertEqual(public.code, "LIVEKIT_USAGE_LIMIT")
            self.assertNotIn("private", public.message)

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

    async def test_remote_silent_packets_do_not_override_agent_listening_state(self):
        frame = self.rtc.AudioFrame(b"\0\0" * 480, 48000, 1, 480)
        class Stream:
            def __init__(self):
                self.frames = iter([SimpleNamespace(frame=frame), SimpleNamespace(frame=frame)])
                self.aclose = AsyncMock()
            def __aiter__(self):
                return self
            async def __anext__(self):
                try:
                    return next(self.frames)
                except StopIteration:
                    raise StopAsyncIteration
        stream = Stream()
        self.provider._started = self.provider._audio_enabled = True
        self.provider._agent_state(SimpleNamespace(new_state="listening"))
        await asyncio.gather(*self.provider._event_tasks)
        with patch.object(self.rtc, "AudioStream", return_value=stream):
            await self.provider._play_remote_track(object())
        self.assertEqual(self.audio.play.await_count, 2)
        self.assertEqual([event["state"] for event in self.events if event["type"] == "voice_state"], ["listening"])
        stream.aclose.assert_awaited_once()

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
