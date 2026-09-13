"""Idempotent task handoff and recovery independent of the microphone lifecycle."""

import asyncio
from pathlib import Path

from .errors import VoiceError
from .hermes import normalized_status
from .store import TERMINAL

DEAD_COORDINATOR_ERRORS = {"OFFLINE_UNAVAILABLE", "OFFLINE_HERMES_EXITED"}


def text_field(value, name, maximum=12000, required=False):
    if not isinstance(value, str) or len(value) > maximum or "\x00" in value or (required and not value.strip()):
        raise VoiceError("INVALID_BRIEF", "The task's " + name + " is missing or too long.")
    return value.strip()


def validate_brief(value):
    fields = {"objective", "summary", "constraints", "requested_output", "tool_preference", "unresolved_questions"}
    if not isinstance(value, dict) or set(value) - fields:
        raise VoiceError("INVALID_BRIEF", "The conversation supplied unsupported task instructions.")
    result = {"objective": text_field(value.get("objective", ""), "objective", 1000, True),
              "summary": text_field(value.get("summary", ""), "summary", required=True),
              "requested_output": text_field(value.get("requested_output", ""), "requested output"),
              "tool_preference": value.get("tool_preference", "auto")}
    if result["tool_preference"] not in {"auto", "hermes", "codex", "claude"}:
        raise VoiceError("INVALID_BRIEF", "The requested coding tool is not supported.")
    for name in ("constraints", "unresolved_questions"):
        items = value.get(name, [])
        if not isinstance(items, list) or len(items) > 30:
            raise VoiceError("INVALID_BRIEF", "The task contains too many constraints or questions.")
        result[name] = [text_field(item, name, 2000) for item in items]
    return result


