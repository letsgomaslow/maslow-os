"""Private Mac GPT-Live experiment; never package this development server."""

import argparse
import asyncio
import contextlib
import importlib
import hashlib
import logging
import os
from pathlib import Path
import tempfile
import time
import uuid

from aiohttp import web

from livekit_mac import Session, ProviderError, create_app, ORIGIN
from maslow_voice.errors import VoiceError

CURRENT_PROVIDER = object()

class LiveSession(Session):
    def __init__(self, *, scratch=None):
        super().__init__(kind="openai")
        self.label = "GPT-Live"
        self.selected_voice = "marin"
        self.voices = [{"name": name} for name in (
            "marin", "cedar", "quartz", "ripple", "vesper", "willow", "stone",
            "gleam", "meridian", "bossa", "tempo", "beacon", "delta", "cinder")]
        self.scratch = Path(scratch or tempfile.mkdtemp(prefix="maslow-gpt-live-"))
        self.runtime = None
        self.backend_error = None
        self.speaking = False
        self.metrics = {}
        self.session_id = uuid.uuid4().hex
        self.notices = {}
        self.background = set()
        self.task_versions = {}
        self.task_notes = []
        self.last_fragment = 0
        self.revision = 0
        self.accepted_delegations = 0
        self.claimed_delegations = set()

    async def setup_backend(self):
        try:
            module = importlib.import_module("gpt_live_backend")
            importlib.reload(module)
            runtime = module.create_backend(self.scratch, openai_key=self.credentials.get("openai", ""))
            readiness = await runtime.readiness()
            if not readiness["ready"]:
                await runtime.close()
                self.backend_error = readiness["message"]
                return
            self.runtime = runtime
            self.backend_engine = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()[:12]
            self.backend_error = None
        except Exception:
            self.backend_error = "The local task agent is not ready yet. Voice checks can still run."

    def save(self, body):
        if self.runtime and (self.runtime.backend.pending or any(
                task["state"] not in {"completed", "cancelled", "failed", "interrupted"}
                for task in self.runtime.backend.snapshot()["tasks"])):
            raise ProviderError("Finish or stop the test task before changing the connection.", "TEST_BUSY")
        super().save(body)
        if self.runtime:
            self.runtime.profile.key = self.credentials["openai"]
            if self.runtime.profile.environment is not None:
                self.runtime.profile.environment["OPENAI_API_KEY"] = self.credentials["openai"]

    def status(self):
        if self.provider and hasattr(self.provider, "metrics_snapshot"):
            self.metrics = self.provider.metrics_snapshot()
        status = super().status()
        status.update(provider="gpt-live", speaking=self.speaking, metrics=self.metrics,
                      backend_ready=self.runtime is not None, backend_error=self.backend_error,
                      pending_handoffs=len(self.notices), accepted_handoffs=self.accepted_delegations,
                      task_counts={})
        if self.runtime and hasattr(self.runtime, "diagnostics"):
            status["backend_diagnostic"] = self.runtime.diagnostics()
        if self.runtime:
            for task in self.runtime.backend.snapshot()["tasks"]:
                state = task.get("state", "unknown")
                status["task_counts"][state] = status["task_counts"].get(state, 0) + 1
        return status

    def private_view(self):
        return {"transcript": self.transcripts,
                "tasks": self.runtime.backend.snapshot()["tasks"] if self.runtime else [],
                "notes": self.task_notes[-10:], "workspace": str(self.scratch)}

    def spawn(self, awaitable):
        task = asyncio.create_task(awaitable)
        self.background.add(task)
        task.add_done_callback(self.background.discard)
        return task

    async def emit(self, event):
        kind = event.get("type")
        if kind == "transcript_delta":
            role = event.get("role")
            delta = event.get("delta", "")
            if role in self.turns and isinstance(delta, str):
                if self.transcripts and self.transcripts[-1]["role"] == role:
                    self.transcripts[-1]["text"] = (self.transcripts[-1]["text"] + delta)[-12000:]
                else:
                    self.transcripts.append({"role": role, "text": delta,
                                             "offset": event.get("start_ms")})
                    self.turns[role] += 1
                self.transcripts = self.transcripts[-30:]
                if role == "user":
                    self.last_fragment = time.monotonic()
                    self.revision += 1
        elif kind == "delegation":
            identity = event.get("delegation_id")
            claimed = getattr(self, "claimed_delegations", set())
            if identity and identity not in claimed and self.mode in {"conversation", "scenario"}:
                claimed.add(identity)
                self.claimed_delegations = claimed
                self.notices[identity] = {"received": time.monotonic()}
                self.spawn(self.delegate(identity, self.provider, self.session_id))
        elif kind == "voice_state":
            await super().emit(event)
            self.speaking = bool(event.get("speaking"))
        elif kind == "closed":
            self.stop_signal.set()
        elif kind == "error":
            await super().emit(event)
        elif kind == "level":
            self.level = event.get("level", 0)

    async def context(self, kind, content, delegation_id=None, *, provider=CURRENT_PROVIDER):
        target = self.provider if provider is CURRENT_PROVIDER else provider
        if not target or target is not self.provider:
            return
        # Fixed host summaries stay well below the Live context token limit.
        safe = content.encode("utf-8")[:480].decode("utf-8", errors="ignore")
        with contextlib.suppress(Exception):
            await target.append_context(kind, safe, delegation_id)

    async def delegate(self, identity, provider, session_id):
        try:
            # Coalesce transport fragments. This is NOT a final-turn assertion:
            # the separate planning agent must still judge scope and ambiguity.
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                await asyncio.sleep(.25)
                if provider is not self.provider or self.stop_signal.is_set():
                    return
                if self.revision and time.monotonic() - self.last_fragment >= 1.5:
                    break
            if not self.runtime:
                await self.context("commentary", "The task agent is unavailable. No task was started.", identity, provider=provider)
                return
            snapshot = [dict(item) for item in self.transcripts]
            if not any(item["role"] == "user" and item["text"].strip() for item in snapshot):
                await self.context("commentary", "No clear task request was captured. Please ask the user to repeat the task.", identity, provider=provider)
                return
            await self.context("thinking", "The separate local agent is checking the requested task. Keep the conversation going.", identity, provider=provider)
            response = await self.runtime.backend.submit_delegation(
                delegation_id=identity, transcript=snapshot, project=getattr(self, "conversation_project", self.scratch),
                expected_artifact="result.html",
                context="This is a local scratch experiment. Create or update result.html when an artifact is requested. Transcript fragments may be incomplete; ask for clarification if scope is unclear.")
            if response.get("action") == "clarify":
                question = response.get("question", "Please clarify the requested task.")
                self.task_notes.append(question)
                await self.context("commentary", "The task planner needs clarification: " + question, identity, provider=provider)
                return
            self.accepted_delegations += 1
            task = response.get("task", response)
            action = response.get("action", "new")
            self.task_notes.append({"cancel": "Voice request cancelled the task.", "redirect": "Voice correction updated the existing task."}.get(action, "Voice handoff accepted by the local task agent."))
            await self.context("thinking", "The local task agent applied the request. Current verified state: " + str(task.get("state", "accepted")) + ". Task: " + str(task.get("brief", {}).get("objective", "scratch artifact")) + ".", identity, provider=provider)
            self.spawn(self.watch_task(task.get("id"), identity, provider))
        except Exception as error:
            message = (error.code + ": " + str(error)) if isinstance(error, VoiceError) else "The task agent needs a clearer request or its connection needs attention. No completion is confirmed."
            self.task_notes.append(message)
            await self.context("commentary", message, identity, provider=provider)
        finally:
            self.notices.pop(identity, None)

    async def watch_task(self, identity, delegation_id=None, provider=None):
        if not identity:
            return
        watch_id = uuid.uuid4().hex
        self.task_versions[identity] = watch_id
        expected_attempt = None
        while self.runtime:
            if self.task_versions.get(identity) != watch_id:
                return
            task = next((item for item in self.runtime.backend.snapshot()["tasks"] if item["id"] == identity), None)
            if not task:
                return
            attempt = task.get("attempt", 0)
            if expected_attempt is None:
                expected_attempt = attempt
            if attempt != expected_attempt:
                return
            state = task.get("state")
            if state in {"completed", "failed", "cancelled", "interrupted", "waiting_input"}:
                message = {"completed": "The local agent reports this task completed. Check the task panel for the saved result.",
                           "cancelled": "The task was cancelled.", "failed": "The task failed. The task panel has its status.",
                           "interrupted": "The task was interrupted; completion is not confirmed.",
                           "waiting_input": "The task agent needs more information. Check the task panel."}[state]
                await self.context("commentary", message, delegation_id, provider=provider)
                return
            await asyncio.sleep(.5)

    async def extra_action(self, name, body):
        if not isinstance(body, dict):
            raise ProviderError("The request could not be read.", "INVALID_REQUEST")
        if name == "reload-host":
            if body or self.status()["busy"]:
                raise ProviderError("Stop audio before refreshing the private tester.", "TEST_BUSY")
            module = importlib.import_module("gpt_live_mac")
            importlib.reload(module)
            self.__class__ = module.LiveSession
        elif name == "clear":
            if body:
                raise ProviderError("The request could not be read.", "INVALID_REQUEST")
            await self.end()
            await self.clear_connection()
            self.credentials.clear()
            self.result = None
        elif name == "scenario":
            if set(body) - {"voice"}:
                raise ProviderError("The test selection could not be read.", "INVALID_REQUEST")
            self.start("scenario", body.get("voice"))
        elif name == "prepare-backend":
            if body or (self.runtime and (self.runtime.backend.snapshot()["tasks"] or self.runtime.backend.pending)):
                raise ProviderError("Finish this test before reloading its task runner.", "INVALID_REQUEST")
            if self.runtime:
                await self.runtime.close()
                self.runtime = None
            await self.setup_backend()
        elif name == "synthetic-planner-check":
            if body or not self.runtime or self.status()["busy"] or self.background:
                raise ProviderError("Wait for the current test before checking the planner.", "TEST_BUSY")
            self.runtime.profile.capture_synthetic_failure_once = True
            self.task_notes = ["Checking the local planner with a fixed test request…"]
            self.spawn(self.typed_task("Create result.html with a weekend hiking checklist. Include Water, Snacks, Rain jacket, First aid. Use a green heading.", uuid.uuid4().hex))
        elif name == "task":
            if not self.runtime:
                raise ProviderError("The local task agent is still being prepared.", "BACKEND_NOT_READY")
            text = body.get("text")
            if set(body) - {"text", "request_id"} or not isinstance(text, str) or not text.strip() or len(text) > 8000:
                raise ProviderError("Write a short task for the local agent.", "INVALID_REQUEST")
            request_id = body.get("request_id")
            if not isinstance(request_id, str) or len(request_id) > 100 or not request_id:
                raise ProviderError("Reload the page before sending the task.", "INVALID_REQUEST")
            self.task_notes = ["The local agent is preparing the typed request…"]
            self.spawn(self.typed_task(text, request_id))
        elif name == "task-action":
            if not self.runtime or set(body) - {"id", "operation", "text"}:
                raise ProviderError("The task action could not be read.", "INVALID_REQUEST")
            operation = body.get("operation")
            if operation not in {"cancel", "redirect", "continue"}:
                raise ProviderError("Choose Stop, Redirect, or Continue.", "INVALID_REQUEST")
            result = await self.runtime.backend.task_action(body.get("id"), operation, body.get("text", ""))
            await self.context("thinking", "The user updated the background task through the task panel. Its current state is " + str(result.get("state", "pending")) + ".")
            if operation in {"redirect", "continue"}:
                self.spawn(self.watch_task(result["id"], provider=self.provider))
        elif name == "mute":
            if self.provider and set(body) == {"muted"} and isinstance(body["muted"], bool):
                await self.provider.mute(body["muted"])
            else:
                raise ProviderError("Start a conversation before changing the microphone.", "INVALID_REQUEST")
        else:
            raise web.HTTPNotFound()

    async def typed_task(self, text, request_id):
        try:
            response = await self.runtime.backend.submit_turn(channel="typed", session_id="private-mac-test",
                turn_id=request_id, text=text, project=self.scratch,
                expected_artifact="result.html",
                context="Create or update result.html in this scratch workspace when an artifact is requested.")
            self.task_notes.append("Typed task accepted by the local task agent.")
            await self.context("thinking", "A typed request was accepted by the separate task agent. Continue the conversation while it works.")
            await self.watch_task(response["task"]["id"], provider=self.provider)
        except Exception as error:
            self.task_notes.append((error.code + ": " + str(error)) if isinstance(error, VoiceError) else "The typed request could not be accepted. Check the task agent connection or clarify the request.")

    def start(self, mode, voice=None):
        self.session_id = uuid.uuid4().hex
        self.metrics = {}
        self.revision = 0
        self.last_fragment = 0
        self.claimed_delegations = set()
        self.conversation_project = self.scratch
        super().start(mode, voice)

    async def run(self, mode):
        # Reload orchestration and provider fixes without re-entering the key.
        try:
            module = importlib.import_module("gpt_live_session")
            importlib.reload(module)
            await module.run_live(self, mode)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            detail = type(error).__name__
            if isinstance(error, ModuleNotFoundError) and error.name:
                detail += " (" + error.name + ")"
            frame = error.__traceback__
            while frame and frame.tb_next:
                frame = frame.tb_next
            if frame:
                detail += " at " + Path(frame.tb_frame.f_code.co_filename).name
                detail += ":" + frame.tb_frame.f_code.co_name
                detail += ":" + str(frame.tb_lineno)
            self.error = {"code": "LIVE_TEST_FAILED",
                          "message": "GPT-Live test setup failed: " + detail + "."}
            self.state = "error"
            self.microphone = False
            if self.mode == "probe" and not self.result:
                self.result = {"passed": False, "physical_microphone_tested": False}

    async def end(self):
        await super().end()
        # A pre-session task failure used to leave the tester permanently
        # connecting because Session.end() only waits for unfinished jobs.
        if self.job and self.job.done() and self.state == "connecting":
            self.error = {"code": "LIVE_TEST_FAILED",
                          "message": "GPT-Live could not finish this test. Check account access and try again."}
            self.state = "error"
            self.microphone = False
            if self.mode == "probe" and not self.result:
                self.result = {"passed": False, "physical_microphone_tested": False}

    async def shutdown(self):
        for task in list(self.background):
            task.cancel()
        await asyncio.gather(*self.background, return_exceptions=True)
        if self.runtime:
            await self.runtime.close()
            self.runtime = None

    async def clear_connection(self):
        await self.shutdown()
        self.backend_error = "Save a connection and start a new test to prepare the task agent."


async def main(port=57519):
    logging.disable(logging.CRITICAL)
    asyncio.get_running_loop().set_exception_handler(lambda _loop, _context: None)
    session = LiveSession()
    app = create_app(session, page_path=Path(__file__).with_suffix(".html"))
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    app[ORIGIN] = f"http://127.0.0.1:{port}"
    print(app[ORIGIN], flush=True)
    with open(os.devnull, "w") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    session.spawn(session.setup_backend())
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=57519)
    try:
        asyncio.run(main(parser.parse_args().port))
    except KeyboardInterrupt:
        pass
