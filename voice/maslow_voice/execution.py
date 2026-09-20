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
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .errors import VoiceError


ACTIVE_CHILD_STATES = {"queued", "running", "awaiting_approval", "stopping"}
CODER_NAMES = {"auto", "codex", "claude"}
MAX_ACTIVITY = 80
MAX_INSTRUCTION_OUTCOMES = 40
MAX_CODEX_OBSERVED_ITEMS = 160
MAX_CODEX_APPROVAL_CHANGES = 6
MAX_CODEX_APPROVAL_PATH = 160
MAX_CODEX_APPROVAL_DIFF = 180
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


def _codex_display_text(value, maximum, *, multiline=False):
    """Bound protocol-provided detail before it becomes a human approval prompt."""
    if not isinstance(value, str):
        return ""
    value = "".join(character if character >= " " or (multiline and character == "\n") else " " for character in value)
    if not multiline:
        value = " ".join(value.split())
    return value[:maximum]


def _codex_change_kind(change):
    kind = change.get("kind") if isinstance(change, dict) else None
    if not isinstance(kind, dict):
        return "change"
    change_type = kind.get("type")
    if change_type == "update":
        move_to = _codex_display_text(kind.get("move_path"), 120)
        return f"move to {move_to}" if move_to else "update"
    return change_type if change_type in {"add", "delete"} else "change"


def _codex_file_change_detail(item, reason):
    """Summarize the exact observed file-change item without widening approval."""
    lines = ["Codex requests permission to apply file changes."]
    valid_changes = 0
    changes = item.get("changes") if isinstance(item, dict) else None
    if isinstance(changes, list):
        for change in changes[:MAX_CODEX_APPROVAL_CHANGES]:
            if not isinstance(change, dict):
                continue
            raw_path = change.get("path")
            path = _codex_display_text(raw_path, MAX_CODEX_APPROVAL_PATH)
            if not path:
                continue
            path_notice = " … path preview truncated." if len(raw_path) > MAX_CODEX_APPROVAL_PATH else ""
            lines.append(f"- {_codex_change_kind(change)}: {path}{path_notice}")
            valid_changes += 1
            raw_diff = change.get("diff")
            diff = _codex_display_text(raw_diff, MAX_CODEX_APPROVAL_DIFF, multiline=True)
            if diff:
                lines.append("  Diff preview: " + diff.replace("\n", "\n  "))
                if len(raw_diff) > MAX_CODEX_APPROVAL_DIFF:
                    lines.append("  … diff preview truncated.")
        if len(changes) > MAX_CODEX_APPROVAL_CHANGES:
            lines.append(f"- … {len(changes) - MAX_CODEX_APPROVAL_CHANGES} additional file changes omitted from preview.")
    detail = "\n".join(lines)
    reason = _codex_display_text(reason, 600, multiline=True)
    if reason:
        detail += "\nReason: " + reason
    return detail[:4000] if valid_changes else ""