class TaskManager:
    def __init__(self, store, client_factory, publish, children=None):
        self.store, self.client_factory, self.publish, self.children = store, client_factory, publish, children
        self.monitors = {}
        self.restart_pending = set()
        self.project_locks = {}
        self.clients = {}
        self.closed = False

    async def submit(self, request_id, brief, project, mode, source, preferred_coder="codex"):
        brief = validate_brief(brief)
        source = text_field(source, "original request", 24000, True)
        if brief["unresolved_questions"]:
            raise VoiceError("CLARIFICATION_REQUIRED", " ".join(brief["unresolved_questions"]))
        path = Path(project).expanduser()
        if not project or not path.is_absolute() or not path.is_dir():
            raise VoiceError("PROJECT_REQUIRED", "Choose an existing project folder before delegating work.")
        task, created = self.store.create(request_id, brief, str(path.resolve()), mode, source)
        if created:
            task = self.store.update(task["id"], preferred_coder=preferred_coder)
            self._start(task)
            await self.publish()
        return task

    def _start(self, task):
        current = self.monitors.get(task["id"])
        if current and not current.done():
            if task["state"] == "queued" and task["id"] not in self.restart_pending:
                self.restart_pending.add(task["id"])

                def restart(_done, identity=task["id"]):
                    self.restart_pending.discard(identity)
                    if self.closed:
                        return
                    saved = self.store.get(identity)
                    if saved["state"] == "queued":
                        self._start(saved)

                current.add_done_callback(restart)
            return
        if current is None or current.done():
            worker = asyncio.create_task(self._run(task["id"]))
            self.monitors[task["id"]] = worker
            def finished(done, identity=task["id"]):
                if self.monitors.get(identity) is done:
                    self.monitors.pop(identity, None)
            worker.add_done_callback(finished)

    async def recover(self):
        for task in self.store.active():
            # A persisted submission reservation is replayed using its original key.
            # After the upstream 24h idempotency window, do not risk a second execution.
            import time
            if task["state"] == "stopping" and not task["run_id"]:
                self.store.update(task["id"], state="interrupted", error={"code": "STOP_UNCERTAIN", "message": "The stop arrived during handoff. Review coordinator history before continuing."})
            elif task["state"] == "submitting" and not task["run_id"] and time.time() - task["updated_at"] > 23 * 3600:
                self.store.update(task["id"], state="interrupted", error={"code": "SUBMISSION_UNCERTAIN", "message": "The previous handoff could not be reconciled. Review the coordinator history before continuing."})
            else:
                self._start(task)

    async def _run(self, task_id):
        task = self.store.get(task_id)
        lock = self.project_locks.setdefault(task["project"], asyncio.Lock())
        stream, client = None, None
        try:
            async with lock:
                task = self.store.get(task_id)
                if task["state"] in TERMINAL:
                    return
                client = await self.client_factory(task)
                self.clients[task_id] = client
                task = self.store.get(task_id)
                if task["state"] in TERMINAL or (task["state"] == "stopping" and not task.get("run_id")):
                    return
                if not task.get("run_id"):
                    self.store.update(task_id, state="submitting")
                    await self.publish()
                    response = await client.submit(task)
                    stopped = self.store.get(task_id)["state"] == "stopping"
                    task = self.store.update(task_id, state="stopping" if stopped else "accepted", run_id=response["run_id"], session_id=task.get("session_id") or task_id)
                    if stopped:
                        await client.stop(task["run_id"])
                    await self.publish()
                stream = asyncio.create_task(self._events(task_id, client, task["run_id"]))
                delay = 1
                while not self.closed:
                    try:
                        status = await client.status(task["run_id"])
                        update = normalized_status(status)
                        if not update.get("session_id"):
                            update.pop("session_id", None)
                        previous = self.store.get(task_id)
                        if (previous.get("approval") or {}).get("owner") == "child" and update["state"] not in TERMINAL:
                            update["approval"] = previous["approval"]
                            update["state"] = "awaiting_approval"
                        if any(previous.get(key) != value for key, value in update.items()):
                            self.store.update(task_id, event="executor_status", **update)
                            await self.publish()
                        if update["state"] in TERMINAL:
                            if self.children and update["state"] != "completed":
                                await self.children.cancel(task_id)
                            return
                        delay = 1
                    except VoiceError as exc:
                        if exc.code == "NOT_FOUND":
                            if self.children:
                                await self.children.cancel(task_id)
                            self.store.update(task_id, state="interrupted", error={"code": "RUN_LOST", "message": "The coordinator no longer has this run. Review its partial results before continuing."})
                            await self.publish()
                            return
                        confirmed_exit = getattr(client, "confirmed_process_exit", None)
                        if exc.code in DEAD_COORDINATOR_ERRORS or (confirmed_exit and confirmed_exit()):
                            await self._interrupt_dead_coordinator(task_id, client)
                            return
                        self.store.update(task_id, error={"code": "RECONNECTING", "message": "Reconnecting to the task coordinator; this task has not been resubmitted."})
                        await self.publish()
                        delay = min(delay * 2, 30)
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        except VoiceError as exc:
            if exc.code in DEAD_COORDINATOR_ERRORS:
                await self._interrupt_dead_coordinator(task_id, client)
                return
            if self.children:
                await self.children.cancel(task_id)
            task = self.store.get(task_id)
            state = "interrupted" if task["state"] == "submitting" or task.get("run_id") else "failed"
            self.store.update(task_id, state=state, error=exc.as_dict())
            await self.publish()
        except Exception:
            if self.children:
                await self.children.cancel(task_id)
            self.store.update(task_id, state="interrupted", error={"code": "EXECUTOR_UNAVAILABLE", "message": "The coordinator needs attention. Review this task before continuing."})
            await self.publish()
        finally:
            if stream:
                stream.cancel()
                await asyncio.gather(stream, return_exceptions=True)

    async def _interrupt_dead_coordinator(self, task_id, client):
        record_exit = getattr(client, "record_process_exit", None)
        if record_exit:
            record_exit()
        if self.children:
            await self.children.cancel(task_id)
        self.store.update(task_id, state="interrupted", error={
            "code": "COORDINATOR_EXITED",
            "message": "The local task coordinator stopped. Review partial changes, then use Continue to start a new attempt.",
        })
        await self.publish()

    async def _events(self, task_id, client, run_id):
        try:
            async for event in client.events(run_id):
                # Persist progress facts, not arbitrary raw provider logs or reasoning.
                kind = str(event.get("type", ""))
                if kind in {"tool_start", "tool_complete", "tool_progress", "run.started", "run.completed", "approval.required"}:
                    safe = {key: event[key] for key in ("type", "tool_name", "status") if isinstance(event.get(key), str)}
                    self.store._event(task_id, "progress", safe)
                    await self.publish()
        except (Exception, asyncio.CancelledError):
            # Poll reconciliation continues; do not reopen a second consuming SSE stream.
            return

    async def action(self, task_id, operation, text="", approval_id=None):
        task = self.store.get(task_id)
        if operation == "dismiss":
            if task["state"] not in TERMINAL:
                raise VoiceError("TASK_ACTIVE", "Finish or stop this task before dismissing it.")
            result = self.store.update(task_id, dismissed=True)
        elif operation == "continue":
            if task["state"] not in TERMINAL | {"waiting_input"}:
                raise VoiceError("TASK_ACTIVE", "Use Redirect while this task is running.")
            answer = text_field(text, "continuation", required=True)
            client = self.clients.get(task_id)
            discard = getattr(client, "discard_dead_process", None)
            if discard and discard():
                self.clients.pop(task_id, None)
            brief = dict(task["brief"], summary=task["brief"]["summary"] + "\nUser continuation: " + answer)
            result = self.store.update(task_id, state="queued", run_id=None, attempt=task.get("attempt", 0) + 1, brief=brief, error=None, dismissed=False)
            self._start(result)
        elif operation == "cancel" and task["state"] == "queued":
            result = self.store.update(task_id, state="cancelled")
        elif operation == "cancel" and not task.get("run_id") and task["state"] == "submitting":
            result = self.store.update(task_id, state="stopping")
            if self.children:
                await self.children.cancel(task_id)
        else:
            if task["state"] in TERMINAL or not task.get("run_id"):
                raise VoiceError("TASK_NOT_RUNNING", "This task has no active execution to change.")
            client = self.clients.get(task_id) or await self.client_factory(task)
            if operation == "cancel":
                try:
                    await client.stop(task["run_id"])
                finally:
                    if self.children:
                        await self.children.cancel(task_id)
                result = self.store.update(task_id, state="stopping")
            elif operation == "steer":
                await client.steer(task["run_id"], text_field(text, "redirect", required=True))
                result = self.store.update(task_id, event="steer_queued", pending_steer=text)
            elif operation in {"approve", "deny"}:
                current = task.get("approval") or {}
                identity = current.get("request_id")
                if not identity or approval_id != identity:
                    raise VoiceError("APPROVAL_EXPIRED", "Refresh and review the current approval before responding.")
                await client.approve(task["run_id"], identity, operation == "approve")
                result = self.store.update(task_id, event="approval_answered", approval=None)
            else:
                raise VoiceError("INVALID_TASK_ACTION", "That task action is not supported.")
        await self.publish()
        return result

    async def close(self):
        self.closed = True
        workers = list(self.monitors.values())
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
