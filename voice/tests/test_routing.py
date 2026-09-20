import asyncio
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from maslow_voice.errors import VoiceError
from maslow_voice.execution import ExecutionManager
from maslow_voice.routing import AgentRouter, DirectExecutionClient
from maslow_voice.store import TaskStore
from maslow_voice.tasks import TaskManager


BRIEF = {
    "objective": "Fix navigation",
    "summary": "Fix the selected project's navigation.",
    "constraints": ["Preserve unrelated changes"],
    "requested_output": "A tested change",
    "tool_preference": "auto",
    "unresolved_questions": [],
}


class CompletingAdapter:
    async def run(self, task, child, instructions, approval, progress):
        self.instructions = instructions
        return {"result": "Navigation fixed", "provider_session_id": "direct-session"}

    async def cancel(self):
        return None


class BlockingAdapter:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, task, child, instructions, approval, progress):
        self.started.set()
        await self.release.wait()
        return {"result": "done"}

    async def cancel(self):
        self.release.set()


class SteerableAdapter:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.instructions = []

    async def run(self, task, child, instructions, approval, progress):
        self.started.set()
        await self.release.wait()
        return {"result": "redirected"}

    async def steer(self, text):
        self.instructions.append(text)

    async def cancel(self):
        self.release.set()


class ApprovalAdapter:
    def __init__(self):
        self.started = asyncio.Event()
        self.allowed = None

    async def run(self, task, child, instructions, approval, progress):
        self.started.set()
        self.allowed = await approval(provider_request_id="provider-request", tool_name="command",
                                      message="Run the focused tests")
        return {"result": "approved"}

    async def cancel(self):
        return None


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = TaskStore(self.temp.name)
        self.publish = AsyncMock()

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    def task(self, request="request-1", *, preference="auto"):
        brief = dict(BRIEF, tool_preference=preference)
        task, _ = self.store.create(request, brief, self.temp.name, "gemini_live", "Please fix navigation")
        return self.store.update(task["id"], session_id=task["id"], preferred_coder="auto")

    async def test_auto_prefers_ready_configured_default_then_fixed_fallback_order(self):
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter(), "claude": CompletingAdapter()})
        settings = SimpleNamespace(value={"default_coder": "claude"})
        router = AgentRouter(execution, AsyncMock(), settings=settings, hermes_readiness=AsyncMock(return_value=True))

        selected = await router.select_agent(self.task())

        self.assertEqual(selected["selected_agent"], "claude")
        self.assertEqual(selected["routing_reason"], "Claude is the configured default and is ready.")

        settings.value["default_coder"] = "auto"
        selected = await router.select_agent(self.task("request-2"))
        self.assertEqual(selected["selected_agent"], "codex")

    async def test_explicit_unavailable_agent_fails_without_fallback(self):
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        hermes = AsyncMock(return_value=object())
        router = AgentRouter(execution, hermes, hermes_readiness=AsyncMock(return_value=True))

        with self.assertRaises(VoiceError) as raised:
            await router.select_agent(self.task(preference="claude"), "claude")

        self.assertEqual(raised.exception.code, "AGENT_UNAVAILABLE")
        hermes.assert_not_awaited()

    async def test_review_revalidation_preserves_original_routing_reason(self):
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        router = AgentRouter(execution, AsyncMock(), hermes_readiness=AsyncMock(return_value=False))
        created = self.task()
        task = self.store.update(created["id"], selected_agent="codex", routing_reason="Codex was first in automatic routing order.")

        selected = await router.validate_selected(task)

        self.assertEqual(selected, {"selected_agent": "codex", "routing_reason": task["routing_reason"]})

    async def test_hermes_selection_returns_daemon_supplied_client(self):
        expected = object()
        hermes = AsyncMock(return_value=expected)
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        router = AgentRouter(execution, hermes)
        task = self.task(preference="hermes")

        selection = await router.select_agent(task, "hermes")
        saved = self.store.update(task["id"], **selection)

        self.assertIs(await router.client(saved), expected)
        hermes.assert_awaited_once_with(task)

    async def test_legacy_task_without_selection_keeps_hermes_client(self):
        expected = object()
        hermes = AsyncMock(return_value=expected)
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        router = AgentRouter(execution, hermes, hermes_readiness=AsyncMock(return_value=True))
        task = self.task()

        self.assertIs(await router.client(task), expected)
        hermes.assert_awaited_once_with(task)

    async def test_task_manager_persists_direct_agent_owner_and_plain_reason(self):
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        router = AgentRouter(execution, AsyncMock(), settings=SimpleNamespace(value={"default_coder": "codex"}),
                             hermes_readiness=AsyncMock(return_value=False))
        manager = TaskManager(self.store, router.client, self.publish)
        manager.agent_selector = router.select_agent

        task = await manager.submit("reviewed-request", BRIEF, self.temp.name, "gemini_live", "Please fix navigation",
                                    preferred_coder="codex", policy="review")

        self.assertEqual(task["selected_agent"], "codex")
        self.assertEqual(task["owner"], "Codex")
        self.assertEqual(task["routing_reason"], "Codex is the configured default and is ready.")
        self.assertEqual(task["state"], "proposed")
        await manager.close()

    async def test_duplicate_submit_returns_persisted_route_without_rechecking_readiness(self):
        readiness = AsyncMock(return_value=True)
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        router = AgentRouter(execution, AsyncMock(), settings=SimpleNamespace(value={"default_coder": "hermes"}),
                             hermes_readiness=readiness)
        manager = TaskManager(self.store, router.client, self.publish)
        manager.agent_selector = router.select_agent

        first = await manager.submit("same-request", BRIEF, self.temp.name, "gemini_live", "Please fix navigation",
                                     preferred_coder="hermes", policy="review")
        readiness.return_value = False
        replay = await manager.submit("same-request", BRIEF, self.temp.name, "gemini_live", "Please fix navigation",
                                      preferred_coder="hermes", policy="review")

        self.assertEqual(replay["id"], first["id"])
        self.assertEqual(replay["selected_agent"], "hermes")
        self.assertEqual(readiness.await_count, 1)
        await manager.close()

    async def test_cancel_during_submit_selection_never_resurrects_or_starts_task(self):
        selector_started, release_selector = asyncio.Event(), asyncio.Event()

        async def blocked_selector(task, requested=None):
            selector_started.set()
            await release_selector.wait()
            return {"selected_agent": "codex", "routing_reason": "Codex is ready."}

        factory = AsyncMock()
        manager = TaskManager(self.store, factory, self.publish)
        manager.agent_selector = blocked_selector
        submitting = asyncio.create_task(manager.submit(
            "cancel-routing", BRIEF, self.temp.name, "gemini_live", "Please fix navigation",
            preferred_coder="codex", policy="lab_auto"))
        await selector_started.wait()
        task_id = self.store.list()[0]["id"]

        await manager.action(task_id, "cancel")
        release_selector.set()
        result = await submitting

        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(self.store.get(task_id)["state"], "cancelled")
        factory.assert_not_awaited()
        self.assertFalse(manager.monitors)
        await manager.close()

    async def test_cancel_during_proposal_revalidation_never_resurrects_or_starts_task(self):
        factory = AsyncMock()
        manager = TaskManager(self.store, factory, self.publish)
        manager.agent_selector = AsyncMock(return_value={"selected_agent": "codex", "routing_reason": "Codex is ready."})
        proposed = await manager.submit(
            "cancel-proposal-start", BRIEF, self.temp.name, "gemini_live", "Please fix navigation",
            preferred_coder="codex", policy="review")
        selector_started, release_selector = asyncio.Event(), asyncio.Event()

        async def blocked_revalidation(task, requested=None):
            selector_started.set()
            await release_selector.wait()
            return {"selected_agent": "codex", "routing_reason": task["routing_reason"]}

        manager.agent_selector = blocked_revalidation
        starting = asyncio.create_task(manager.action(proposed["id"], "start"))
        await selector_started.wait()

        await manager.action(proposed["id"], "cancel")
        release_selector.set()
        result = await starting

        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(self.store.get(proposed["id"])["state"], "cancelled")
        factory.assert_not_awaited()
        self.assertFalse(manager.monitors)
        await manager.close()

    async def test_recovery_interrupts_direct_run_without_factory_or_resubmission(self):
        created = self.task()
        self.store.update(created["id"], state="submitting", selected_agent="codex",
                          routing_reason="Codex is the configured default and is ready.")
        factory = AsyncMock()
        manager = TaskManager(self.store, factory, self.publish)

        await manager.recover()

        recovered = self.store.get(created["id"])
        self.assertEqual(recovered["state"], "interrupted")
        self.assertEqual(recovered["error"]["code"], "DIRECT_RUN_LOST")
        factory.assert_not_awaited()
        self.assertFalse(manager.monitors)
        await manager.close()

    async def test_explicit_routing_failure_is_persisted_without_hermes_fallback(self):
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        router = AgentRouter(execution, AsyncMock(), hermes_readiness=AsyncMock(return_value=False))
        manager = TaskManager(self.store, router.client, self.publish)
        manager.agent_selector = router.select_agent
        brief = dict(BRIEF, tool_preference="claude")

        with self.assertRaises(VoiceError) as raised:
            await manager.submit("unavailable-claude", brief, self.temp.name, "gemini_live", "Use Claude for this",
                                 preferred_coder="hermes")

        failed = self.store.list()[0]
        self.assertEqual(raised.exception.code, "AGENT_UNAVAILABLE")
        self.assertEqual(failed["state"], "failed")
        self.assertEqual(failed["selected_agent"], "claude")
        self.assertEqual(failed["owner"], "Claude")
        self.assertEqual(failed["routing_reason"], "Agent selection failed.")
        await manager.close()

    async def test_direct_client_runs_adapter_with_task_manager_protocol(self):
        adapter = CompletingAdapter()
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": adapter})
        created = self.task()
        task = self.store.update(created["id"], selected_agent="codex", routing_reason="Codex is ready.")
        client = DirectExecutionClient(execution, "codex")

        submitted = await client.submit(task)
        await client.job
        status = await client.status(submitted["run_id"])

        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["output"], "Navigation fixed")
        self.assertIn("Original request:\nPlease fix navigation", adapter.instructions)
        self.assertEqual(self.store.get(task["id"])["children"][0]["tool"], "codex")

    async def test_new_direct_client_cannot_resume_or_resubmit_known_run(self):
        adapter = BlockingAdapter()
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": adapter})
        created = self.task()
        task = self.store.update(created["id"], selected_agent="codex", routing_reason="Codex is ready.")
        first = DirectExecutionClient(execution, "codex")
        submitted = await first.submit(task)
        await adapter.started.wait()

        restarted = DirectExecutionClient(execution, "codex")
        with self.assertRaises(VoiceError) as raised:
            await restarted.status(submitted["run_id"])
        self.assertEqual(raised.exception.code, "NOT_FOUND")

        await first.stop(submitted["run_id"])

    async def test_direct_client_preserves_one_tool_approval(self):
        adapter = ApprovalAdapter()
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": adapter})
        created = self.task()
        task = self.store.update(created["id"], selected_agent="codex", routing_reason="Codex is ready.")
        client = DirectExecutionClient(execution, "codex")
        submitted = await client.submit(task)
        await adapter.started.wait()
        for _ in range(20):
            approval = self.store.get(task["id"]).get("approval")
            if approval:
                break
            await asyncio.sleep(0)

        await client.approve(submitted["run_id"], approval["request_id"], True)
        await client.job

        self.assertTrue(adapter.allowed)
        self.assertEqual((await client.status(submitted["run_id"]))["status"], "completed")

    async def test_direct_codex_steer_persists_the_outcome_and_activity(self):
        adapter = SteerableAdapter()
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": adapter})
        created = self.task()
        task = self.store.update(created["id"], selected_agent="codex", routing_reason="Codex is ready.")
        client = DirectExecutionClient(execution, "codex")
        submitted = await client.submit(task)
        await adapter.started.wait()

        await client.steer(submitted["run_id"], "Make it simpler")

        saved = self.store.get(task["id"])
        self.assertEqual(adapter.instructions, ["Make it simpler"])
        self.assertEqual(saved["instruction_outcomes"][-1]["outcome"], "accepted")
        self.assertEqual(saved["activity"][-1], {"kind": "instruction", "text": "Correction sent to Codex."})
        adapter.release.set()
        await client.job

    async def test_direct_status_exposes_the_child_error(self):
        execution = ExecutionManager(self.store, self.publish, adapters={"codex": CompletingAdapter()})
        created = self.task()
        task = self.store.update(created["id"], children=[{
            "id": "child-1", "tool": "codex", "status": "failed", "result": "",
            "error": {"code": "CODEX_RESUME_FAILED", "message": "Resume failed"},
        }])
        client = DirectExecutionClient(execution, "codex")
        client.task_id, client.child_id, client.run_id = task["id"], "child-1", "direct:failed"

        status = await client.status("direct:failed")

        self.assertEqual(status["error"]["code"], "CODEX_RESUME_FAILED")


if __name__ == "__main__":
    unittest.main()
