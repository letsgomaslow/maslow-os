import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from maslow_voice.errors import VoiceError
from maslow_voice.execution import (
    ClaudeSdkAdapter, CodexAppServerAdapter, ExecutionManager, OfflineCodexAdapter,
    OfflineClaudeAdapter, JsonRpcProcess, _codex_file_change_detail, validate_url,
)
from maslow_voice.store import TaskStore


BRIEF = {"objective": "Fix navigation", "summary": "Fix the selected project's navigation.", "constraints": [],
         "requested_output": "A tested change", "tool_preference": "codex"}


class ApprovalAdapter:
    def __init__(self):
        self.started = asyncio.Event()
        self.allowed = None

    async def run(self, task, child, instructions, approval, progress):
        self.started.set()
        self.allowed = await approval(provider_request_id="provider-approval", tool_name="command",
                                      message="Run the focused test", provider_context={"itemId": "item-1"})
        return {"result": "Verified result", "provider_session_id": "session-1", "thread_id": "thread-1", "turn_id": "turn-1"}

    async def cancel(self):
        return None


class BlockingAdapter:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = False

    async def run(self, task, child, instructions, approval, progress):
        self.started.set()
        await self.release.wait()
        raise VoiceError("EXECUTION_INTERRUPTED", "Stopped")

    async def cancel(self):
        self.cancelled = True
        self.release.set()


class ExecutionManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = TaskStore(self.temp.name)
        self.published = 0

        async def publish():
            self.published += 1

        self.publish = publish
        self.task, _ = self.store.create("request-1", BRIEF, self.temp.name, "openai", "Fix navigation")
        self.task = self.store.update(self.task["id"], session_id=self.task["id"], preferred_coder="codex")

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def test_child_approval_is_one_shot_and_scoped_to_task_and_child(self):
        adapter = ApprovalAdapter()
        manager = ExecutionManager(self.store, self.publish, adapters={"codex": adapter})
        delegated = asyncio.create_task(manager.handle(self.task, "coding", {"tool": "codex", "instructions": "Fix it"}))
        await adapter.started.wait()
        for _ in range(20):
            current = self.store.get(self.task["id"])
            if current.get("approval"):
                break
            await asyncio.sleep(0)
        approval = current["approval"]
        self.assertEqual(approval["owner"], "child")
        self.assertEqual(approval["provider_request_id"], "provider-approval")

        with self.assertRaises(VoiceError):
            await manager.handle(self.task, "approve", {"approval_id": "stale", "child_id": approval["child_id"]})

        other, _ = self.store.create("request-2", BRIEF, self.temp.name, "openai", "Fix navigation")
        other = self.store.update(other["id"], session_id=other["id"])
        with self.assertRaises(VoiceError):
            await manager.handle(other, "approve", {"approval_id": approval["request_id"], "child_id": approval["child_id"]})

        await manager.handle(self.store.get(self.task["id"]), "approve",
                             {"approval_id": approval["request_id"], "child_id": approval["child_id"]})
        result = await delegated
        self.assertTrue(adapter.allowed)
        self.assertEqual(result["result"], "Verified result")
        child = self.store.get(self.task["id"])["children"][0]
        self.assertEqual((child["provider_session_id"], child["thread_id"], child["turn_id"]),
                         ("session-1", "thread-1", "turn-1"))
        with self.assertRaises(VoiceError):
            await manager.handle(self.store.get(self.task["id"]), "approve",
                                 {"approval_id": approval["request_id"], "child_id": approval["child_id"]})

    async def test_activity_coalesces_only_chunks_of_the_same_message(self):
        manager = ExecutionManager(self.store, self.publish)
        for stream, text in [("turn-1:message-1", "Building "), ("turn-1:message-1", "a calculator."), ("turn-1:message-2", "Now testing.")]:
            await manager._record_activity(self.task["id"], {"kind": "assistant", "text": text, "stream_id": stream})
        activity = self.store.get(self.task["id"])["activity"]
        self.assertEqual([event["text"] for event in activity], ["Building a calculator.", "Now testing."])

    async def test_cancel_cascades_and_leaves_child_cancelled(self):
        adapter = BlockingAdapter()
        manager = ExecutionManager(self.store, self.publish, adapters={"codex": adapter})
        delegated = asyncio.create_task(manager.handle(self.task, "coding", {"tool": "codex", "instructions": "Fix it"}))
        await adapter.started.wait()
        await manager.cancel(self.task["id"])
        with self.assertRaises(VoiceError):
            await delegated
        self.assertTrue(adapter.cancelled)
        self.assertEqual(self.store.get(self.task["id"])["children"][0]["status"], "cancelled")

    async def test_offline_mode_fails_closed_without_isolated_runtime(self):
        offline, _ = self.store.create("offline", BRIEF, self.temp.name, "offline", "Fix navigation")
        offline = self.store.update(offline["id"], session_id=offline["id"])
        host_adapter = ApprovalAdapter()
        manager = ExecutionManager(self.store, self.publish, adapters={"codex": host_adapter})
        with self.assertRaisesRegex(VoiceError, "offline coding sandbox"):
            await manager.handle(offline, "coding", {"tool": "codex", "instructions": "Fix it"})
        self.assertFalse(host_adapter.started.is_set())
        self.assertEqual(self.store.get(offline["id"])["children"][0]["status"], "failed")

    async def test_restart_does_not_replay_a_saved_child_approval(self):
        child_id, approval_id = "child-id", "approval-id"
        saved = self.store.update(self.task["id"], children=[{"id": child_id, "status": "awaiting_approval"}],
                                 approval={"owner": "child", "child_id": child_id, "request_id": approval_id})
        restarted = ExecutionManager(self.store, self.publish)
        with self.assertRaisesRegex(VoiceError, "current child approval"):
            await restarted.handle(saved, "approve", {"child_id": child_id, "approval_id": approval_id})

    async def test_cancel_during_approval_cannot_record_success_after_denial(self):
        adapter = ApprovalAdapter()
        manager = ExecutionManager(self.store, self.publish, adapters={"codex": adapter})
        delegated = asyncio.create_task(manager.handle(self.task, "coding", {"tool": "codex", "instructions": "Fix it"}))
        await adapter.started.wait()
        await manager.cancel(self.task["id"])
        with self.assertRaises(VoiceError):
            await delegated
        self.assertFalse(adapter.allowed)
        self.assertEqual(self.store.get(self.task["id"])["children"][0]["status"], "cancelled")

    async def test_immutable_task_context_cannot_change_project_or_mode(self):
        manager = ExecutionManager(self.store, self.publish, adapters={"codex": ApprovalAdapter()})
        with self.assertRaises(VoiceError) as caught:
            await manager.handle(dict(self.task, project="/tmp"), "readiness")
        self.assertEqual(caught.exception.code, "IMMUTABLE_TASK")

    def test_website_validation_rejects_commands_and_credentials(self):
        self.assertEqual(validate_url("https://example.com/path"), "https://example.com/path")
        for value in ("file:///etc/passwd", "javascript:alert(1)", "https://user:pass@example.com", "https://example.com\n--flag"):
            with self.assertRaises(VoiceError):
                validate_url(value)


class FakeRpc:
    instance = None

    def __init__(self, argv, cwd, **kwargs):
        self.argv, self.cwd, self.kwargs = argv, cwd, kwargs
        self.calls, self.closed = [], False
        FakeRpc.instance = self

    async def start(self):
        self.calls.append(("start", None))

    async def request(self, method, params=None):
        self.calls.append((method, params))
        if method == "initialize":
            return {"userAgent": "test"}
        if method in {"thread/start", "thread/resume"}:
            return {"thread": {"id": "thread-1", "sessionId": "session-1"}}
        if method == "turn/start":
            return {"turn": {"id": "turn-1"}}
        return {}

    async def notify(self, method, params=None):
        self.calls.append((method, params))

    async def next_notification(self):
        if not hasattr(self, "sent_delta"):
            self.sent_delta = True
            return {"method": "item/agentMessage/delta", "params": {"threadId": "thread-1", "turnId": "turn-1", "delta": "Done"}}
        return {"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"}}}

    async def close(self):
        self.closed = True


