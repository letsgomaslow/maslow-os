"""Scratch-only task bridge for the GPT-Live whole-idea experiment.

This is deliberately a small integration layer: realtime transports feed final
typed or spoken turns here, while the existing durable ``TaskManager`` owns
submission, reconciliation, cancellation, and result state.  It never accepts
an executable instruction from the conversation transport.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import signal
import tempfile
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from maslow_voice.errors import VoiceError
from maslow_voice.tasks import TaskManager, text_field, validate_brief
from maslow_voice.store import TERMINAL


TASK_CONTRACT_VERSION = 1
MAX_BRIEF_SECONDS = 45
BriefBuilder = Callable[[str, Path], Awaitable[dict[str, Any]]]


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _request_id(session_id: str, turn_id: str, source: str, project: Path, dedupe_identity: str = "") -> str:
    material = json.dumps({"v": TASK_CONTRACT_VERSION, "session": session_id,
                           "turn": dedupe_identity or turn_id, "source": "" if dedupe_identity else source,
                           "project": str(project)}, sort_keys=True).encode()
    return "gpt-live-v1-" + hashlib.sha256(material).hexdigest()[:48]


MAX_OUTPUT_BYTES = 256_000


async def _terminate(process) -> None:
    """Reap our entire process group, including children holding stdout open."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(asyncio.shield(process.wait()), 2)
            # A parent can exit before its descendants. Ensure none survive.
            if sig == signal.SIGTERM:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            return
        except TimeoutError:
            continue
    raise VoiceError("HERMES_STOP_FAILED", "The local agent could not be stopped safely.")