def _workspace_artifact(task, path):
    """Return a verified workspace-relative artifact, or None for unsafe paths."""
    if not isinstance(path, str) or not path or "\x00" in path:
        return None
    try:
        workspace = Path(task["project"]).resolve(strict=True)
        candidate = Path(path)
        candidate = candidate.resolve(strict=False) if candidate.is_absolute() else (workspace / candidate).resolve(strict=False)
        relative = candidate.relative_to(workspace)
    except (KeyError, OSError, RuntimeError, ValueError):
        return None
    if not relative.parts or relative == Path("."):
        return None
    return {"path": relative.as_posix(), "exists": candidate.exists(),
            "verification": "exists" if candidate.exists() else "missing"}


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
        self.steer_lock = asyncio.Lock()

    def ready(self):
        return bool(self.binary and (self.isolated or (Path(self.binary).is_file() and os.access(self.binary, os.X_OK))))

    async def run(self, task, child, instructions, approval, progress):
        if self.cancel_requested:
            raise VoiceError("EXECUTION_INTERRUPTED", "Codex was stopped before it started.")
        if not self.ready():
            raise VoiceError("CODEX_MISSING", "Install or repair Codex before delegating coding work to it.")

        observed_items, observed_item_events = {}, {}

        def item_identity(params, item_id=None):
            thread_id = params.get("threadId") if isinstance(params, dict) else None
            turn_id = params.get("turnId") if isinstance(params, dict) else None
            item_id = item_id if item_id is not None else params.get("itemId") if isinstance(params, dict) else None
            if not all(isinstance(value, str) and value for value in (thread_id, turn_id, item_id)):
                return None
            return thread_id, turn_id, item_id

        def remember_item(params, item):
            identity = item_identity(params, item.get("id") if isinstance(item, dict) else None)
            if not identity:
                return
            observed_items[identity] = item
            observed_item_events.setdefault(identity, asyncio.Event()).set()
            if len(observed_items) > MAX_CODEX_OBSERVED_ITEMS:
                removed = next(iter(observed_items))
                observed_items.pop(removed)
                observed_item_events.pop(removed, None)

        async def server_request(method, params, request_id):
            if method not in {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}:
                raise VoiceError("CODEX_REQUEST_UNSUPPORTED", "Codex requested an interaction this bridge cannot safely provide.")
            identity = item_identity(params)
            if not identity or identity[0] != self.thread_id or identity[1] != self.turn_id:
                raise VoiceError("CODEX_REQUEST_UNSUPPORTED", "Codex requested approval for a different task turn.")
            kind = "command" if "commandExecution" in method else "file_change"
            observed = observed_items.get(identity)
            if kind == "file_change":
                if observed is None:
                    ready = observed_item_events.get(identity)
                    created_waiter = ready is None
                    if created_waiter:
                        ready = asyncio.Event()
                        observed_item_events[identity] = ready
                    try:
                        await asyncio.wait_for(ready.wait(), 0.5)
                    except TimeoutError:
                        pass
                    finally:
                        if created_waiter and identity not in observed_items:
                            observed_item_events.pop(identity, None)
                    observed = observed_items.get(identity)
                if observed is None or observed.get("type") != "fileChange":
                    detail = "Codex requested a file change, but the exact file-change details were unavailable. The request was declined."
                    await progress(activity={"kind": "approval", "text": detail})
                    return {"decision": "decline"}
                detail = _codex_file_change_detail(observed, params.get("reason"))
                if not detail:
                    detail = "Codex requested a file change, but no valid file-change path was available for review. The request was declined."
                    await progress(activity={"kind": "approval", "text": detail})
                    return {"decision": "decline"}
            else:
                detail = (params.get("command")
                          or (observed or {}).get("command")
                          or params.get("reason")
                          or "Codex requests permission to run a command.")
                if isinstance(detail, str) and len(detail) > 4000:
                    await progress(activity={
                        "kind": "approval",
                        "text": "Codex requested a command whose full details exceed the 4,000-character review limit. "
                                "The request was declined without approval. Codex can split it into shorter commands for review.",
                    })
                    return {"decision": "decline"}
                detail = _codex_display_text(detail, 4000, multiline=True)
            await progress(activity={"kind": "approval", "text": str(detail)[:4000]})
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
            resume_thread_id = child.get("resume_thread_id")
            if resume_thread_id:
                started = await self.rpc.request("thread/resume", {
                    "threadId": _text(resume_thread_id, "Codex thread identity", 200),
                    "cwd": task["project"], "approvalPolicy": "untrusted", "approvalsReviewer": "user",
                    "sandbox": "workspace-write",
                    **({"model": self.model} if self.model else {}),
                    **({"modelProvider": "maslow"} if self.base_url else {}),
                })
            else:
                started = await self.rpc.request("thread/start", {
                    "cwd": task["project"], "approvalPolicy": "untrusted",
                    "approvalsReviewer": "user", "sandbox": "workspace-write", "ephemeral": False,
                    "threadSource": "appServer",
                    **({"model": self.model} if self.model else {}),
                    **({"modelProvider": "maslow"} if self.base_url else {}),
                })
            thread = (started or {}).get("thread") or {}
            self.thread_id = _text(thread.get("id"), "Codex thread identity", 200)
            if resume_thread_id and self.thread_id != resume_thread_id:
                raise VoiceError("CODEX_RESUME_FAILED", "Codex did not resume the saved task thread. No new task was started.")
            provider_session = _text(thread.get("sessionId"), "Codex session identity", 200)
            await progress(status="running", provider_session_id=provider_session, thread_id=self.thread_id,
                           activity={"kind": "thread", "text": "Resumed Codex thread." if resume_thread_id else "Started Codex thread."})
            turn = await self.rpc.request("turn/start", {
                "threadId": self.thread_id,
                "input": [{"type": "text", "text": instructions, "text_elements": []}],
                "approvalPolicy": "untrusted", "approvalsReviewer": "user",
            })
            self.turn_id = _text(((turn or {}).get("turn") or {}).get("id"), "Codex turn identity", 200)
            await progress(status="running", turn_id=self.turn_id, activity={"kind": "turn", "text": "Codex is working."})
            output, assistant_delta, artifact_paths = [], "", set()
            assistant_item_id = ""
            last_assistant_flush = time.monotonic()

            async def flush_assistant():
                nonlocal assistant_delta, last_assistant_flush
                if assistant_delta:
                    await progress(activity={"kind": "assistant", "text": assistant_delta,
                                             "stream_id": self.thread_id + ":" + self.turn_id + ":" + assistant_item_id})
                    assistant_delta = ""
                last_assistant_flush = time.monotonic()

            async def record_item(params, phase):
                item = params.get("item")
                if not isinstance(item, dict):
                    return
                remember_item(params, item)
                if item.get("type") == "commandExecution":
                    command = item.get("command")
                    if isinstance(command, str) and command:
                        status = item.get("status") if phase == "completed" else "running"
                        await progress(activity={"kind": "command", "text": (str(status) + ": " + command)[:4000]})
                elif item.get("type") == "fileChange":
                    changed = []
                    for change in item.get("changes") or []:
                        if isinstance(change, dict):
                            artifact = _workspace_artifact(task, change.get("path"))
                            if artifact:
                                artifact_paths.add(artifact["path"])
                                changed.append(artifact["path"])
                                await progress(artifact=artifact)
                    if changed:
                        await progress(activity={"kind": "file_change", "text": (phase.title() + ": " + ", ".join(changed))[:4000]})

            while True:
                try:
                    event = await asyncio.wait_for(self.rpc.next_notification(), 0.1)
                except TimeoutError:
                    await flush_assistant()
                    continue
                params = event.get("params") or {}
                if event.get("method") == "item/agentMessage/delta" and params.get("threadId") == self.thread_id and params.get("turnId") == self.turn_id:
                    item_id = str(params.get("itemId", ""))[:200]
                    if item_id != assistant_item_id:
                        await flush_assistant()
                        assistant_item_id = item_id
                    delta = str(params.get("delta", ""))[:4000]
                    if delta:
                        if output and output[-1][0] == item_id:
                            output[-1][1] += delta
                        else:
                            output.append([item_id, delta])
                        assistant_delta = (assistant_delta + delta)[:4000]
                        if len(assistant_delta) == 4000 or time.monotonic() - last_assistant_flush >= 0.1:
                            await flush_assistant()
                elif event.get("method") == "item/commandExecution/outputDelta" and params.get("threadId") == self.thread_id and params.get("turnId") == self.turn_id:
                    await flush_assistant()
                elif event.get("method") == "item/fileChange/patchUpdated" and params.get("threadId") == self.thread_id and params.get("turnId") == self.turn_id:
                    await flush_assistant()
                    changes = params.get("changes")
                    if isinstance(changes, list):
                        for change in changes[:40]:
                            if not isinstance(change, dict):
                                continue
                            artifact = _workspace_artifact(task, change.get("path"))
                            if artifact:
                                artifact_paths.add(artifact["path"])
                                await progress(activity={"kind": "file_change", "text": artifact["path"]}, artifact=artifact)
                elif event.get("method") in {"item/started", "item/completed"} and params.get("threadId") == self.thread_id and params.get("turnId") == self.turn_id:
                    await flush_assistant()
                    await record_item(params, "started" if event.get("method") == "item/started" else "completed")
                elif event.get("method") == "turn/completed" and params.get("threadId") == self.thread_id:
                    completed = params.get("turn") or {}
                    if completed.get("id") != self.turn_id:
                        continue
                    await flush_assistant()
                    status = completed.get("status")
                    if status == "completed":
                        for path in artifact_paths:
                            artifact = _workspace_artifact(task, path)
                            if artifact:
                                await progress(artifact=artifact)
                        final_output = [text for item_id, text in output
                                        if (observed_items.get((self.thread_id, self.turn_id, item_id)) or {}).get("phase") == "final_answer"]
                        return {"status": "completed", "result": "\n\n".join(final_output or [text for _item_id, text in output]), "provider_session_id": provider_session,
                                "thread_id": self.thread_id, "turn_id": self.turn_id}
                    if status == "interrupted":
                        raise VoiceError("EXECUTION_INTERRUPTED", "Codex stopped before it completed the task.")
                    failure = completed.get("error") or {}
                    detail = str(failure.get("message", "")).lower()
                    category = failure.get("codexErrorInfo")
                    if "requires a newer version of codex" in detail:
                        raise VoiceError("CODEX_UPDATE_REQUIRED", "The configured model requires a newer Codex CLI. Update Codex through its supported setup flow, then Continue this task.")
                    if category == "usageLimitExceeded":
                        raise VoiceError("CODEX_USAGE_LIMIT", "Codex usage is unavailable. Check your account limits before continuing.")
                    if category == "unauthorized" or "not authenticated" in detail or "authentication required" in detail:
                        raise VoiceError("CODEX_AUTH_REQUIRED", "Sign in to Codex, then Continue this task.")
                    raise VoiceError("EXECUTION_FAILED", "Codex could not complete the task. Review its task for details.")
        finally:
            await self.rpc.close()

    async def steer(self, text):
        text = _text(text, "redirect", 12000)
        async with self.steer_lock:
            if self.cancel_requested or not self.rpc or not self.thread_id or not self.turn_id:
                raise VoiceError("STEERING_UNAVAILABLE", "Codex has no active task turn to redirect.")
            expected_turn_id = self.turn_id
            try:
                await self.rpc.request("turn/steer", {
                    "threadId": self.thread_id,
                    "expectedTurnId": expected_turn_id,
                    "input": [{"type": "text", "text": text, "text_elements": []}],
                })
            except VoiceError as exc:
                if exc.code in {"CODEX_REQUEST_FAILED", "CODEX_DISCONNECTED"}:
                    raise VoiceError("STEERING_UNAVAILABLE", "Codex could not accept that correction. The task may have already finished; use Continue if needed.") from None
                raise

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
                streamed_text, terminal_result = [], None
                session_id, turn_id, completed = task["id"], None, False
                async for message in self.client.receive_response():
                    if isinstance(message, sdk.AssistantMessage):
                        session_id = message.session_id or session_id
                        turn_id = message.uuid or message.message_id or turn_id
                        for block in message.content:
                            if isinstance(block, sdk.TextBlock):
                                streamed_text.append(block.text)
                    elif isinstance(message, sdk.ResultMessage):
                        completed = True
                        session_id = message.session_id or session_id
                        turn_id = message.uuid or turn_id
                        if message.result:
                            terminal_result = message.result
                        if message.is_error:
                            raise VoiceError("EXECUTION_FAILED", "Claude could not complete the task. Review its task for details.")
                if not completed:
                    raise VoiceError("CLAUDE_DISCONNECTED", "Claude stopped before returning a final result.")
                result = terminal_result or "\n".join(part for part in streamed_text if part)
                return {"status": "completed", "result": result,
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
                 "provider_session_id": None, "thread_id": None, "turn_id": None, "result": "", "error": None, "approval": None,
                 "capabilities": {"steer": tool == "codex" and task.get("mode") != "offline", "continue": True},
                 "resume_thread_id": task.get("resume_thread_id") if tool == "codex" and task.get("resume_required") else None}
        await self._published_update(task["id"], children=[*task.get("children", []), child])
        return child

    async def _record_activity(self, task_id, activity):
        if not isinstance(activity, dict):
            return
        kind, text = activity.get("kind"), activity.get("text")
        if not isinstance(kind, str) or not isinstance(text, str) or not kind or not text:
            return
        entry = {"kind": kind[:64], "text": text[:4000]}
        stream_id = activity.get("stream_id")
        if isinstance(stream_id, str) and stream_id:
            entry["stream_id"] = stream_id[:640]
        task = self.store.get(task_id)
        activity = list(task.get("activity") or [])
        if (kind == "assistant" and entry.get("stream_id") and activity
                and activity[-1].get("kind") == "assistant"
                and activity[-1].get("stream_id") == entry["stream_id"]
                and len(activity[-1]["text"]) + len(entry["text"]) <= 4000):
            activity[-1] = dict(entry, text=activity[-1]["text"] + entry["text"])
        else:
            activity.append(entry)
        activity = activity[-MAX_ACTIVITY:]
        await self._published_update(task_id, event="activity", activity=activity)

    async def _record_artifact(self, task_id, artifact):
        if not isinstance(artifact, dict) or set(artifact) != {"path", "exists", "verification"}:
            return
        task = self.store.get(task_id)
        artifacts = [item for item in task.get("artifacts", []) if item.get("path") != artifact["path"]]
        artifacts.append(artifact)
        await self._published_update(task_id, event="artifact", artifacts=artifacts[-80:])

    async def _record_instruction(self, task_id, text, outcome, message=""):
        task = self.store.get(task_id)
        entries = list(task.get("instruction_outcomes") or [])[-(MAX_INSTRUCTION_OUTCOMES - 1):]
        entries.append({"text": text[:12000], "outcome": outcome[:64], "message": message[:1000]})
        await self._published_update(task_id, event="instruction", instruction_outcomes=entries)

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
        codex = "codex" in self.adapters or bool(self.codex_binary or shutil.which("codex"))
        try:
            __import__("claude_agent_sdk") if self.claude_sdk_module is None else self.claude_sdk_module
            claude_sdk = True
        except ImportError:
            claude_sdk = False
        claude_sdk = "claude" in self.adapters or claude_sdk
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
            claude_ready = bool("claude" in self.adapters or (claude_sdk and claude_key))
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
        if operation == "steer":
            return await self._steer(task, params)
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
        await self._published_update(task["id"], capabilities={"steer": tool == "codex" and task.get("mode") != "offline", "continue": True},
                                     activity=list(task.get("activity") or [])[-MAX_ACTIVITY:],
                                     artifacts=list(task.get("artifacts") or [])[-80:],
                                     instruction_outcomes=list(task.get("instruction_outcomes") or [])[-MAX_INSTRUCTION_OUTCOMES:])
        task = self.store.get(task["id"])
        child = await self._new_child(task, tool, instructions)
        key = (task["id"], child["id"])

        async def progress(**changes):
            activity = changes.pop("activity", None)
            artifact = changes.pop("artifact", None)
            if changes:
                await self._child_update(task["id"], child["id"], **changes)
            if activity:
                await self._record_activity(task["id"], activity)
            if artifact:
                await self._record_artifact(task["id"], artifact)

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
            if tool == "codex" and final.get("thread_id"):
                await self._published_update(task["id"], resume_thread_id=final["thread_id"], resume_required=False)
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

    async def _steer(self, task, params):
        child_id = _text(params.get("child_id"), "coding task identity", 200)
        text = _text(params.get("text"), "redirect", 12000)
        child = next((item for item in task.get("children", []) if item.get("id") == child_id), None)
        if not child or child.get("tool") != "codex":
            raise VoiceError("STEERING_UNAVAILABLE", "Only the active Codex task can accept a correction.")
        adapter = self.active.get((task["id"], child_id))
        if not adapter or not hasattr(adapter, "steer"):
            await self._record_instruction(task["id"], text, "rejected", "Codex is no longer running.")
            raise VoiceError("STEERING_UNAVAILABLE", "Codex has already finished. Use Continue to give it another instruction.")
        try:
            await adapter.steer(text)
        except VoiceError as exc:
            await self._record_instruction(task["id"], text, "rejected", exc.message)
            raise
        await self._record_instruction(task["id"], text, "accepted")
        await self._record_activity(task["id"], {"kind": "instruction", "text": "Correction sent to Codex."})
        return {"status": "accepted", "child_id": child_id}

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
