"""SDK-surface checks; skipped only when optional provider dependencies are absent."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from maslow_voice.providers.livekit_expressive import LiveKitExpressiveProvider


class LiveKitNoNetworkTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        try:
            from livekit import agents
        except ImportError:
            self.skipTest("LiveKit provider dependencies are not installed")
        prewarm = patch.object(agents.inference.LLM, "prewarm")
        prewarm.start()
        self.addCleanup(prewarm.stop)


class LiveKitSdkSurfaceTests(LiveKitNoNetworkTest):
    async def test_expressive_agent_session_and_room_token_construct(self) -> None:
        try:
            from livekit import api, agents
            from livekit.agents import inference
        except ImportError:
            self.skipTest("LiveKit provider dependencies are not installed")

        session = agents.AgentSession(
            stt=inference.STT(model="deepgram/nova-3", language="en", api_key="a" * 32, api_secret="b" * 32),
            llm=inference.LLM(model="google/gemma-4-31b-it", api_key="a" * 32, api_secret="b" * 32),
            tts=inference.TTS(model="inworld/inworld-tts-2", voice="Ashley", api_key="a" * 32, api_secret="b" * 32),
            expressive=True,
        )
        token = (
            api.AccessToken("test-key", "a" * 32)
            .with_identity("maslow-voice-agent")
            .with_name("maslow-voice-agent")
            .with_grants(api.VideoGrants(room_join=True, room="voice-test"))
            .with_inference_grants(api.InferenceGrants(perform=True))
            .to_jwt()
        )
        self.assertIsInstance(session, agents.AgentSession)
        self.assertGreater(len(token), 20)


class LiveKitProviderConstructionTests(LiveKitNoNetworkTest):
    async def test_our_named_agent_session_factory_uses_the_installed_sdk(self) -> None:
        try:
            from livekit import api, agents, rtc
        except ImportError:
            self.skipTest("LiveKit provider dependencies are not installed")

        async def emit(_event: dict) -> None:
            return None

        async def submit(_intent: dict) -> dict:
            return {}

        provider = LiveKitExpressiveProvider(
            config={"mode": "livekit", "livekit_agent_name": "maslow-voice-agent"},
            secrets={},
            emit=emit,
            submit=submit,
        )
        self.addAsyncCleanup(provider.stop)
        provider.room_name = "voice-test"
        token = provider._token(api, "a" * 32, "b" * 32, provider.agent_name)
        session = provider._create_agent_session(agents, "a" * 32, "b" * 32)
        room = rtc.Room()
        self.assertGreater(len(token), 20)
        self.assertIsInstance(session, agents.AgentSession)
        self.assertTrue(callable(room.connect))

    async def test_tool_call_is_bound_to_generation_message_even_after_new_input(self):
        try:
            from livekit import agents
            from livekit.agents.voice.speech_handle import SpeechHandle
        except ImportError:
            self.skipTest("LiveKit provider dependencies are not installed")
        events, submitted = [], []
        async def emit(event):
            events.append(event)
        async def submit(intent, turn_id):
            submitted.append(turn_id)
            return {"id": "task"}
        provider = LiveKitExpressiveProvider(config={"mode": "livekit"}, secrets={}, emit=emit, submit=submit)
        self.addAsyncCleanup(provider.stop)
        session = provider._create_agent_session(agents, "a" * 32, "b" * 32)
        provider._started = True
        first = agents.llm.ChatMessage(role="user", content=["Fix the first project"])
        second = agents.llm.ChatMessage(role="user", content=["Tell me something else"])
        async def generation(agent, chat_ctx, tools, settings):
            message = chat_ctx.items[-1]
            yield agents.llm.ChatChunk(id="chunk", delta=agents.llm.ChoiceDelta(tool_calls=[
                agents.llm.FunctionToolCall(name="submit_intent", arguments="{}", call_id="call-" + message.id)]))
        with patch.object(agents.Agent.default, "llm_node", generation):
            for message in (first, second):
                async for _chunk in provider._agent.llm_node(agents.llm.ChatContext(items=[message]), [], None):
                    pass
        handle = SpeechHandle.create()
        context = agents.RunContext(session=session, speech_handle=handle,
            function_call=agents.llm.FunctionCall(call_id="call-" + first.id, name="submit_intent", arguments="{}"))
        result = await provider._agent.submit_intent(context, objective="Fix it", summary="Fix the first project", constraints=[],
            requested_output="A tested fix", tool_preference="auto", unresolved_questions=[])
        self.assertEqual(result, "SUBMITTED: The work request was submitted for the host to review.")
        self.assertEqual(submitted, [first.id])
        self.assertEqual([event["turn_id"] for event in events], [first.id, second.id])
        interrupted = SpeechHandle.create()
        interrupted.interrupt()
        context = agents.RunContext(session=session, speech_handle=interrupted,
            function_call=agents.llm.FunctionCall(call_id="call-" + second.id, name="submit_intent", arguments="{}"))
        result = await provider._agent.submit_intent(context, objective="Other", summary="Other", constraints=[],
            requested_output="", tool_preference="auto", unresolved_questions=[])
        self.assertEqual(
            result,
            "NOT_SUBMITTED: No work was submitted or started. Ask the user to clarify the request.",
        )
        self.assertEqual(submitted, [first.id])

    async def test_invalid_tool_preference_is_truthfully_not_submitted(self):
        try:
            from livekit import agents
            from livekit.agents.voice.speech_handle import SpeechHandle
        except ImportError:
            self.skipTest("LiveKit provider dependencies are not installed")
        submitted = []
        async def emit(_event):
            return None
        async def submit(intent, turn_id):
            submitted.append((intent, turn_id))
            return {"id": "task"}
        provider = LiveKitExpressiveProvider(config={"mode": "livekit"}, secrets={}, emit=emit, submit=submit)
        self.addAsyncCleanup(provider.stop)
        session = provider._create_agent_session(agents, "a" * 32, "b" * 32)
        provider._started = True
        message = agents.llm.ChatMessage(role="user", content=["Create the report with Hermes"])
        call_id = "call-" + message.id
        provider._tool_turns[call_id] = message.id
        context = agents.RunContext(
            session=session,
            speech_handle=SpeechHandle.create(),
            function_call=agents.llm.FunctionCall(call_id=call_id, name="submit_intent", arguments="{}"),
        )
        result = await provider._agent.submit_intent(
            context,
            objective="Create the report",
            summary="Create the requested report with Hermes",
            constraints=[],
            requested_output="A report",
            tool_preference="Hermes",
            unresolved_questions=[],
        )
        self.assertEqual(
            result,
            "NOT_SUBMITTED: No work was submitted or started. Ask the user to clarify the request.",
        )
        self.assertEqual(submitted, [])