def _diagnostic(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace").lower()
    for code, needles in (
        ("HERMES_DEPENDENCY_MISSING", ("modulenotfounderror", "no module named", "library not loaded")),
        ("HERMES_SANDBOX_DENIED", ("operation not permitted", "permission denied", "sandbox-exec:")),
        ("OPENAI_AUTH_FAILED", ("invalid_api_key", "authenticationerror", "incorrect api key", "401")),
        ("OPENAI_QUOTA_EXCEEDED", ("insufficient_quota", "rate_limit", "429")),
        ("OPENAI_MODEL_UNAVAILABLE", ("model_not_found", "does not exist or you do not have access")),
        ("HERMES_EXECUTABLE_FAILED", ("no such file or directory", "command not found")),
        ("HERMES_PROFILE_INVALID", ("unknown provider", "unsupported provider", "invalid provider")),
        ("OPENAI_CONNECTION_FAILED", ("connectionerror", "connection error", "certificate_verify_failed")),
    ):
        if any(needle in text for needle in needles):
            return code
    return "HERMES_AGENT_FAILED"


async def _collect(process, timeout: float) -> bytes:
    """Drain both pipes concurrently; retain only a safe stderr category."""
    async def errors():
        kept = bytearray()
        if process.stderr is not None:
            while chunk := await process.stderr.read(16_384):
                kept.extend(chunk[:max(0, 16_384 - len(kept))])
        process.scratch_diagnostic = _diagnostic(bytes(kept))
        lowered = kept.decode("utf-8", "replace").lower()
        process.scratch_diagnostic_flags = [flag for flag in
            ("state.db", "dotenv", "sandbox", "sqlite", "traceback", "uv", "api key", "provider", "model")
            if flag in lowered]
        process.scratch_exception = next((name for name in
            ("PermissionError", "FileNotFoundError", "ModuleNotFoundError", "TypeError", "ValueError", "RuntimeError", "OperationalError")
            if name.lower() in lowered), None)
    stderr = asyncio.create_task(errors())
    async def read():
        output = bytearray()
        while chunk := await process.stdout.read(16_384):
            output.extend(chunk)
            if len(output) > MAX_OUTPUT_BYTES:
                raise VoiceError("HERMES_OUTPUT_LIMIT", "The local agent exceeded the scratch output limit.")
        await process.wait()
        await stderr
        return bytes(output)
    try:
        return await asyncio.wait_for(read(), timeout)
    except BaseException:
        await _terminate(process)
        raise
    finally:
        if not stderr.done():
            stderr.cancel()
        await asyncio.gather(stderr, return_exceptions=True)


async def _spawn(profile, binary, prompt):
    launch = asyncio.create_task(asyncio.create_subprocess_exec(
        *profile.command(binary, prompt), cwd=profile.root, env=profile.prepare()[1],
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, start_new_session=True))
    try:
        return await asyncio.shield(launch)
    except asyncio.CancelledError:
        # Cancellation during process creation must not lose ownership of a child.
        async def cleanup():
            process = await launch
            await _terminate(process)
        cleanup_task = asyncio.create_task(cleanup())
        await asyncio.shield(cleanup_task)
        raise


class HermesProfile:
    """Isolated temporary config; the caller supplies credentials in RAM only."""

    def __init__(self, root: Path, openai_key: str, model: str = "gpt-5-mini") -> None:
        self.root, self.key, self.model = root.resolve(), openai_key, model
        self.environment = None
        self.last_diagnostic = {}
        self.capture_synthetic_failure_once = False

    def prepare(self) -> tuple[dict[str, Any], dict[str, str]]:
        if not self.key:
            raise VoiceError("OPENAI_KEY_REQUIRED", "Save an OpenAI key to enable the scratch agent.")
        model = {"default": self.model, "provider": "openai-api", "base_url": "https://api.openai.com/v1"}
        if self.environment is None:
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            config = {
                "model": model, "platform_toolsets": {"cli": []}, "mcp_servers": {},
                "agent": {"max_turns": 2, "disabled_toolsets": ["kanban"]}, "terminal": {"backend": "local", "cwd": str(self.root)},
                "memory": {"enabled": False}, "compression": {"enabled": False},
                "telemetry": {"enabled": False}, "fallback_model": None, "fallback_models": [],
                "security": {"allow_lazy_installs": False}, "plugins": {"enabled": []},
                "skills": {"creation_nudge_interval": 0, "external_dirs": []},
            }
            path = self.root / "config.yaml"
            path.write_text(json.dumps(config) + "\n")
            path.chmod(0o600)
            # Never inherit ambient credentials, hooks, proxy settings, or user config.
            self.environment = {
                "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin",
                "HOME": str(self.root), "HERMES_HOME": str(self.root), "TMPDIR": str(self.root),
                "XDG_CONFIG_HOME": str(self.root), "XDG_CACHE_HOME": str(self.root),
                "HERMES_DISABLE_LAZY_INSTALLS": "1", "HERMES_ENABLE_PROJECT_PLUGINS": "false",
                "DO_NOT_TRACK": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHON_DOTENV_DISABLED": "1",
                "OPENAI_API_KEY": self.key,
            }
        return model, self.environment

    def command(self, binary: str, prompt: str) -> list[str]:
        self.prepare()
        executable = shutil.which(binary) if binary == "hermes" else binary
        if not executable:
            raise VoiceError("HERMES_MISSING", "A local Hermes installation is required for the scratch agent.")
        if not Path("/usr/bin/sandbox-exec").is_file():
            raise VoiceError("SCRATCH_SANDBOX_REQUIRED", "This private scratch runner requires the Mac sandbox.")
        # No model tools; OS-level write boundary also confines runtime caches/logs.
        sessions = self.root / "sessions"
        sessions.mkdir(exist_ok=True)
        # Hermes tolerates an unavailable session DB and failed debug dumps.
        # Prevent raw conversation snapshots and ambient dotenv imports at the OS boundary.
        policy = ('(version 1)(allow default)(deny file-write*)'
                  '(allow file-write* (subpath ' + json.dumps(str(self.root)) + ') (literal "/dev/null"))'
                  '(deny file-read-data (regex #"/[.]env$") (regex #"/[.]op[.]env$"))'
                  '(deny file-write* (subpath ' + json.dumps(str(sessions)) + ')'
                  ' (regex ' + json.dumps('^' + re.escape(str(self.root / 'state.db'))) + '))')
        return ["/usr/bin/sandbox-exec", "-p", policy, executable, "--oneshot", prompt,
                "--in", str(self.root), "--ignore-rules", "--model", self.model, "--provider", "openai-api"]


def _parse_json_output(output: bytes, diagnostic: dict[str, Any]) -> dict[str, Any]:
    """Accept a whole JSON object, optionally inside one enclosing Markdown fence."""
    diagnostic.update(output_bytes=len(output), startswith_fence=False, json_error=None,
                      leading_known_banner=None)
    try:
        text = output.decode("utf-8").strip()
        diagnostic["startswith_fence"] = text.startswith("```")
        diagnostic["starts_json"] = text.startswith("{")
        diagnostic["leading_known_banner"] = next((label for prefix, label in
            (("Warning:", "warning"), ("WARNING:", "warning"), ("hermes -z:", "hermes_oneshot"),
             ("Hermes", "hermes"), ("\x1b[", "ansi")) if text.startswith(prefix)), None)
        fenced = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            text = fenced.group(1)
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeDecodeError) as error:
        diagnostic["json_error"] = type(error).__name__
        if isinstance(error, json.JSONDecodeError):
            diagnostic["json_error_line"] = error.lineno
            diagnostic["json_error_column"] = error.colno
        category = _diagnostic(output)
        diagnostic["stdout_error_category"] = category if category != "HERMES_AGENT_FAILED" else None
        raise VoiceError("BRIEF_INVALID", "The local planning agent returned an unreadable result.") from None


