import unittest
from unittest.mock import AsyncMock, patch

from maslow_voice.providers.local import LocalProvider


class LocalConversationTests(unittest.IsolatedAsyncioTestCase):
    def provider(self, mode="server", **config):
        self.emitted, self.submitted = [], []
        async def emit(event):
            self.emitted.append(event)
        async def submit(intent, turn_id):
            self.submitted.append(intent)
            return {"id": "task"}
        return LocalProvider(config={"mode": mode, "server_kind": "ollama", "model": "local", "server_url": "https://models.example", **config},
                             secrets={}, emit=emit, submit=submit)

    async def test_remote_server_is_supported_and_greeting_creates_no_task(self):
        provider = self.provider()
        await provider.start(audio=False)
        with patch("maslow_voice.providers.local.request_json", AsyncMock(return_value={"message": {"content": '{"reply":"Hello!","intent":null}'}})) as request:
            await provider.text("Hello")
        self.assertEqual(request.call_args.args[0], "https://models.example/api/chat")
        self.assertEqual(self.submitted, [])
        self.assertEqual(self.emitted[-2]["text"], "Hello!")

    async def test_offline_cannot_use_host_http(self):
        provider = self.provider(mode="offline")
        with self.assertRaisesRegex(Exception, "isolated"):
            await provider.start(audio=False)
        isolated = AsyncMock(return_value={"message": {"content": '{"reply":"What folder should I use?","intent":null}'}})
        provider = self.provider(mode="offline", model_request=isolated)
        await provider.start(audio=False)
        with patch("maslow_voice.providers.local.request_json", side_effect=AssertionError("host HTTP forbidden")):
            await provider.text("Fix the project")
        isolated.assert_awaited_once()
        self.assertEqual(self.submitted, [])

    async def test_clear_work_hands_off_once_and_never_claims_completion(self):
        provider = self.provider()
        await provider.start(audio=False)
        intent = {"objective": "Fix tests", "summary": "Fix the failing tests", "constraints": [], "requested_output": "Passing tests", "tool_preference": "codex", "unresolved_questions": []}
        provider._conversation_from_model = AsyncMock(return_value={"reply": "Done", "intent": intent})
        await provider.text("Fix the failing tests")
        self.assertEqual(self.submitted, [intent])
        self.assertIn("sent that request to Hermes", self.emitted[-2]["text"])