class CodexAdapterTests(unittest.IsolatedAsyncioTestCase):
    def test_file_change_preview_marks_truncation_and_omitted_changes(self):
        detail = _codex_file_change_detail({"changes": [
            {"path": f"src/file-{index}.py", "diff": "x" * 181, "kind": {"type": "update", "move_path": None}}
            for index in range(7)
        ]}, None)
        self.assertIn("diff preview truncated", detail)
        self.assertIn("1 additional file changes omitted from preview", detail)

    async def test_model_cli_mismatch_is_actionable_without_raw_server_error(self):
        import sys
        from unittest.mock import AsyncMock
        class FailedRpc(FakeRpc):
            async def next_notification(self):
                return {"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {
                    "id": "turn-1", "status": "failed", "error": {"codexErrorInfo": "other",
                    "message": "The configured model requires a newer version of Codex. private-server-detail"}}}}
        adapter = CodexAppServerAdapter(sys.executable, rpc_factory=FailedRpc)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(VoiceError) as error:
                await adapter.run({"project": directory}, {}, "Create index.html", AsyncMock(), AsyncMock())
        self.assertEqual(error.exception.code, "CODEX_UPDATE_REQUIRED")
        self.assertNotIn("private-server-detail", error.exception.message)

    async def test_cancel_during_initialize_terminates_peer_and_unblocks_run(self):
        import sys
        spawned = []
        async def process_factory(argv, *, cwd, env):
            # A real JSONL peer acknowledges receiving initialize, but never
            # answers it. Cancellation must close the child without turn IDs.
            process = await asyncio.create_subprocess_exec(sys.executable, "-u", "-c",
                "import json,sys,time; message=json.loads(sys.stdin.readline()); "
                "assert message['method']=='initialize'; "
                "print(json.dumps({'method':'test/initializeReceived'}),flush=True); time.sleep(60)",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            spawned.append(process)
            return process
        adapter = CodexAppServerAdapter(sys.executable, process_factory=process_factory)
        async def callback(**changes):
            return False
        task = asyncio.create_task(adapter.run({"id": "task", "project": "/unused"}, {}, "Do work", callback, callback))
        try:
            async def initialized():
                while adapter.rpc is None:
                    await asyncio.sleep(0)
                return await adapter.rpc.next_notification()
            self.assertEqual((await asyncio.wait_for(initialized(), 3))["method"], "test/initializeReceived")
            self.assertIsNone(adapter.turn_id)
            await asyncio.wait_for(adapter.cancel(), 3)
            with self.assertRaises(VoiceError):
                await asyncio.wait_for(task, 3)
            self.assertIsNotNone(spawned[0].returncode)
            self.assertTrue(adapter.rpc.closed)
            self.assertIsNone(adapter.thread_id)
        finally:
            for process in spawned:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_app_server_uses_user_review_and_preserves_protocol_ids(self):
        adapter = CodexAppServerAdapter(sys.executable, rpc_factory=FakeRpc)
        progress = []

        async def update(**changes):
            progress.append(changes)

        async def approve(**request):
            return False

        task = {"id": "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5", "project": "/work"}
        result = await adapter.run(task, {"id": "child"}, "Fix navigation", approve, update)
        calls = dict((method, params) for method, params in FakeRpc.instance.calls if method != "start")
        self.assertEqual(calls["thread/start"]["approvalPolicy"], "untrusted")
        self.assertEqual(calls["thread/start"]["approvalsReviewer"], "user")
        self.assertEqual(calls["thread/start"]["sandbox"], "workspace-write")
        self.assertNotIn("danger-full-access", str(FakeRpc.instance.calls))
        self.assertEqual(calls["turn/start"]["input"][0]["text"], "Fix navigation")
        self.assertEqual((result["provider_session_id"], result["thread_id"], result["turn_id"]),
                         ("session-1", "thread-1", "turn-1"))
        with self.assertRaises(VoiceError) as raised:
            await FakeRpc.instance.kwargs["server_request"]("item/commandExecution/requestApproval", {
                "threadId": "another-thread", "turnId": "turn-1", "command": "false",
            }, "approval-1")
        self.assertEqual(raised.exception.code, "CODEX_REQUEST_UNSUPPORTED")
        self.assertTrue(FakeRpc.instance.closed)

    async def test_steer_uses_the_active_thread_and_expected_turn_identity(self):
        adapter = CodexAppServerAdapter(sys.executable, rpc_factory=FakeRpc)
        rpc = FakeRpc([], "/work")
        adapter.rpc, adapter.thread_id, adapter.turn_id = rpc, "thread-1", "turn-1"

        await adapter.steer("Use three columns instead")

        self.assertIn(("turn/steer", {
            "threadId": "thread-1", "expectedTurnId": "turn-1",
            "input": [{"type": "text", "text": "Use three columns instead", "text_elements": []}],
        }), rpc.calls)

    async def test_resume_uses_saved_thread_without_starting_a_new_one(self):
        adapter = CodexAppServerAdapter(sys.executable, rpc_factory=FakeRpc)
        progress = []

        async def update(**changes):
            progress.append(changes)

        async def approve(**request):
            return False

        task = {"id": "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5", "project": "/work"}
        result = await adapter.run(task, {"id": "child", "resume_thread_id": "thread-1"}, "Continue", approve, update)

        methods = [method for method, _params in FakeRpc.instance.calls]
        self.assertIn("thread/resume", methods)
        self.assertNotIn("thread/start", methods)
        calls = dict(FakeRpc.instance.calls)
        self.assertEqual(calls["thread/resume"]["cwd"], "/work")
        self.assertEqual(calls["thread/resume"]["approvalPolicy"], "untrusted")
        self.assertEqual(calls["thread/resume"]["approvalsReviewer"], "user")
        self.assertEqual(calls["thread/resume"]["sandbox"], "workspace-write")
        self.assertEqual(result["thread_id"], "thread-1")
        self.assertTrue(any(change.get("activity", {}).get("kind") == "thread" for change in progress))

    async def test_file_change_activity_only_records_verified_workspace_artifacts(self):
        class FileChangeRpc(FakeRpc):
            async def next_notification(self):
                count = getattr(self, "notification_count", 0)
                self.notification_count = count + 1
                if count == 0:
                    return {"method": "item/completed", "params": {
                        "threadId": "thread-1", "turnId": "turn-1", "itemId": "file-1",
                        "item": {"id": "file-1", "type": "fileChange", "status": "completed",
                                 "changes": [{"path": "result.html", "diff": "", "kind": {"type": "add"}},
                                             {"path": "../../outside", "diff": "", "kind": {"type": "add"}}]},
                    }}
                return {"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"}}}

        with tempfile.TemporaryDirectory() as project:
            Path(project, "result.html").write_text("<title>Result</title>", encoding="utf-8")
            adapter = CodexAppServerAdapter(sys.executable, rpc_factory=FileChangeRpc)
            changes = []
            async def update(**change):
                changes.append(change)
            async def approve(**request):
                return False

            await adapter.run({"id": "task", "project": project}, {"id": "child"}, "Make it", approve, update)

        artifacts = [change["artifact"] for change in changes if "artifact" in change]
        self.assertEqual(artifacts, [{"path": "result.html", "exists": True, "verification": "exists"}] * 2)

    async def test_file_change_approval_uses_only_the_exact_observed_item(self):
        class ApprovalDetailRpc(FakeRpc):
            async def next_notification(self):
                count = getattr(self, "notification_count", 0)
                self.notification_count = count + 1
                if count == 0:
                    return {"method": "item/started", "params": {
                        "threadId": "wrong-thread", "turnId": "turn-1",
                        "item": {"id": "wrong-file", "type": "fileChange", "changes": [
                            {"path": "private/secret.txt", "diff": "+ secret", "kind": {"type": "add"}},
                        ]},
                    }}
                if count == 1:
                    return {"method": "item/started", "params": {
                        "threadId": "thread-1", "turnId": "turn-1",
                        "item": {"id": "other-file", "type": "fileChange", "changes": [
                            {"path": "wrong-item.py", "diff": "+ wrong", "kind": {"type": "add"}},
                        ]},
                    }}
                if count == 2:
                    self.request_started = asyncio.Event()
                    async def request_approval():
                        self.request_started.set()
                        return await self.kwargs["server_request"]("item/fileChange/requestApproval", {
                            "threadId": "thread-1", "turnId": "turn-1", "itemId": "approved-file",
                        }, "right-request")
                    self.server_request_task = asyncio.create_task(request_approval())
                    await self.request_started.wait()
                    return {"method": "item/started", "params": {
                        "threadId": "thread-1", "turnId": "turn-1",
                        "item": {"id": "approved-file", "type": "fileChange", "changes": [
                            {"path": "src/app.py", "diff": "@@ -1 +1 @@\n-old\n+new", "kind": {"type": "update", "move_path": None}},
                        ]},
                    }}
                if count == 3:
                    return {"method": "item/started", "params": {
                        "threadId": "thread-1", "turnId": "turn-1",
                        "item": {"id": "malformed-file", "type": "fileChange", "changes": [
                            {"path": "", "diff": "+ hidden", "kind": {"type": "add"}},
                        ]},
                    }}
                return {"method": "turn/completed", "params": {
                    "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"},
                }}

        requests, progress = [], []
        async def approve(**request):
            requests.append(request)
            return False
        async def update(**change):
            progress.append(change)

        adapter = CodexAppServerAdapter(sys.executable, rpc_factory=ApprovalDetailRpc)
        with tempfile.TemporaryDirectory() as project:
            await adapter.run({"id": "task", "project": project}, {"id": "child"}, "Make it", approve, update)

        callback = FakeRpc.instance.kwargs["server_request"]
        with self.assertRaisesRegex(VoiceError, "different task turn"):
            await callback("item/fileChange/requestApproval", {
                "threadId": "wrong-thread", "turnId": "turn-1", "itemId": "wrong-file",
            }, "wrong-request")
        self.assertEqual(await FakeRpc.instance.server_request_task, {"decision": "decline"})
        self.assertEqual(await callback("item/fileChange/requestApproval", {
            "threadId": "thread-1", "turnId": "turn-1", "itemId": "unobserved-file",
        }, "unobserved-request"), {"decision": "decline"})
        self.assertEqual(await callback("item/fileChange/requestApproval", {
            "threadId": "thread-1", "turnId": "turn-1", "itemId": "malformed-file",
        }, "malformed-request"), {"decision": "decline"})

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[-1]["provider_context"]["itemId"], "approved-file")
        self.assertIn("update: src/app.py", requests[-1]["message"])
        self.assertIn("+new", requests[-1]["message"])
        self.assertNotIn("secret.txt", requests[-1]["message"])
        self.assertNotIn("wrong-item.py", requests[-1]["message"])
        self.assertTrue(any("details were unavailable" in change.get("activity", {}).get("text", "") for change in progress))

    async def test_final_agent_message_is_preferred(self):
        class PhasedMessageRpc(FakeRpc):
            async def next_notification(self):
                count = getattr(self, "notification_count", 0)
                self.notification_count = count + 1
                if count == 0:
                    return {"method": "item/started", "params": {
                        "threadId": "thread-1", "turnId": "turn-1",
                        "item": {"id": "commentary", "type": "agentMessage", "phase": "commentary"},
                    }}
                if count == 1:
                    return {"method": "item/agentMessage/delta", "params": {
                        "threadId": "thread-1", "turnId": "turn-1", "itemId": "commentary", "delta": "I built the browser.",
                    }}
                if count == 2:
                    return {"method": "item/started", "params": {
                        "threadId": "thread-1", "turnId": "turn-1",
                        "item": {"id": "final", "type": "agentMessage", "phase": "final_answer"},
                    }}
                if count == 3:
                    return {"method": "item/agentMessage/delta", "params": {
                        "threadId": "thread-1", "turnId": "turn-1", "itemId": "final", "delta": "The project is ready.",
                    }}
                return {"method": "turn/completed", "params": {
                    "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"},
                }}

        adapter = CodexAppServerAdapter(sys.executable, rpc_factory=PhasedMessageRpc)
        async def callback(**changes):
            return False

        result = await adapter.run({"id": "task", "project": "/work"}, {"id": "child"}, "Make it", callback, callback)
        self.assertEqual(result["result"], "The project is ready.")

    async def test_unknown_message_phases_preserve_item_boundaries(self):
        class UnphasedMessageRpc(FakeRpc):
            async def next_notification(self):
                count = getattr(self, "notification_count", 0)
                self.notification_count = count + 1
                if count == 0:
                    return {"method": "item/started", "params": {
                        "threadId": "thread-1", "turnId": "turn-1",
                        "item": {"id": "first", "type": "agentMessage", "phase": None},
                    }}
                if count == 1:
                    return {"method": "item/agentMessage/delta", "params": {
                        "threadId": "thread-1", "turnId": "turn-1", "itemId": "first", "delta": "First message.",
                    }}
                if count == 2:
                    return {"method": "item/started", "params": {
                        "threadId": "thread-1", "turnId": "turn-1",
                        "item": {"id": "second", "type": "agentMessage", "phase": None},
                    }}
                if count == 3:
                    return {"method": "item/agentMessage/delta", "params": {
                        "threadId": "thread-1", "turnId": "turn-1", "itemId": "second", "delta": "Second message.",
                    }}
                return {"method": "turn/completed", "params": {
                    "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"},
                }}

        adapter = CodexAppServerAdapter(sys.executable, rpc_factory=UnphasedMessageRpc)
        async def callback(**changes):
            return False

        result = await adapter.run({"id": "task", "project": "/work"}, {"id": "child"}, "Make it", callback, callback)
        self.assertEqual(result["result"], "First message.\n\nSecond message.")


