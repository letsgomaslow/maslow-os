"""Bounded coding and desktop execution owned by the local Voice daemon.

The conversational provider never imports this module and never receives a process
handle.  Hermes reaches it through the daemon's authenticated Unix socket using the
immutable Voice task UUID as its session identity.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .errors import VoiceError


ACTIVE_CHILD_STATES = {"queued", "running", "awaiting_approval", "stopping"}
CODER_NAMES = {"auto", "codex", "claude"}
APPLICATION_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._+-]{0,79}$")
DESKTOP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,159}\.desktop$")

# These names resolve only to fixed, packaged helpers. Deployments may replace or
# extend the mapping, but model supplied text is never interpreted as an argv.
DEFAULT_APPLICATIONS = {
    "browser": ("omarchy-launch-browser",),
    "files": ("omarchy-launch-nautilus",),
    "hub": ("omarchy-launch-hub",),
    "terminal": ("omarchy-launch-terminal",),
}


def _text(value, field, maximum=24000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise VoiceError("INVALID_EXECUTION_REQUEST", f"The {field} is missing or too long.")
    return value.strip()


def _task_uuid(task):
    try:
        identity = str(uuid.UUID(task["id"]))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise VoiceError("INVALID_TASK_CONTEXT", "The execution request has no valid task identity.") from None
    if task.get("session_id") not in {None, identity}:
        raise VoiceError("IMMUTABLE_TASK", "The execution request does not match its Voice task session.")
    return identity


def validate_url(value):
    value = _text(value, "website address", 4096)
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
        parsed.port
        if any(ord(character) < 32 or character.isspace() for character in value):
            raise ValueError()
    except (TypeError, ValueError):
        raise VoiceError("INVALID_WEBSITE", "Only a complete HTTP or HTTPS website address can be opened.") from None
    return value


def _safe_result(value, maximum=200000):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, default=str)
    return value[:maximum]


async def _default_process(argv, *, cwd=None, env=None):
    return await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=2 * 1024 * 1024,
    )


class DesktopLauncher:
    """Launch fixed desktop helpers or explicitly allowlisted desktop IDs."""

    def __init__(self, applications=None, process_factory=None, browser=("omarchy-launch-browser",)):
        self.applications = dict(DEFAULT_APPLICATIONS if applications is None else applications)
        self.process_factory = process_factory or _default_process
        self.browser = tuple(browser) if browser else None

    def _application_argv(self, requested):
        requested = _text(requested, "application", 80)
        if not APPLICATION_NAME.fullmatch(requested):
            raise VoiceError("APPLICATION_NOT_ALLOWED", "That application is not available to Voice.")
        entry = self.applications.get(requested.casefold())
        if isinstance(entry, str):
            if not DESKTOP_ID.fullmatch(entry):
                raise VoiceError("APPLICATION_NOT_ALLOWED", "That application entry is not a valid desktop ID.")
            return ("gtk-launch", entry.removesuffix(".desktop"))
        if not isinstance(entry, (list, tuple)) or not entry or not all(isinstance(part, str) and part for part in entry):
            raise VoiceError("APPLICATION_NOT_ALLOWED", "That application is not in the Voice allowlist.")
        return tuple(entry)

    async def _launch(self, argv):
        binary = shutil.which(argv[0])
        if not binary:
            raise VoiceError("APPLICATION_UNAVAILABLE", "The selected desktop application is not installed.")
        process = await self.process_factory((binary, *argv[1:]), cwd=None, env=None)
        try:
            _output, error = await asyncio.wait_for(process.communicate(), 15)
        except TimeoutError:
            # GUI helpers may remain attached after the application is visible. A live
            # process is a successful launch request; the caller does not kill the app.
            return {"status": "opened"}
        if process.returncode:
            raise VoiceError("APPLICATION_LAUNCH_FAILED", "The desktop could not open the requested application.")
        return {"status": "opened", "detail": error.decode(errors="replace")[:1000] if error else ""}

    async def open_application(self, application):
        return await self._launch(self._application_argv(application))

    async def open_url(self, url):
        url = validate_url(url)
        if not self.browser:
            raise VoiceError("BROWSER_UNAVAILABLE", "No approved desktop browser helper is configured.")
        return await self._launch((*self.browser, url))


class JsonRpcProcess:
    """Small JSONL JSON-RPC peer for one Codex app-server child."""

    def __init__(self, argv, cwd, *, process_factory=None, environment=None, server_request=None):
        self.argv, self.cwd = tuple(argv), cwd
        self.process_factory = process_factory or _default_process
        self.environment, self.server_request = environment, server_request
        self.process = None
        self.reader = None
        self.pending = {}
        self.notifications = asyncio.Queue()
        self.sequence = 0
        self.closed = False
        self.server_tasks = set()

    async def start(self):
        self.process = await self.process_factory(self.argv, cwd=self.cwd, env=self.environment)
        self.reader = asyncio.create_task(self._read())

    async def _write(self, payload):
        if not self.process or not self.process.stdin or self.process.returncode is not None:
            raise VoiceError("CODEX_DISCONNECTED", "Codex stopped before the task completed.")
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False).encode() + b"\n")
        await self.process.stdin.drain()

    async def request(self, method, params=None):
        self.sequence += 1
        identity = self.sequence
        future = asyncio.get_running_loop().create_future()
        self.pending[identity] = future
        payload = {"method": method, "id": identity}
        if params is not None:
            payload["params"] = params
        await self._write(payload)
        try:
            return await future
        finally:
            self.pending.pop(identity, None)

    async def notify(self, method, params=None):
        payload = {"method": method}
        if params is not None:
            payload["params"] = params
        await self._write(payload)

    async def _respond_to_server(self, message):
        try:
            if not self.server_request:
                raise VoiceError("APPROVAL_UNAVAILABLE", "No reviewer is attached to this coding task.")
            result = await self.server_request(message["method"], message.get("params") or {}, message["id"])
            await self._write({"id": message["id"], "result": result})
        except Exception:
            await self._write({"id": message.get("id"), "error": {"code": -32000, "message": "The request was not approved."}})

    async def _read(self):
        try:
            while self.process and self.process.stdout:
                raw = await self.process.stdout.readline()
                if not raw:
                    break
                if len(raw) > 2 * 1024 * 1024:
                    raise VoiceError("CODEX_PROTOCOL_ERROR", "Codex returned an oversized protocol message.")
                try:
                    message = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise VoiceError("CODEX_PROTOCOL_ERROR", "Codex returned an unreadable protocol message.") from None
                if "id" in message and ("result" in message or "error" in message):
                    future = self.pending.get(message["id"])
                    if future and not future.done():
                        if "error" in message:
                            future.set_exception(VoiceError("CODEX_REQUEST_FAILED", "Codex could not complete a protocol request."))
                        else:
                            future.set_result(message.get("result"))
                elif "id" in message and "method" in message:
                    handler = asyncio.create_task(self._respond_to_server(message))
                    self.server_tasks.add(handler)
                    handler.add_done_callback(self.server_tasks.discard)
                elif "method" in message:
                    await self.notifications.put(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(exc if isinstance(exc, VoiceError) else VoiceError("CODEX_DISCONNECTED", "Codex stopped before the task completed."))
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(VoiceError("CODEX_DISCONNECTED", "Codex stopped before the task completed."))
            await self.notifications.put(None)

    async def next_notification(self):
        item = await self.notifications.get()
        if item is None:
            raise VoiceError("CODEX_DISCONNECTED", "Codex stopped before the task completed.")
        return item

    async def close(self):
        if self.closed:
            return
        self.closed = True
        for handler in self.server_tasks:
            handler.cancel()
        await asyncio.gather(*self.server_tasks, return_exceptions=True)
        if self.process and (self.process.returncode is None or hasattr(self.process, "handle")):
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.reader:
            self.reader.cancel()
            await asyncio.gather(self.reader, return_exceptions=True)


class CodexAppServerAdapter:
    """Run one Codex thread through its versioned app-server protocol."""

    def __init__(self, binary=None, *, rpc_factory=JsonRpcProcess, process_factory=None, environment=None, model=None, base_url=None, isolated=False, api_key=None):
        self.binary = binary or shutil.which("codex")
        self.rpc_factory, self.process_factory = rpc_factory, process_factory
        self.environment = environment
        self.model, self.base_url, self.isolated = model, base_url, isolated
        self.api_key = api_key
        self.rpc = None
        self.thread_id = None
        self.turn_id = None
        self.cancel_requested = False

    def ready(self):
        return bool(self.binary and (self.isolated or (Path(self.binary).is_file() and os.access(self.binary, os.X_OK))))

    async def run(self, task, child, instructions, approval, progress):
        if self.cancel_requested:
            raise VoiceError("EXECUTION_INTERRUPTED", "Codex was stopped before it started.")
        if not self.ready():
            raise VoiceError("CODEX_MISSING", "Install or repair Codex before delegating coding work to it.")

        async def server_request(method, params, request_id):
            if method not in {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}:
                raise VoiceError("CODEX_REQUEST_UNSUPPORTED", "Codex requested an interaction this bridge cannot safely provide.")
            kind = "command" if "commandExecution" in method else "file_change"
            detail = params.get("command") or params.get("reason") or "Codex requests permission to continue."
            allowed = await approval(
                provider_request_id=str(request_id),
                tool_name=kind,
                message=str(detail)[:4000],
                provider_context={key: params.get(key) for key in ("threadId", "turnId", "itemId", "approvalId")},
            )
            return {"decision": "accept" if allowed else "decline"}

        argv = [self.binary, "app-server", "--listen", "stdio://"]
        if self.base_url:
            # A fixed explicit provider prevents configured native-cloud routing.
            provider = 'name="Maslow",base_url=' + json.dumps(self.base_url) + ',wire_api="responses",requires_openai_auth=false'
            if self.api_key:
                provider += ',env_key="MASLOW_EXECUTION_API_KEY"'
                self.environment = dict(self.environment if self.environment is not None else os.environ, MASLOW_EXECUTION_API_KEY=self.api_key)
            argv += ["-c", 'model_provider="maslow"', "-c", "model_providers.maslow={" + provider + "}",
                     "-c", 'model=' + json.dumps(self.model)]
        self.rpc = self.rpc_factory(
            argv,
            task["project"],
            process_factory=self.process_factory,
            environment=self.environment,
            server_request=server_request,
        )
        await self.rpc.start()
        if self.cancel_requested:
            await self.rpc.close()
            raise VoiceError("EXECUTION_INTERRUPTED", "Codex was stopped during startup.")
        try:
            await self.rpc.request("initialize", {"clientInfo": {"name": "maslow-voice", "title": "Maslow Voice", "version": "0.1.0"},
                                                  "capabilities": {"experimentalApi": False, "requestAttestation": False}})
            await self.rpc.notify("initialized")
            started = await self.rpc.request("thread/start", {
                "cwd": task["project"], "approvalPolicy": "untrusted",
                "approvalsReviewer": "user", "sandbox": "workspace-write", "ephemeral": False,
                "threadSource": "appServer",
                **({"model": self.model} if self.model else {}),
                **({"modelProvider": "maslow"} if self.base_url else {}),
            })
            thread = (started or {}).get("thread") or {}
            self.thread_id = _text(thread.get("id"), "Codex thread identity", 200)
            provider_session = _text(thread.get("sessionId"), "Codex session identity", 200)
            await progress(status="running", provider_session_id=provider_session, thread_id=self.thread_id)
            turn = await self.rpc.request("turn/start", {
                "threadId": self.thread_id,
                "input": [{"type": "text", "text": instructions, "text_elements": []}],
                "approvalPolicy": "untrusted", "approvalsReviewer": "user",
            })
            self.turn_id = _text(((turn or {}).get("turn") or {}).get("id"), "Codex turn identity", 200)
            await progress(status="running", turn_id=self.turn_id)
            output = []
            while True:
                event = await self.rpc.next_notification()
                params = event.get("params") or {}
                if event.get("method") == "item/agentMessage/delta" and params.get("threadId") == self.thread_id and params.get("turnId") == self.turn_id:
                    output.append(str(params.get("delta", "")))
                elif event.get("method") == "turn/completed" and params.get("threadId") == self.thread_id:
                    completed = params.get("turn") or {}
                    if completed.get("id") != self.turn_id:
                        continue
                    status = completed.get("status")
                    if status == "completed":
                        return {"status": "completed", "result": "".join(output), "provider_session_id": provider_session,
                                "thread_id": self.thread_id, "turn_id": self.turn_id}
                    if status == "interrupted":
                        raise VoiceError("EXECUTION_INTERRUPTED", "Codex stopped before it completed the task.")
                    raise VoiceError("EXECUTION_FAILED", "Codex could not complete the task. Review its task for details.")
        finally:
            await self.rpc.close()

    async def cancel(self):
        self.cancel_requested = True
        if self.rpc:
            try:
                if self.thread_id and self.turn_id:
                    await asyncio.wait_for(self.rpc.request("turn/interrupt", {"threadId": self.thread_id, "turnId": self.turn_id}), 5)
            finally:
                await self.rpc.close()


class ClaudeSdkAdapter:
    """Use ClaudeAgentSDK with a Voice-owned API key and exact task UUID."""

    def __init__(self, api_key, *, model=None, client_factory=None, sdk_module=None, safe_environment=None, base_url=None):
        self.api_key, self.model = api_key, model or None
        self.client_factory, self.sdk = client_factory, sdk_module
        self.safe_environment = dict(safe_environment or {})
        self.base_url = base_url
        self.client = None

    def _load(self):
        if self.sdk is not None:
            return self.sdk
        try:
            import claude_agent_sdk
        except ImportError:
            raise VoiceError("CLAUDE_SDK_MISSING", "Install the Claude Agent SDK before delegating coding work to Claude.") from None
        self.sdk = claude_agent_sdk
        return self.sdk

    def ready(self):
        try:
            self._load()
        except VoiceError:
            return False
        return bool(self.api_key)

    async def run(self, task, child, instructions, approval, progress):
        sdk = self._load()
        if not self.api_key:
            raise VoiceError("CLAUDE_API_KEY_REQUIRED", "Connect a Claude API key in Hub before delegating coding work to Claude.")

        async def can_use_tool(tool_name, tool_input, context):
            provider_id = getattr(context, "tool_use_id", None) or str(uuid.uuid4())
            allowed = await approval(provider_request_id=provider_id, tool_name=tool_name,
                                     message=f"Claude requests permission to use {tool_name}: " + _safe_result(tool_input, 3500),
                                     provider_context={"tool_use_id": provider_id})
            if allowed:
                return sdk.PermissionResultAllow(updated_input=tool_input)
            return sdk.PermissionResultDeny(message="The user denied this one tool call.", interrupt=False)

        # A private empty config directory prevents Claude subscription credentials from
        # being read. The integration supplies only the API key saved by Voice.
        with tempfile.TemporaryDirectory(prefix="maslow-voice-claude-") as config_dir:
            environment = dict(self.safe_environment)
            environment.update(ANTHROPIC_API_KEY=self.api_key, CLAUDE_CONFIG_DIR=config_dir,
                               CLAUDE_CODE_OAUTH_TOKEN="", ANTHROPIC_AUTH_TOKEN="",
                               CLAUDE_CODE_USE_BEDROCK="0", CLAUDE_CODE_USE_VERTEX="0", CLAUDE_CODE_USE_FOUNDRY="0",
                               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
            environment["ANTHROPIC_BASE_URL"] = self.base_url or "https://api.anthropic.com"
            if self.base_url:
                environment.update(ANTHROPIC_API_KEY="", ANTHROPIC_AUTH_TOKEN=self.api_key)
            options = sdk.ClaudeAgentOptions(
                cwd=task["project"], session_id=task["id"], model=self.model,
                tools={"type": "preset", "preset": "claude_code"}, permission_mode="default",
                can_use_tool=can_use_tool, env=environment, setting_sources=[], strict_mcp_config=True,
            )
            factory = self.client_factory or sdk.ClaudeSDKClient
            self.client = factory(options=options)
            await self.client.connect()
            try:
                await progress(status="running", provider_session_id=task["id"], thread_id=task["id"])
                await self.client.query(instructions, session_id=task["id"])
                text, session_id, turn_id, completed = [], task["id"], None, False
                async for message in self.client.receive_response():
                    if isinstance(message, sdk.AssistantMessage):
                        session_id = message.session_id or session_id
                        turn_id = message.uuid or message.message_id or turn_id
                        for block in message.content:
                            if isinstance(block, sdk.TextBlock):
                                text.append(block.text)
                    elif isinstance(message, sdk.ResultMessage):
                        completed = True
                        session_id = message.session_id or session_id
                        turn_id = message.uuid or turn_id
                        if message.result:
                            text.append(message.result)
                        if message.is_error:
                            raise VoiceError("EXECUTION_FAILED", "Claude could not complete the task. Review its task for details.")
                if not completed:
                    raise VoiceError("CLAUDE_DISCONNECTED", "Claude stopped before returning a final result.")
                return {"status": "completed", "result": "\n".join(part for part in text if part),
                        "provider_session_id": session_id, "thread_id": session_id, "turn_id": turn_id}
            finally:
                await self.client.disconnect()

    async def cancel(self):
        if self.client:
            try:
                await self.client.interrupt()
            finally:
                await self.client.disconnect()


class OfflineCodexAdapter:
    """The same structured Codex protocol, wholly inside the private runtime."""

    def __init__(self, runtime, model, *, rpc_factory=JsonRpcProcess):
        self.runtime, self.model, self.rpc_factory = runtime, model, rpc_factory
        self.adapter = None

    async def run(self, task, child, instructions, approval, progress):
        if not self.runtime:
            raise VoiceError("OFFLINE_ISOLATION_REQUIRED", "The offline coding sandbox is unavailable; no process was started.")
        if not self.model:
            raise VoiceError("MODEL_REQUIRED", "Choose a downloaded execution model before delegating offline coding work.")
        await self.runtime.start(project=task["project"])
        self.adapter = CodexAppServerAdapter("codex", process_factory=self.runtime.create_process,
            rpc_factory=self.rpc_factory, model=self.model, base_url="http://127.0.0.1:11434/v1", isolated=True,
            environment={"CODEX_HOME": "/home/voice/.codex"})
        return await self.adapter.run(dict(task, project=self.runtime.project_path), child, instructions, approval, progress)

    async def cancel(self):
        if self.adapter:
            await self.adapter.cancel()


class OfflineClaudeAdapter:
    """Run the packaged SDK in the namespace and relay typed permission replies."""

    def __init__(self, runtime, model):
        self.runtime, self.model, self.process = runtime, model, None

    async def run(self, task, child, instructions, approval, progress):
        if not self.runtime or not self.model:
            raise VoiceError("OFFLINE_ISOLATION_REQUIRED", "Choose a downloaded model and start the offline workspace first.")
        await self.runtime.start(project=task["project"])
        self.process = await self.runtime.create_process(
            ("/usr/lib/maslow-voice/venv/bin/python3", "/usr/lib/maslow-voice/maslow_voice/execution_worker.py"),
            cwd=self.runtime.project_path, env={})
        async def send(payload):
            self.process.stdin.write(json.dumps(payload).encode() + b"\n")
            await self.process.stdin.drain()
        try:
            await send({"task": dict(task, project=self.runtime.project_path), "child": child,
                        "instructions": instructions, "model": self.model})
            while raw := await self.process.stdout.readline():
                event = json.loads(raw)
                if event.get("type") == "progress":
                    await progress(**event["value"])
                elif event.get("type") == "approval":
                    allowed = await approval(**event["value"])
                    await send({"type": "approval", "id": event["id"], "allowed": allowed is True})
                elif event.get("type") == "result":
                    return event["value"]
                else:
                    raise VoiceError("EXECUTION_FAILED", "The isolated Claude task could not complete.")
            raise VoiceError("CLAUDE_DISCONNECTED", "Claude stopped before returning a final result.")
        finally:
            await self.cancel()

    async def cancel(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()


class ExecutionManager:
    """Persist and supervise child executions for authoritative Voice tasks."""

    def __init__(self, store, publish, *, settings=None, credentials=None, adapters=None, offline_runtime_factory=None,
                 codex_binary=None, desktop_launcher=None, application_allowlist=None, process_factory=None,
                 claude_client_factory=None, claude_sdk_module=None, safe_environment=None):
        self.store, self.publish = store, publish
        self.settings, self.credentials = settings, credentials
        self.adapters = dict(adapters or {})
        self.offline_runtime_factory = offline_runtime_factory
        self.codex_binary, self.process_factory = codex_binary, process_factory
        self.claude_client_factory, self.claude_sdk_module = claude_client_factory, claude_sdk_module
        self.safe_environment = dict(safe_environment or {})
        self.desktop = desktop_launcher or DesktopLauncher(application_allowlist, process_factory=process_factory)
        self.active, self.pending_approvals, self.cancelled = {}, {}, set()
        self.approval_locks = {}

    def _authoritative(self, supplied):
        identity = _task_uuid(supplied)
        task = self.store.get(identity)
        for field in ("id", "request_id", "project", "mode", "source"):
            if supplied.get(field) != task.get(field):
                raise VoiceError("IMMUTABLE_TASK", "The execution request does not match the saved Voice task.")
        return task

    async def _published_update(self, task_id, **changes):
        result = self.store.update(task_id, **changes)
        await self.publish()
        return result

    async def _child_update(self, task_id, child_id, **changes):
        task = self.store.get(task_id)
        children, found = [], False
        for child in task.get("children", []):
            if child.get("id") == child_id:
                child = dict(child, **changes)
                found = True
            children.append(child)
        if not found:
            raise VoiceError("CHILD_NOT_FOUND", "That coding task is no longer attached to this Voice task.")
        await self._published_update(task_id, children=children)
        return next(child for child in children if child["id"] == child_id)

    async def _new_child(self, task, tool, instructions):
        child = {"id": str(uuid.uuid4()), "kind": "coding", "tool": tool, "status": "queued", "instructions": instructions,
                 "provider_session_id": None, "thread_id": None, "turn_id": None, "result": "", "error": None, "approval": None}
        await self._published_update(task["id"], children=[*task.get("children", []), child])
        return child

    async def _approval(self, task_id, child_id, **request):
        async with self.approval_locks.setdefault(task_id, asyncio.Lock()):
            if (task_id, child_id) in self.cancelled:
                return False
            return await self._approval_one(task_id, child_id, **request)

    async def _approval_one(self, task_id, child_id, **request):
        public_id = str(uuid.uuid4())
        approval = {"owner": "child", "request_id": public_id, "child_id": child_id,
                    "tool_name": request.get("tool_name", "coding"), "message": request.get("message", "Approval required."),
                    "provider_request_id": request.get("provider_request_id")}
        future = asyncio.get_running_loop().create_future()
        self.pending_approvals[(task_id, child_id, public_id)] = future
        await self._child_update(task_id, child_id, status="awaiting_approval", approval=approval)
        await self._published_update(task_id, approval=approval)
        try:
            return await future
        finally:
            self.pending_approvals.pop((task_id, child_id, public_id), None)
            current = self.store.get(task_id)
            if (current.get("approval") or {}).get("request_id") == public_id:
                await self._published_update(task_id, approval=None)
            await self._child_update(task_id, child_id, status="running", approval=None)

    async def _adapter(self, task, tool):
        if task["mode"] == "offline":
            if not self.offline_runtime_factory:
                raise VoiceError("OFFLINE_ISOLATION_REQUIRED", "The offline coding sandbox is unavailable; no process was started.")
            runtime = await self._offline_runtime(task)
            model = (self.settings.value if self.settings else {}).get("execution_model") or (self.settings.value if self.settings else {}).get("model")
            return (OfflineClaudeAdapter if tool == "claude" else OfflineCodexAdapter)(runtime, model)
        config = self.settings.value if self.settings else {}
        model = config.get("execution_model") or config.get("model")
        base_url = None
        if task["mode"] == "server":
            from .config import validate_endpoint
            base_url = validate_endpoint(config.get("server_url", "")).removesuffix("/v1")
            if not model or config.get("server_kind") not in {"ollama", "lmstudio"}:
                raise VoiceError("MODEL_REQUIRED", "Choose an execution model on your supported server first.")
        if tool in self.adapters:
            adapter = self.adapters[tool]
            return adapter(task) if callable(adapter) else adapter
        if tool == "codex":
            token = await self.credentials.get("server_token") if base_url and self.credentials else None
            return CodexAppServerAdapter(self.codex_binary, process_factory=self.process_factory, environment=self.safe_environment or None,
                                         model=model if base_url else None, base_url=base_url + "/v1" if base_url else None, api_key=token)
        if not self.credentials and not base_url:
            raise VoiceError("CLAUDE_API_KEY_REQUIRED", "Connect a Claude API key in Hub before delegating coding work to Claude.")
        api_key = (await self.credentials.get("server_token") if self.credentials else None) or "local-server" if base_url else await self.credentials.get("anthropic")
        return ClaudeSdkAdapter(api_key, model=model, client_factory=self.claude_client_factory,
                                sdk_module=self.claude_sdk_module, safe_environment=self.safe_environment, base_url=base_url)

    async def _offline_runtime(self, task):
        runtime = self.offline_runtime_factory(project=task["project"])
        if inspect.isawaitable(runtime):
            runtime = await runtime
        return runtime

    async def readiness(self, task=None):
        mode = task.get("mode") if task else None
        codex = bool(self.codex_binary or shutil.which("codex"))
        try:
            __import__("claude_agent_sdk") if self.claude_sdk_module is None else self.claude_sdk_module
            claude_sdk = True
        except ImportError:
            claude_sdk = False
        claude_key = False
        if self.credentials and mode != "offline":
            try:
                claude_key = bool(await self.credentials.get("anthropic"))
            except VoiceError:
                pass
        config = self.settings.value if self.settings else {}
        configured_model = bool(config.get("execution_model") or config.get("model"))
        if mode == "offline":
            codex = bool(codex and self.offline_runtime_factory and configured_model)
            claude_ready = bool(claude_sdk and self.offline_runtime_factory and configured_model)
        elif mode == "server":
            supported = config.get("server_kind") in {"ollama", "lmstudio"} and configured_model
            codex, claude_ready = bool(codex and supported), bool(claude_sdk and supported)
        else:
            claude_ready = bool(claude_sdk and claude_key)
        return {"codex": {"ready": codex, "message": "Configured; connection is checked when starting." if codex else "Codex or its execution model is unavailable."},
                "claude": {"ready": claude_ready, "message": "Configured; connection is checked when starting." if claude_ready else "Claude SDK, credentials, or its execution model is unavailable."}}

    async def handle(self, supplied_task, operation, params=None):
        task = self._authoritative(supplied_task)
        params = params or {}
        if not isinstance(params, dict):
            raise VoiceError("INVALID_EXECUTION_REQUEST", "Execution parameters must be an object.")
        if operation == "readiness":
            return await self.readiness(task)
        if operation in {"coding", "delegate_coding"}:
            return await self._delegate(task, params)
        if operation == "open_application":
            application = _text(params.get("application"), "application", 80)
            if task["mode"] == "offline":
                if not self.offline_runtime_factory:
                    raise VoiceError("OFFLINE_ISOLATION_REQUIRED", "The offline desktop sandbox is unavailable; no application was opened.")
                runtime = await self._offline_runtime(task)
                await runtime.start(project=task["project"])
                if not hasattr(runtime, "open_application"):
                    raise VoiceError("OFFLINE_APPLICATION_UNAVAILABLE", "The offline workspace has no approved application launcher.")
                return await runtime.open_application(application)
            return await self.desktop.open_application(application)
        if operation == "open_website":
            url = validate_url(params.get("url"))
            if task["mode"] == "offline":
                if not self.offline_runtime_factory:
                    raise VoiceError("OFFLINE_ISOLATION_REQUIRED", "The offline browser sandbox is unavailable; no website was opened.")
                runtime = await self._offline_runtime(task)
                await runtime.start(project=task["project"])
                if not hasattr(runtime, "open_url"):
                    raise VoiceError("OFFLINE_BROWSER_UNAVAILABLE", "The fixed offline browser is unavailable.")
                return await runtime.open_url(url)
            return await self.desktop.open_url(url)
        if operation in {"approve", "deny"}:
            return await self._answer_approval(task, operation == "approve", params)
        if operation == "cancel":
            await self.cancel(task["id"])
            return {"status": "cancelled"}
        raise VoiceError("INVALID_EXECUTION_OPERATION", "That execution operation is not supported.")

    async def _delegate(self, task, params):
        instructions = _text(params.get("instructions"), "coding instructions")
        tool = params.get("tool", "auto")
        if tool not in CODER_NAMES:
            raise VoiceError("INVALID_CODER", "Choose Codex, Claude, or automatic coding delegation.")
        if tool == "auto":
            tool = task.get("preferred_coder", "codex")
            if tool not in {"codex", "claude"}:
                tool = "codex"
        child = await self._new_child(task, tool, instructions)
        key = (task["id"], child["id"])

        async def progress(**changes):
            await self._child_update(task["id"], child["id"], **changes)

        async def approval(**request):
            return await self._approval(task["id"], child["id"], **request)

        try:
            adapter = await self._adapter(task, tool)
            self.active[key] = adapter
            await progress(status="running")
            result = await adapter.run(task, child, instructions, approval, progress)
            if key in self.cancelled:
                raise VoiceError("EXECUTION_INTERRUPTED", "The coding task was stopped.")
            final = await self._child_update(task["id"], child["id"], status="completed", approval=None, error=None,
                                             result=_safe_result(result.get("result")),
                                             provider_session_id=result.get("provider_session_id"), thread_id=result.get("thread_id"),
                                             turn_id=result.get("turn_id"))
            return {"status": "completed", "child": final, "result": final["result"]}
        except asyncio.CancelledError:
            await self._child_update(task["id"], child["id"], status="cancelled", approval=None)
            raise
        except VoiceError as exc:
            if key not in self.cancelled:
                await self._child_update(task["id"], child["id"], status="failed", approval=None, error=exc.as_dict())
            raise
        except Exception:
            error = VoiceError("EXECUTOR_UNAVAILABLE", "The coding tool stopped unexpectedly. Review any partial changes before continuing.")
            if key not in self.cancelled:
                await self._child_update(task["id"], child["id"], status="failed", approval=None, error=error.as_dict())
            raise error from None
        finally:
            self.active.pop(key, None)
            self.cancelled.discard(key)

    async def _answer_approval(self, task, allow, params):
        approval_id = _text(params.get("approval_id"), "approval identity", 200)
        child_id = params.get("child_id") or (task.get("approval") or {}).get("child_id")
        key = (task["id"], child_id, approval_id)
        future = self.pending_approvals.get(key)
        if not future or future.done():
            raise VoiceError("APPROVAL_EXPIRED", "Refresh and review the current child approval before responding.")
        current = self.store.get(task["id"]).get("approval") or {}
        if current.get("owner") != "child" or current.get("request_id") != approval_id or current.get("child_id") != child_id:
            raise VoiceError("APPROVAL_EXPIRED", "Refresh and review the current child approval before responding.")
        future.set_result(bool(allow))
        return {"status": "approved" if allow else "denied", "child_id": child_id, "approval_id": approval_id}

    async def cancel(self, task_id):
        task = self.store.get(task_id)
        active = [(key, adapter) for key, adapter in self.active.items() if key[0] == task_id]
        self.cancelled.update(key for key, _adapter in active)
        for (identity, child_id, approval_id), future in list(self.pending_approvals.items()):
            if identity == task_id and not future.done():
                future.set_result(False)
        await asyncio.gather(*(adapter.cancel() for _key, adapter in active), return_exceptions=True)
        for (_identity, child_id), _adapter in active:
            try:
                await self._child_update(task_id, child_id, status="cancelled", approval=None)
            except VoiceError:
                pass
        if (task.get("approval") or {}).get("owner") == "child":
            await self._published_update(task_id, approval=None)