def _redact_synthetic_output(output: bytes, key: str) -> str:
    """Explicit, single-use debugging of the fixed synthetic prompt only."""
    value = output.decode("utf-8", "replace")
    if key:
        value = value.replace(key, "[REDACTED]")
    value = re.sub(r"(?i)\b(?:sk|sess|pk)-[A-Za-z0-9_-]+", "[REDACTED]", value)
    value = re.sub(r"(?i)(?:authorization\s*[:=]\s*)?(?:bearer|basic)\s+[^\s\"']+", "[REDACTED]", value)
    value = re.sub(r"(?i)(?:api[_ -]?key|token|secret|password)\s*[\"']?\s*[:=]\s*[\"']?[^\s\"']+", "[REDACTED]", value)
    # Suppress home/temp paths and URL query strings; neither helps explain format.
    value = re.sub(r"(?:/Users/|/private/var/|/var/folders/)[^\s\"']+", "[PATH]", value)
    value = re.sub(r"(https?://[^\s?]+)\?[^\s]+", r"\1?[REDACTED]", value)
    return value[:512]


class HermesJSONAgent:
    def __init__(self, binary="hermes", model="gpt-5-mini", timeout=MAX_BRIEF_SECONDS, profile=None):
        self.binary, self.model, self.timeout, self.profile = binary, model, timeout, profile

    async def __call__(self, prompt: str, project: Path) -> dict[str, Any]:
        if self.profile is None:
            raise VoiceError("SCRATCH_PROFILE_REQUIRED", "The scratch agent needs its isolated profile.")
        capture_synthetic = self.profile.capture_synthetic_failure_once
        self.profile.capture_synthetic_failure_once = False
        process = await _spawn(self.profile, self.binary, prompt)
        try:
            output = await _collect(process, self.timeout)
        except TimeoutError:
            raise VoiceError("BRIEF_TIMEOUT", "The local planning agent did not respond in time.") from None
        self.profile.last_diagnostic = {
            "exit_code": process.returncode, "category": getattr(process, "scratch_diagnostic", "HERMES_AGENT_FAILED"),
            "flags": getattr(process, "scratch_diagnostic_flags", []),
            "exception": getattr(process, "scratch_exception", None),
        }
        if process.returncode != 0:
            raise VoiceError(getattr(process, "scratch_diagnostic", "HERMES_AGENT_FAILED"),
                             "The local planning agent could not prepare this task.")
        try:
            return _parse_json_output(output, self.profile.last_diagnostic)
        except VoiceError:
            if capture_synthetic:
                self.profile.last_diagnostic["redacted_synthetic_output"] = _redact_synthetic_output(output, self.profile.key)
            raise


