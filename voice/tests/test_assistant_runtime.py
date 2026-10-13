import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import assistant_worker
from maslow_voice.assistant_runtime import AssistantClient
from maslow_voice.errors import VoiceError


class AssistantClientTests(unittest.IsolatedAsyncioTestCase):
    def client(self, status, cooldown):
        router = Mock(cooldown_message=Mock(return_value=cooldown))
        client = AssistantClient("http://127.0.0.1:18574", "fixture-token", Mock(returncode=None), router, "task")
        client.request = AsyncMock(return_value=status)
        return client

    async def test_running_quota_is_reported_before_hermes_retries_finish(self):
        client = self.client({"status": "running"}, "Use Continue after the account cooldown.")
        with self.assertRaises(VoiceError) as caught:
            await client.status("run")
        self.assertEqual(caught.exception.code, "FREE_AI_QUOTA_PAUSED")
        self.assertEqual(caught.exception.message, client.router.cooldown_message.return_value)

    async def test_terminal_quota_uses_authoritative_router_not_raw_error(self):
        for status in ("failed", "interrupted"):
            with self.subTest(status=status):
                client = self.client({"status": status, "error": "private provider error"}, "Safe account cooldown.")
                with self.assertRaises(VoiceError) as caught:
                    await client.status("run")
                self.assertEqual(caught.exception.message, "Safe account cooldown.")

    async def test_no_cooldown_preserves_failed_status_without_guessing_error_text(self):
        status = {"status": "failed", "error": "rate_limit_exceeded"}
        self.assertEqual(await self.client(status, None).status("run"), status)

    async def test_cooldown_cannot_replace_a_completed_or_cancelled_result(self):
        for state in ("completed", "cancelled", "stopping"):
            with self.subTest(state=state):
                status = {"status": state, "output": "checked result"}
                client = self.client(status, "Cooldown from another inference call.")
                self.assertEqual(await client.status("run"), status)
                client.router.cooldown_message.assert_not_called()


class AssistantWorkerTests(unittest.TestCase):
    def agent(self, retries=1, recovery=0, tools=None):
        class FakeAgent:
            def __init__(self, **kwargs):
                self.valid_tool_names = assistant_worker.TOOLS if tools is None else tools
                if retries is not None:
                    self._api_max_retries = retries
                if recovery is not None:
                    self._auto_recovery_cycles = recovery
        module = types.ModuleType("run_agent")
        module.AIAgent = FakeAgent
        with patch.dict("sys.modules", {"run_agent": module}), patch.dict("os.environ", {"MASLOW_ASSISTANT_ACCOUNTS": "0"}):
            return assistant_worker.install_boundary()()

    def test_supported_reviewed_retry_contract_is_accepted(self):
        self.agent()

    def test_ignored_or_missing_retry_controls_fail_closed(self):
        for retries, recovery in ((3, 0), (1, 5), (None, 0), (1, None)):
            with self.subTest(retries=retries, recovery=recovery), self.assertRaisesRegex(RuntimeError, "retry compatibility gate"):
                self.agent(retries, recovery)

    def test_retry_control_does_not_relax_tool_allowlist(self):
        with self.assertRaisesRegex(RuntimeError, "tool compatibility gate"):
            self.agent(tools=assistant_worker.TOOLS | {"terminal"})