class FakeOfflineRuntime:
    project_path = "/project"

    def __init__(self):
        self.started = None
        self.spawned = None
        self.stopped = False

    async def start(self, project=None):
        self.started = project

    async def create_process(self, argv, **kwargs):
        raise AssertionError("FakeRpc must use only the isolated process factory")

    async def spawn(self, argv, **kwargs):
        self.spawned = (argv, kwargs)
        return {"returncode": 0, "stdout": '{"type":"thread.started","thread_id":"offline-thread"}\n'
                                                 '{"type":"item.completed","item":{"type":"agent_message","text":"Offline done"}}\n',
                "stderr": ""}

    async def stop(self):
        self.stopped = True


class OfflineAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_isolated_codex_uses_app_server_local_provider_and_real_ids(self):
        runtime = FakeOfflineRuntime()
        adapter = OfflineCodexAdapter(runtime, "qwen-local", rpc_factory=FakeRpc)
        async def callback(**changes):
            return False
        task = {"id": "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5", "project": "/host/project"}
        result = await adapter.run(task, {"id": "child"}, "Fix it", callback, callback)
        rpc = FakeRpc.instance
        self.assertEqual(runtime.started, "/host/project")
        self.assertEqual(rpc.cwd, "/project")
        self.assertEqual(rpc.kwargs["process_factory"], runtime.create_process)
        self.assertIn("app-server", rpc.argv)
        self.assertIn("http://127.0.0.1:11434/v1", str(rpc.argv))
        self.assertNotIn("bypass", str(rpc.argv))
        self.assertEqual(result["provider_session_id"], "session-1")
        self.assertEqual(result["turn_id"], "turn-1")

    async def test_cancel_interrupts_codex_and_closes_only_its_process(self):
        runtime = FakeOfflineRuntime()
        adapter = OfflineCodexAdapter(runtime, "qwen-local", rpc_factory=FakeRpc)
        coder = CodexAppServerAdapter(sys.executable, rpc_factory=FakeRpc)
        coder.rpc, coder.thread_id, coder.turn_id = FakeRpc([], "/project"), "thread-1", "turn-1"
        adapter.adapter = coder
        await adapter.cancel()
        self.assertIn(("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"}), coder.rpc.calls)
        self.assertTrue(coder.rpc.closed)
        self.assertFalse(runtime.stopped)