class HermesOneShotBriefAgent(HermesJSONAgent):
    async def __call__(self, prompt, project):
        value = await super().__call__(prompt, project)
        fields = ("objective", "summary", "constraints", "requested_output", "tool_preference", "unresolved_questions")
        self.profile.last_diagnostic["brief_shape"] = {
            name: {"type": type(value.get(name)).__name__,
                   "length": len(value[name]) if isinstance(value.get(name), list) else None}
            for name in fields
        }
        self.profile.last_diagnostic["unsupported_field_count"] = len(set(value) - set(fields))
        return validate_brief(value)


class GPTLiveBackend:
    """Provider-neutral full-duplex turn intake over the existing task backend."""

    def __init__(self, tasks: TaskManager, brief_builder: BriefBuilder, scratch_root: str | Path, planner=None) -> None:
        self.tasks, self.brief_builder, self.planner = tasks, brief_builder, planner
        self.action_locks = {}
        self.delegations = {}
        self.delegation_lock = asyncio.Lock()
        self.planning = set()
        self.scratch_root = Path(scratch_root).resolve()
        self.pending: dict[str, asyncio.Task[dict[str, Any]]] = {}

    def _project(self, project: str | Path) -> Path:
        path = Path(project).expanduser().resolve()
        if not path.is_dir() or not _inside(path, self.scratch_root):
            raise VoiceError("SCRATCH_PROJECT_REQUIRED", "Choose a project inside the GPT-Live scratch workspace.")
        return path

    @staticmethod
    def _prompt(source: str, context: str) -> str:
        return """Return exactly one JSON object with all six fields and no other fields, prose, or Markdown fences.
Use this exact shape (replace the example strings with the actual brief):
{"objective":"Create a small scratch page","summary":"Describe the requested work for the executor.","constraints":[],"requested_output":"One small HTML file","tool_preference":"auto","unresolved_questions":[]}

Field types and limits:
- objective: a nonempty string, at most 1000 characters.
- summary: a nonempty string, at most 12000 characters.
- constraints: an array of strings, at most 30 items and 2000 characters per item. Use [] when none.
- requested_output: a string, at most 12000 characters.
- tool_preference: a string exactly equal to "auto", "hermes", "codex", or "claude".
- unresolved_questions: an array of strings, at most 30 items and 2000 characters per item. Use [] when none.
Never use null, an object, or a single string for either array field.

You are planning a bounded local scratch task for a separate executor. Do not use tools, commands,
web, messaging, browser, publication, or external services. The executor may only create or update
a small text or HTML artifact inside the selected scratch project. Preserve the user's request;
put necessary clarification questions in unresolved_questions if the request is unclear.

User request:
""" + source + ("\n\nUser-provided context:\n" + context if context else "")

    def _existing(self, request_id: str) -> dict[str, Any] | None:
        return next((task for task in self.tasks.store.list(10_000) if task.get("request_id") == request_id), None)

    async def submit_turn(self, *, channel: str, session_id: str, turn_id: str, text: str,
                          project: str | Path, context: str = "", mode: str = "openai",
                          preferred_coder: str = "auto", dedupe_identity: str = "",
                          expected_artifact: str = "") -> dict[str, Any]:
        if channel not in {"typed", "voice"}:
            raise VoiceError("INVALID_TURN", "The task must come from a typed or final voice turn.")
        session = text_field(session_id, "session identity", 200, True)
        turn = text_field(turn_id, "turn identity", 200, True)
        source = text_field(text, "original request", 24_000, True)
        context = text_field(context, "context", 12_000)
        workspace = self._project(project)
        dedupe_identity = text_field(dedupe_identity, "delegation identity", 300)
        expected_artifact = text_field(expected_artifact, "expected artifact", 300)
        if expected_artifact:
            target = (workspace / expected_artifact).resolve()
            if Path(expected_artifact).is_absolute() or not _inside(target, workspace) or target == workspace:
                raise VoiceError("INVALID_ARTIFACT", "The expected artifact must be a relative path inside the scratch project.")
        request_id = _request_id(session, turn, source, workspace, dedupe_identity)
        existing = self._existing(request_id)
        if existing:
            return {"contract_version": TASK_CONTRACT_VERSION, "duplicate": True, "task": existing}
        if request_id not in self.pending:
            self.pending[request_id] = asyncio.create_task(
                self._prepare(request_id, source, context, workspace, mode, preferred_coder, expected_artifact)
            )
        task = await asyncio.shield(self.pending[request_id])
        return {"contract_version": TASK_CONTRACT_VERSION, "duplicate": False, "task": task}

    async def _prepare(self, request_id: str, source: str, context: str, project: Path,
                       mode: str, preferred_coder: str, expected_artifact: str) -> dict[str, Any]:
        try:
            brief = validate_brief(await self.brief_builder(self._prompt(source, context), project))
            # These are host policy constraints, not model-provided authority.
            constraints = list(dict.fromkeys(brief["constraints"] + [
                "Work only inside the selected GPT-Live scratch project.",
                "Do not send messages, publish content, or use web services.",
                "Create or update only a small text or HTML artifact.",
            ]))
            brief = dict(brief, constraints=constraints)
            original = source + ("\n\nUser-provided context:\n" + context if context else "")
            if expected_artifact:
                original += "\n\nExpected test artifact (must exist before completion): " + expected_artifact
            return await self.tasks.submit(request_id, brief, str(project), mode, original, preferred_coder)
        finally:
            self.pending.pop(request_id, None)

    async def task_action(self, task_id: str, operation: str, text: str = "", approval_id: str | None = None) -> dict[str, Any]:
        if operation not in {"redirect", "cancel"}:
            return await self.tasks.action(task_id, operation, text, approval_id)
        async with self.action_locks.setdefault(task_id, asyncio.Lock()):
            task = self.tasks.store.get(task_id)
            if operation == "redirect":
                text = text_field(text, "redirect", required=True)
            # Join the previous monitor before changing this same task's attempt.
            # Its final status cannot overwrite the new revision.
            worker = self.tasks.monitors.get(task_id)
            if worker and not worker.done():
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
            task = self.tasks.store.get(task_id)
            client = self.tasks.clients.get(task_id)
            if task.get("run_id"):
                client = client or await self.tasks.client_factory(task)
                await client.stop(task["run_id"])
            self.tasks.store.update(task_id, event="revision_stopped" if operation == "redirect" else "cancelled",
                                    state="cancelled", result="", error=None)
            if operation == "redirect":
                return await self.tasks.action(task_id, "continue", "Explicit revision: " + text)
            await self.tasks.publish()
            return self.tasks.store.get(task_id)

    def snapshot(self) -> dict[str, Any]:
        tasks = []
        for task in self.tasks.store.list(100):
            task = dict(task)
            task["revision"] = len(self.tasks.store.events(task["id"]))
            tasks.append(task)
        return {"contract_version": TASK_CONTRACT_VERSION, "tasks": tasks}

    async def submit_delegation(self, *, delegation_id: str, transcript: list[dict[str, Any]],
                                project: str | Path, session_id: str = "gpt-live", context: str = "",
                                expected_artifact: str = "", preferred_coder: str = "auto",
                                correction_task_id: str = "") -> dict[str, Any]:
        """Interpret a client-delegation snapshot; delegation alone is not a turn."""
        if correction_task_id:
            if not transcript:
                raise VoiceError("TRANSCRIPT_REQUIRED", "Wait for a correction transcript before redirecting a task.")
            correction = "\n".join(text_field(item.get("text", ""), "transcript text", 24_000, True)
                                   for item in transcript if isinstance(item, dict) and item.get("role") == "user")
            if not correction:
                raise VoiceError("TRANSCRIPT_REQUIRED", "The correction needs a user transcript.")
            return {"correction": True, "task": await self.task_action(correction_task_id, "redirect", correction)}
        delegation = text_field(delegation_id, "delegation identity", 300, True)
        if not isinstance(transcript, list) or not transcript:
            raise VoiceError("TRANSCRIPT_REQUIRED", "Wait for a role-labelled transcript snapshot before delegating work.")
        lines = []
        for item in transcript:
            if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                raise VoiceError("INVALID_TRANSCRIPT", "The delegation transcript has an unsupported role.")
            value = text_field(item.get("text", ""), "transcript text", 24_000, True)
            lines.append(item["role"].title() + ": " + value)
        source = "\n".join(lines)
        workspace = self._project(project)
        identity = _request_id(session_id, delegation, source, workspace, delegation)
        async with self.delegation_lock:
            if identity in self.delegations:
                return dict(self.delegations[identity], duplicate=True)
            if self.planner is None:
                raise VoiceError("PLANNER_REQUIRED", "The delegation planner is not configured.")
            snapshot = [{"id": t["id"], "state": t["state"], "objective": t["brief"]["objective"],
                         "summary": t["brief"]["summary"], "attempt": t.get("attempt", 0)}
                        for t in self.tasks.store.list(100) if t["project"] == str(workspace)]
            prompt = ("Interpret this conversation and current tasks. Return exactly JSON with action "
                      "(new, redirect, cancel, or clarify), task_id (existing ID only for redirect/cancel), "
                      "text (complete new task request or revision), question (for clarify). "
                      "Delegate only work the user requested; ambiguity needs clarify. A correction to an "
                      "existing task is redirect, never a duplicate new task. Do not execute tools.\n" +
                      json.dumps({"transcript": source, "context": context, "tasks": snapshot}))
            planning = asyncio.create_task(self.planner(prompt, workspace))
            self.planning.add(planning)
            try:
                plan = await planning
            finally:
                self.planning.discard(planning)
            if not isinstance(plan, dict):
                raise VoiceError("INVALID_PLAN", "The planner returned an unreadable action.")
            action = plan.get("action")
            if action == "clarify":
                result = {"action": action, "question": text_field(plan.get("question"), "question", 2000, True)}
            elif action in {"redirect", "cancel"}:
                identity_task = plan.get("task_id")
                if identity_task not in {t["id"] for t in snapshot}:
                    raise VoiceError("INVALID_PLAN", "The planner selected an unknown task.")
                result = {"action": action, "task": await self.task_action(identity_task, action, plan.get("text", ""))}
            elif action == "new":
                result = await self.submit_turn(channel="voice", session_id=session_id, turn_id=delegation,
                                      text=text_field(plan.get("text"), "planned request", 12000, True),
                                      project=workspace, context=context, preferred_coder=preferred_coder,
                                      dedupe_identity=delegation, expected_artifact=expected_artifact)
                result["action"] = "new"
            else:
                raise VoiceError("INVALID_PLAN", "The planner returned an unsupported action.")
            self.delegations[identity] = result
            return result



