"""Deterministic routing from Voice tasks to peer execution agents."""

from __future__ import annotations

import asyncio
import inspect

from .errors import VoiceError


AGENTS = ("codex", "hermes", "claude")
DIRECT_AGENTS = {"codex", "claude"}


def _agent_label(agent):
    return {"codex": "Codex", "hermes": "Hermes", "claude": "Claude"}.get(agent, "the selected agent")


def direct_instructions(task):
    """Render the saved user request and normalized brief without adding authority."""
    brief = task["brief"]
    sections = [
        "Complete the following task from the user. The original request is authoritative; the task brief is only a summary.",
        "Original request:\n" + task["source"],
        "Objective:\n" + brief["objective"],
        "Summary:\n" + brief["summary"],
    ]
    if brief.get("constraints"):
        sections.append("Constraints:\n" + "\n".join("- " + item for item in brief["constraints"]))
    if brief.get("requested_output"):
        sections.append("Requested output:\n" + brief["requested_output"])
    return "\n\n".join(sections)


class DirectExecutionClient:
    """TaskManager-compatible client for a Voice-owned Codex or Claude run.

    These runs live only in this daemon process. A new client deliberately cannot
    rediscover an old run, allowing TaskManager recovery to mark it interrupted
    instead of risking a duplicate submission.
    """

    resumable = False

    def __init__(self, execution, agent):
        if agent not in DIRECT_AGENTS:
            raise ValueError("A direct execution client requires Codex or Claude.")
        self.execution = execution
        self.agent = agent
        self.task_id = None
        self.run_id = None
        self.child_id = None
        self.job = None

    def _require_run(self, run_id):
        if not self.run_id or run_id != self.run_id:
            raise VoiceError("NOT_FOUND", "This direct execution no longer exists in the running Voice daemon.")

    async def submit(self, task):
        if self.job:
            raise VoiceError("RUN_ALREADY_STARTED", "This direct execution has already started.")
        self.task_id = task["id"]
        previous = {child.get("id") for child in task.get("children", [])}
        self.run_id = "direct:" + task["id"] + ":" + str(task.get("attempt", 0))
        self.job = asyncio.create_task(self.execution.handle(task, "coding", {
            "tool": self.agent,
            "instructions": direct_instructions(task),
        }))
        # ExecutionManager persists the child before its first asynchronous publish.
        # Yield once so status calls can identify this exact child.
        await asyncio.sleep(0)
        saved = self.execution.store.get(task["id"])
        created = [child for child in saved.get("children", []) if child.get("id") not in previous]
        if created:
            self.child_id = created[-1]["id"]
        elif self.job.done():
            # Consume the concrete setup failure and let TaskManager persist it.
            await self.job
        else:
            self.job.cancel()
            await asyncio.gather(self.job, return_exceptions=True)
            raise VoiceError("EXECUTOR_UNAVAILABLE", "The selected agent did not create a direct execution.")
        self.job.add_done_callback(self._consume_result)
        return {"run_id": self.run_id, "status": "started"}

    @staticmethod
    def _consume_result(job):
        if not job.cancelled():
            job.exception()

    def _child(self):
        if not self.task_id or not self.child_id:
            raise VoiceError("NOT_FOUND", "This direct execution is unavailable.")
        task = self.execution.store.get(self.task_id)
        child = next((item for item in task.get("children", []) if item.get("id") == self.child_id), None)
        if not child:
            raise VoiceError("NOT_FOUND", "This direct execution is no longer in Voice history.")
        return task, child

    async def status(self, run_id):
        self._require_run(run_id)
        task, child = self._child()
        status = child.get("status", "running")
        mapped = {
            "queued": "pending",
            "running": "running",
            "awaiting_approval": "waiting_for_approval",
            "completed": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }.get(status, "interrupted")
        result = {"status": mapped, "run_id": run_id, "session_id": task["id"], "output": child.get("result", "")}
        if mapped == "waiting_for_approval":
            result["approval"] = task.get("approval") or child.get("approval")
        return result

    async def events(self, run_id):
        self._require_run(run_id)
        if False:
            yield {}

    async def stop(self, run_id):
        self._require_run(run_id)
        await self.execution.cancel(self.task_id)
        if self.job and not self.job.done():
            self.job.cancel()
            await asyncio.gather(self.job, return_exceptions=True)
        return {"status": "stopping"}

    async def steer(self, run_id, text):
        self._require_run(run_id)
        raise VoiceError("STEERING_UNAVAILABLE", "Direct Codex and Claude tasks cannot be redirected while running. Stop the task, then continue with revised instructions.")

    async def approve(self, run_id, request_id, allow):
        self._require_run(run_id)
        task, child = self._child()
        await self.execution.handle(task, "approve" if allow else "deny", {
            "approval_id": request_id,
            "child_id": child["id"],
        })
        return {"status": "approved" if allow else "denied"}