class FakeClaudeSdk:
    class PermissionResultAllow:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class PermissionResultDeny:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class TextBlock:
        def __init__(self, text):
            self.text = text

    class AssistantMessage:
        def __init__(self):
            self.session_id = "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5"
            self.uuid = "claude-turn"
            self.message_id = "message-1"
            self.content = [FakeClaudeSdk.TextBlock("Claude done")]

    class ResultMessage:
        def __init__(self):
            self.session_id = "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5"
            self.uuid = "result-1"
            self.result = None
            self.is_error = False


class FakeClaudeClient:
    instance = None

    def __init__(self, options):
        self.options = options
        self.disconnected = False
        self.permission = None
        FakeClaudeClient.instance = self

    async def connect(self):
        self.config_existed = Path(self.options.env["CLAUDE_CONFIG_DIR"]).is_dir()

    async def query(self, instructions, session_id):
        self.instructions, self.session_id = instructions, session_id
        self.permission = await self.options.can_use_tool("Bash", {"command": "test"}, SimpleNamespace(tool_use_id="tool-1"))

    async def receive_response(self):
        yield FakeClaudeSdk.AssistantMessage()
        yield FakeClaudeSdk.ResultMessage()

    async def disconnect(self):
        self.disconnected = True

    async def interrupt(self):
        return None


class ClaudeAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_uses_voice_api_key_task_uuid_and_default_permissions(self):
        adapter = ClaudeSdkAdapter("sk-test", model="claude-test", client_factory=FakeClaudeClient, sdk_module=FakeClaudeSdk)

        async def progress(**changes):
            return None

        async def approval(**request):
            self.assertEqual(request["provider_request_id"], "tool-1")
            return False

        task = {"id": "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5", "project": "/work"}
        result = await adapter.run(task, {"id": "child"}, "Fix navigation", approval, progress)
        options = FakeClaudeClient.instance.options
        self.assertEqual(options.session_id, task["id"])
        self.assertEqual(options.permission_mode, "default")
        self.assertEqual(options.env["ANTHROPIC_API_KEY"], "sk-test")
        self.assertEqual(options.env["CLAUDE_CODE_OAUTH_TOKEN"], "")
        self.assertEqual(options.setting_sources, [])
        self.assertTrue(options.strict_mcp_config)
        self.assertTrue(FakeClaudeClient.instance.config_existed)
        self.assertTrue(FakeClaudeClient.instance.disconnected)
        self.assertIsInstance(FakeClaudeClient.instance.permission, FakeClaudeSdk.PermissionResultDeny)
        self.assertEqual(result["result"], "Claude done")
        self.assertEqual(result["turn_id"], "result-1")

    async def test_terminal_result_does_not_duplicate_streamed_assistant_text(self):
        class DuplicateTerminalClient(FakeClaudeClient):
            async def receive_response(self):
                yield FakeClaudeSdk.AssistantMessage()
                terminal = FakeClaudeSdk.ResultMessage()
                terminal.result = "Claude done"
                yield terminal

        adapter = ClaudeSdkAdapter("test", client_factory=DuplicateTerminalClient, sdk_module=FakeClaudeSdk)

        async def callback(**changes):
            return False

        result = await adapter.run({"id": "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5", "project": "/work"}, {},
                                   "Reply once", callback, callback)
        self.assertEqual(result["result"], "Claude done")


class ExecutionRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_mode_pins_both_coders_to_selected_endpoint(self):
        settings = SimpleNamespace(value={"server_kind": "lmstudio", "server_url": "http://127.0.0.1:1234/v1", "execution_model": "local-coder"})
        manager = ExecutionManager(None, None, settings=settings, claude_sdk_module=FakeClaudeSdk)
        task = {"mode": "server"}
        codex = await manager._adapter(task, "codex")
        claude = await manager._adapter(task, "claude")
        self.assertEqual(codex.base_url, "http://127.0.0.1:1234/v1")
        self.assertEqual(claude.base_url, "http://127.0.0.1:1234")
        self.assertEqual((codex.model, claude.model), ("local-coder", "local-coder"))
        self.assertEqual(claude.api_key, "local-server")

    async def test_offline_claude_never_uses_host_adapter(self):
        runtime = FakeOfflineRuntime()
        manager = ExecutionManager(None, None, settings=SimpleNamespace(value={"execution_model": "local-coder"}),
                                   adapters={"claude": object()}, offline_runtime_factory=lambda **kw: runtime)
        adapter = await manager._adapter({"mode": "offline", "project": "/host/project"}, "claude")
        self.assertIsInstance(adapter, OfflineClaudeAdapter)
        self.assertIs(adapter.runtime, runtime)

    async def test_claude_rejects_stream_without_final_result(self):
        class TruncatedClient(FakeClaudeClient):
            async def receive_response(self):
                yield FakeClaudeSdk.AssistantMessage()
        adapter = ClaudeSdkAdapter("test", client_factory=TruncatedClient, sdk_module=FakeClaudeSdk)
        async def callback(**changes):
            return False
        with self.assertRaisesRegex(VoiceError, "final result"):
            await adapter.run({"id": "d8e6ef43-5d27-47df-b9f4-4d21c5ad13c5", "project": "/work"}, {}, "Fix it", callback, callback)

    async def test_json_rpc_eof_fails_pending_request_instead_of_hanging(self):
        import sys
        rpc = JsonRpcProcess((sys.executable, "-c", "import sys;sys.stdin.readline()"), None)
        await rpc.start()
        try:
            with self.assertRaisesRegex(VoiceError, "stopped"):
                await asyncio.wait_for(rpc.request("initialize", {}), 3)
        finally:
            await rpc.close()


class OfflineProcessRpcTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_stream_uses_worker_owned_handle_and_kills_process(self):
        import sys
        from unittest.mock import patch
        from maslow_voice import offline_worker as worker
        from maslow_voice.offline import RemoteProcess
        original = worker.launch
        async def launch(argv, **kwargs):
            kwargs["cwd"] = None
            return await original(argv, **kwargs)
        class Runtime:
            async def request(self, method, params=None, **kwargs):
                return await worker.process_rpc(method, params)
        with patch.object(worker, "launch", launch):
            result = await worker.process_rpc("process_start", {"argv": [sys.executable, "-u", "-c", "import sys,time;print(sys.stdin.readline().strip());time.sleep(30)"], "cwd": "/project"})
        remote = RemoteProcess(Runtime(), result["handle"])
        try:
            remote.write(b"permission denied\n")
            await remote.drain()
            self.assertEqual(await remote.readline(), b"permission denied\n")
            with self.assertRaises(ValueError):
                await worker.process_rpc("process_stop", {"handle": "foreign"})
        finally:
            remote.terminate()
            self.assertNotEqual(await remote.wait(), 0)
        self.assertNotIn(result["handle"], worker.PROCESSES)

    async def test_worker_rejects_host_paths_and_reserved_environment(self):
        from maslow_voice import offline_worker as worker
        for params in ({"argv": ["codex"], "cwd": "/host/project"},
                       {"argv": ["codex"], "cwd": "/project/../host"},
                       {"argv": ["codex"], "env": {"HOME": "/host/home"}}):
            with self.assertRaises(ValueError):
                await worker.process_rpc("process_start", params)


if __name__ == "__main__":
    unittest.main()