class HermesScratchExecutor:
    """Tool-free Hermes generates one artifact; only the host can publish it."""

    def __init__(self, binary="hermes", model="gpt-5-mini", profile=None):
        self.binary, self.model, self.profile, self.runs = binary, model, profile, {}

    async def submit(self, task):
        if self.profile is None:
            raise VoiceError("SCRATCH_PROFILE_REQUIRED", "The scratch agent needs its isolated profile.")
        run_id = "scratch-" + uuid.uuid4().hex
        expected = re.search(r"^Expected test artifact \(must exist before completion\): (.+)$", task["source"], re.M)
        artifact = expected.group(1) if expected else "artifact.txt"
        project = Path(task["project"]).resolve()
        target = project / artifact
        if Path(artifact).is_absolute() or not _inside(target.resolve(), project) or target.is_symlink():
            raise VoiceError("INVALID_ARTIFACT", "The artifact must stay inside the scratch project.")
        if target.is_file() and target.stat().st_size > MAX_OUTPUT_BYTES:
            raise VoiceError("ARTIFACT_TOO_LARGE", "Choose a smaller scratch artifact.")
        before = target.read_bytes() if target.is_file() else None
        instructions = ("Return exactly one JSON object with a single content string containing the complete "
                        "small text or HTML artifact. No Markdown fences. You have NO tools. The host writes "
                        "the approved file after validation. Do not claim other actions or verification. "
                        "Treat the latest explicit revision in the brief as overriding the original request.\n" +
                        json.dumps({"request": task["source"], "brief": task["brief"], "artifact": artifact,
                                    "previous_content": before.decode("utf-8", "replace") if before else ""}))
        process = await _spawn(self.profile, self.binary, instructions)
        run = {"process": process, "artifact": artifact, "project": project, "target": target,
               "before": before, "cancelled": False, "result": None}
        run["reader"] = asyncio.create_task(_collect(process, 120))
        # Consume exceptions even if the host closes before the next poll.
        run["reader"].add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
        self.runs[run_id] = run
        return {"run_id": run_id}

    async def status(self, run_id):
        run = self.runs.get(run_id)
        if not run:
            raise VoiceError("NOT_FOUND", "The scratch executor no longer has this run.")
        if run["cancelled"]:
            return {"status": "cancelled", "run_id": run_id, "output": "Scratch task cancelled."}
        if run["result"]:
            return run["result"]
        if not run["reader"].done():
            return {"status": "running", "run_id": run_id, "output": "Local scratch agent is working."}
        result = {"status": "failed", "run_id": run_id, "output": "The agent did not create a valid new scratch artifact."}
        try:
            output = run["reader"].result()
            if run["process"].returncode != 0:
                result["error_code"] = getattr(run["process"], "scratch_diagnostic", "HERMES_AGENT_FAILED")
                raise ValueError
            self.profile.last_diagnostic = {"exit_code": run["process"].returncode}
            value = _parse_json_output(output, self.profile.last_diagnostic)
            if not isinstance(value, dict) or set(value) != {"content"} or not isinstance(value["content"], str):
                raise ValueError
            content = value["content"].encode("utf-8")
            if not content.strip() or len(content) > MAX_OUTPUT_BYTES or content == run["before"]:
                raise ValueError
            target, project = run["target"], run["project"]
            if target.is_symlink() or not _inside(target.resolve(), project):
                raise ValueError
            if target.is_file() and target.stat().st_size > MAX_OUTPUT_BYTES:
                raise ValueError
            current = target.read_bytes() if target.is_file() else None
            if current != run["before"]:
                raise ValueError  # Do not overwrite a concurrent user edit.
            target.parent.mkdir(parents=True, exist_ok=True)
            # This synchronous checked replace has no cancellation point. Cancelled
            # attempts never reach it; subsequent polls cannot publish twice.
            fd, temporary = tempfile.mkstemp(prefix=".gpt-live-", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(content)
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
            result = {"status": "completed", "run_id": run_id, "output": "Created or updated scratch artifact: " + run["artifact"]}
        except (ValueError, OSError, VoiceError, TimeoutError):
            pass
        run["result"] = result
        return result

    async def stop(self, run_id):
        run = self.runs.get(run_id)
        if run:
            run["cancelled"] = True
            if run["process"].returncode is None or not run["reader"].done():
                await _terminate(run["process"])
            if not run["reader"].done():
                run["reader"].cancel()
            await asyncio.gather(run["reader"], return_exceptions=True)
        return {"stopped": True}

    async def steer(self, run_id, text):
        raise VoiceError("STEER_UNSUPPORTED", "Redirect this task through the scratch revision controller.")

    async def approve(self, run_id, request_id, allow):
        raise VoiceError("APPROVAL_UNSUPPORTED", "This bounded scratch executor has no approval prompt.")

    async def events(self, run_id):
        if False:
            yield {}

    async def close(self):
        for run_id in list(self.runs):
            await self.stop(run_id)


class GPTLiveScratchRuntime:
    """Owns temporary task state; closing voice never closes this runtime implicitly."""

    ram_credentials_only = True

    def __init__(self, backend: GPTLiveBackend, tasks: TaskManager, store: Any, executor: HermesScratchExecutor,
                 temporary: tempfile.TemporaryDirectory[str], profile: HermesProfile) -> None:
        self.backend, self.tasks, self.store, self.executor, self.temporary, self.profile = backend, tasks, store, executor, temporary, profile

    async def close(self) -> None:
        planners = list(self.backend.pending.values()) + list(self.backend.planning)
        for planner in planners:
            planner.cancel()
        await asyncio.gather(*planners, return_exceptions=True)
        await self.tasks.close()
        await self.executor.close()
        self.store.close()
        self.temporary.cleanup()
        self.profile.key = ""
        if self.profile.environment is not None:
            self.profile.environment.clear()

    def diagnostics(self) -> dict[str, Any]:
        return dict(self.profile.last_diagnostic)

    async def readiness(self) -> dict[str, Any]:
        """Check local launchability without opening Hermes configuration or secrets."""
        binary = shutil.which(self.executor.binary) if self.executor.binary == "hermes" else self.executor.binary
        if not binary:
            return {"ready": False, "agent": "Hermes", "model": "unavailable", "message": "Hermes is not available."}
        try:
            model, _environment = self.profile.prepare()
            self.profile.command(self.executor.binary, "readiness only")
        except VoiceError as error:
            return {"ready": False, "agent": "Hermes", "model": "configured default", "message": error.message}
        return {"ready": True, "agent": "Hermes", "model": self.executor.model or str(model.get("default", model.get("model", "configured default"))),
                "message": "A compatible local Hermes model is configured. Authentication is checked when the planner starts."}


def create_backend(scratch_root: str | Path, *, openai_key: str = "", model: str = "gpt-5-mini", binary: str = "hermes",
                   brief_builder: BriefBuilder | None = None, planner=None) -> GPTLiveScratchRuntime:
    """Create the isolated Mac runtime; caller keeps it past voice-session end."""
    from maslow_voice.store import TaskStore
    root = Path(scratch_root).resolve()
    if not root.is_dir():
        raise VoiceError("SCRATCH_PROJECT_REQUIRED", "Create the GPT-Live scratch workspace before starting.")
    temporary = tempfile.TemporaryDirectory(prefix="maslow-gpt-live-")
    store = TaskStore(Path(temporary.name) / "state")
    profile = HermesProfile(Path(temporary.name) / "hermes-home", openai_key, model)
    executor = HermesScratchExecutor(binary, model, profile)

    async def client_factory(_task):
        return executor

    async def publish():
        return None

    tasks = TaskManager(store, client_factory, publish)
    backend = GPTLiveBackend(tasks, brief_builder or HermesOneShotBriefAgent(binary, model, profile=profile), root,
                             planner=planner or HermesJSONAgent(binary, model, profile=profile))
    return GPTLiveScratchRuntime(backend, tasks, store, executor, temporary, profile)