class AgentRouter:
    """Resolve one persisted agent choice and return its compatible client."""

    def __init__(self, execution, hermes_factory, *, settings=None, hermes_readiness=None):
        self.execution = execution
        self.hermes_factory = hermes_factory
        self.settings = settings
        self.hermes_readiness = hermes_readiness
        self.hermes_clients = {}

    def _configured_default(self, task):
        preferred = task.get("preferred_coder")
        if preferred in AGENTS:
            return preferred
        config = self.settings.value if self.settings else {}
        configured = config.get("default_coder", "auto")
        return configured if configured in AGENTS else None

    async def _hermes_is_ready(self, task):
        if self.hermes_readiness:
            value = self.hermes_readiness(task)
            if inspect.isawaitable(value):
                value = await value
            if isinstance(value, dict):
                return bool(value.get("ready"))
            return value is True
        try:
            self.hermes_clients[task["id"]] = await self.hermes_factory(task)
            return True
        except VoiceError:
            return False

    async def _readiness(self, task, agents=AGENTS):
        direct = await self.execution.readiness(task)
        readiness = {agent: bool((direct.get(agent) or {}).get("ready")) for agent in DIRECT_AGENTS if agent in agents}
        if "hermes" in agents:
            readiness["hermes"] = await self._hermes_is_ready(task)
        return readiness

    async def select_agent(self, task, requested=None):
        requested = requested or (task.get("brief") or {}).get("tool_preference", "auto")
        if requested not in {*AGENTS, "auto"}:
            raise VoiceError("INVALID_CODER", "Choose Codex, Hermes, Claude, or automatic task routing.")
        if requested != "auto":
            readiness = await self._readiness(task, (requested,))
            if not readiness.get(requested):
                label = _agent_label(requested)
                raise VoiceError("AGENT_UNAVAILABLE", f"{label} is not ready. Finish its setup or choose another task agent.")
            return {"selected_agent": requested, "routing_reason": f"The user explicitly selected {_agent_label(requested)}."}

        readiness = await self._readiness(task)
        configured = self._configured_default(task)
        candidates = []
        for candidate in (configured, "codex", "hermes", "claude"):
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        selected = next((candidate for candidate in candidates if readiness.get(candidate)), None)
        if not selected:
            raise VoiceError("AGENT_UNAVAILABLE", "No task agent is ready. Finish setting up Codex, Hermes, or Claude and try again.")
        reason = (f"{_agent_label(selected)} is the configured default and is ready."
                  if selected == configured else f"{_agent_label(selected)} is the first ready agent in automatic routing order.")
        return {"selected_agent": selected, "routing_reason": reason}

    async def validate_selected(self, task):
        """Recheck a reviewed choice without changing its recorded reason."""
        selected = task.get("selected_agent")
        if selected not in AGENTS:
            raise VoiceError("AGENT_NOT_SELECTED", "This task has no persisted execution agent.")
        readiness = await self._readiness(task, (selected,))
        if not readiness.get(selected):
            raise VoiceError("AGENT_UNAVAILABLE", f"{_agent_label(selected)} is not ready. Finish its setup or choose another task agent.")
        return {"selected_agent": selected, "routing_reason": task.get("routing_reason", "")}

    async def client(self, task):
        selected = task.get("selected_agent")
        # Records created before peer routing were always Hermes-owned. Keep their
        # known durable coordinator path during upgrade instead of inventing a new
        # direct run or changing their recorded history.
        if selected is None:
            return await self.hermes_factory(task)
        if selected not in AGENTS:
            raise VoiceError("AGENT_NOT_SELECTED", "This task has no persisted execution agent.")
        if selected == "hermes":
            cached = self.hermes_clients.pop(task["id"], None)
            return cached or await self.hermes_factory(task)
        return DirectExecutionClient(self.execution, selected)
