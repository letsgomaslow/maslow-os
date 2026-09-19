"""Desktop voice lifecycle and intent handoff; execution belongs to Hermes."""

import asyncio
import fcntl
import hashlib
import json
import os
import secrets
import shutil
import signal
import time
import uuid
from pathlib import Path

from .audio import PortAudioTransport
from .audit import SessionAudit
from .config import Settings, atomic_json, private_directory, runtime_directory, validate_settings
from .coordinator import HermesRuntime, hermes_configuration
from .hermes import HermesClient
from .errors import VoiceError
from .ipc import ControlServer, MAX_REQUEST, peer_is_owner, remove_stale_socket
from .keyring import Credentials
from .live_tasks import LiveTaskPlanner, LiveTranscript, live_request_id, live_update_text
from .models import discover_models, download_speech, test_model, verify_speech
from .providers import create_provider
from .store import TaskStore, TERMINAL
from .tasks import TaskManager, text_field, validate_brief


class VoiceService:
    def __init__(self, directory=None, runtime=None, *, provider_factory=create_provider, credentials=None, executor_factory=None,
                 audio_transport_factory=PortAudioTransport, live_planner=None):
        self.settings = Settings(directory)
        self.directory = self.settings.directory
        self.audit = SessionAudit(self.directory)
        self.runtime = private_directory(Path(runtime)) if runtime else runtime_directory()
        self.credentials = credentials or Credentials()
        self.store = TaskStore(self.directory)
        self.store.prune(self.settings.value["retention_days"])
        self.provider_factory = provider_factory
        self.audio_transport_factory = audio_transport_factory
        self.live_planner = live_planner or LiveTaskPlanner()
        self.provider = None
        self.session = {"id": str(uuid.uuid4()), "transcript": []}
        self.voice = {"enabled": False, "state": "disabled", "microphone": False, "speaking": False, "level": 0, "error": ""}
        self.readiness = {"ready": False, "checks": [], "models": [],
                          "conversation": {"ready": False, "checks": []}, "tasks": {"ready": False, "checks": []}}
        self.project = ""
        self.context = ""
        self.turn_id = ""
        self.source = ""
        self.turns = {}
        self.live_transcript = LiveTranscript()
        self.live_delegations = {}
        self.provider_epoch = None
        self.last_activity = time.monotonic()
        self.session_started = self.last_activity
        self.lifecycle_lock = asyncio.Lock()
        self.configuration_lock = asyncio.Lock()
        self.turn_lock = asyncio.Lock()
        self.conversation_requests = set()
        self.startup_task = None
        self.provider_cleanup = None
        self.work = set()
        self.level_publish_task = None
        self.level_publish_dirty = False
        self.offline = None
        self.offline_clients = {}
        self.offline_client_lock = asyncio.Lock()
        self.tool_socket = self.runtime / "tools.sock"
        # Existing coordinators may survive a Voice restart. Their private bridge
        # token stays stable; no account credentials are written here.
        token_file = self.directory / "bridge.json"
        if token_file.is_file() and not token_file.is_symlink():
            self.tool_token = json.loads(token_file.read_text())["token"]
        else:
            self.tool_token = secrets.token_urlsafe(32)
            atomic_json(token_file, {"token": self.tool_token})
        self.hermes = HermesRuntime(self.directory, self.settings, self.credentials, self.tool_socket, self.tool_token)
        self.execution = None
        self.tasks = TaskManager(self.store, executor_factory or self.executor_client, self.publish)
        self.control = ControlServer(self.runtime / "control.sock", self.dispatch, self.snapshot)
        self.tool_server = None

    def snapshot(self):
        tasks = []
        for task in self.store.list(50):
            if task.get("dismissed"):
                continue
            children = [dict(child, result=child.get("result", "")[:4000], instructions=child.get("instructions", "")[:2000])
                        for child in task.get("children", [])[-8:]]
            tasks.append(dict(task, result=task.get("result", "")[:12000], source=task.get("source", "")[:12000], children=children))
        session = dict(self.session, transcript=[dict(turn, text=turn["text"][-4000:]) for turn in self.session["transcript"][-40:]])
        snapshot = {"schemaVersion": 1, "voice": dict(self.voice), "settings": dict(self.settings.value),
                    "tasks": tasks, "session": session, "readiness": self.readiness}
        # Keep a busy task history within the IPC frame. Full results remain in
        # the store; approval details are never shortened for an approval decision.
        while len(tasks) > 1 and len(json.dumps(snapshot).encode()) > 3 * 1024 * 1024:
            tasks.pop()
        return snapshot

    async def publish(self):
        await self.control.publish()

    def background(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.work.add(task)
        task.add_done_callback(self.work.discard)
        return task

    def queue_level_publish(self):
        """Coalesce level snapshots without blocking microphone ingestion."""

        self.level_publish_dirty = True
        if self.level_publish_task is None or self.level_publish_task.done():
            self.level_publish_task = self.background(self._publish_levels())

    async def _publish_levels(self):
        current = asyncio.current_task()
        try:
            while self.level_publish_dirty:
                await asyncio.sleep(0.05)
                self.level_publish_dirty = False
                await self.publish()
        finally:
            if self.level_publish_task is current:
                self.level_publish_task = None

    async def _cancel_level_publish(self):
        self.level_publish_dirty = False
        task = self.level_publish_task
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        if self.level_publish_task is task:
            self.level_publish_task = None

    async def provider_event(self, event):
        kind = event.get("type")
        if kind == "voice_state":
            if self.voice["speaking"] and event.get("state") == "listening":
                self.last_activity = time.monotonic()
            self.voice.update(state=event["state"], microphone=bool(event.get("microphone")), speaking=bool(event.get("speaking")))
        elif kind == "metrics":
            self.audit.record("usage", session_id=self.session["id"], provider=self.settings.value["mode"], **event.get("usage", {}))
        elif kind == "task_error":
            self.voice["task_error"] = {"code": event.get("code"), "message": str(event.get("message", "Task needs setup."))[:300]}
        elif kind == "error":
            self.audit.record("error", session_id=self.session["id"], provider=self.settings.value["mode"], code=event.get("code"))
            self.voice.update(error=str(event.get("message", "Voice needs attention."))[:300], microphone=False)
            # A failed connection must release physical capture immediately.
            if self.provider:
                self.background(self.end_voice(preserve_error=True))
        elif kind == "closed":
            # Remote expiry and hangup are terminal for the audio conversation.
            # Durable tasks keep running after this provider is detached.
            if self.provider:
                self.background(self.end_voice())
            return  # end_voice publishes the final disabled snapshot.
        elif kind == "level":
            level = max(0, min(float(event.get("level", 0)), 1))
            self.voice["level"] = level
            self.queue_level_publish()
            return
        elif kind == "transcript":
            text = str(event.get("text", ""))[:24000]
            role = "user" if event.get("role") == "user" else "assistant"
            transcript = self.session["transcript"]
            if transcript and transcript[-1].get("partial") and transcript[-1]["role"] == role:
                if event.get("final"):
                    transcript[-1] = {"role": role, "text": text}
                else:
                    transcript[-1]["text"] = (transcript[-1]["text"] + text)[-24000:]
            else:
                transcript.append({"role": role, "text": text, "partial": not bool(event.get("final", True))})
            self.session["transcript"] = transcript[-100:]
            if role == "assistant" and event.get("final", True):
                self.last_activity = time.monotonic()
            if role == "user" and event.get("final", True):
                identity = event.get("turn_id")
                if isinstance(identity, str) and 0 < len(identity) <= 200 and identity not in self.turns:
                    self.turns[identity] = {"source": text, "project": self.project, "mode": self.settings.value["mode"],
                                            "context": self.context, "session_id": self.session["id"],
                                            "preferred_coder": self.settings.value["default_coder"],
                                            "task_policy": self.settings.value["task_policy"]}
                    if len(self.turns) > 100:
                        self.turns.pop(next(iter(self.turns)))
                self.source, self.turn_id = text, identity or ""
        elif kind == "transcript_delta":
            role = "user" if event.get("role") == "user" else "assistant"
            raw_delta = event.get("delta")
            delta = raw_delta[:8000] if isinstance(raw_delta, str) else ""
            self.live_transcript.append(role, delta, event.get("start_ms"), event.get("end_ms"))
            if delta:
                transcript = self.session["transcript"]
                if transcript and transcript[-1].get("partial") and transcript[-1]["role"] == role:
                    transcript[-1]["text"] = (transcript[-1]["text"] + delta)[-24000:]
                else:
                    transcript.append({"role": role, "text": delta, "partial": True})
                self.session["transcript"] = transcript[-100:]
        elif kind == "turn_complete":
            self.last_activity = time.monotonic()
        elif kind == "delegation" and self.settings.value["mode"] == "gpt_live":
            identity = event.get("delegation_id")
            if isinstance(identity, str) and identity and identity not in self.live_delegations:
                self.live_delegations[identity] = None
                self.background(self._handle_live_delegation(
                    self.provider, self.provider_epoch, identity, event.get("offset_ms"), self.live_transcript.mark()))
        await self.publish()

    async def _append_live_context(self, provider, epoch, kind, content, delegation_id=None):
        content = live_update_text(content)
        if not content or self.provider is not provider or self.provider_epoch is not epoch:
            return False
        try:
            await provider.append_context(kind, content, delegation_id)
            return True
        except VoiceError:
            return False

    async def _prepare_live_task(self, transcript, delegation_id, *, session_id, project, context, preferred_coder):
        path = Path(project).expanduser()
        if not project or not path.is_absolute() or not path.is_dir():
            raise VoiceError("PROJECT_REQUIRED", "Choose an existing project folder before delegating work.")
        project = str(path.resolve())
        active = [task for task in self.store.active() if task["project"] == project]
        plan = await asyncio.wait_for(self.live_planner.prepare(
            transcript, context=context, preferred_coder=preferred_coder, active_tasks=active), 5)
        if plan["action"] == "new":
            request_id = live_request_id(session_id, delegation_id, plan["source"])
            task = await self.tasks.submit(request_id, plan["brief"], project, "gpt_live", plan["source"], preferred_coder,
                                           policy=self.settings.value["task_policy"])
        else:
            task = await self.tasks.action(plan["task_id"], plan["action"], plan.get("text", ""))
        self.voice.pop("task_error", None)
        return task, plan["action"]

    async def _handle_live_delegation(self, provider, epoch, delegation_id, offset_ms, untimed_through):
        try:
            # Transcript fragments and the delegation notice use independent
            # event streams. Yield briefly for fragments at the same offset.
            await asyncio.sleep(0.1)
            if self.provider is not provider or self.provider_epoch is not epoch:
                return
            transcript = self.live_transcript.snapshot(offset_ms, untimed_through)
            task, action = await self._prepare_live_task(
                transcript, delegation_id, session_id=self.session["id"], project=self.project,
                context=self.context, preferred_coder=self.settings.value["default_coder"])
            if self.provider is not provider or self.provider_epoch is not epoch:
                return  # The durable task survives, but this conversation is gone.
            self.live_delegations[delegation_id] = task["id"]
            message = ("Maslow accepted the delegated task locally. The task remains active if audio stops." if action == "new"
                       else "Maslow accepted the task cancellation." if action == "cancel"
                       else "Maslow sent the correction to the active task.")
            await self._append_live_context(provider, epoch, "thinking", message, delegation_id)
            self.background(self._relay_live_task(provider, epoch, task["id"], delegation_id))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            message = error.message if isinstance(error, VoiceError) else "The local task planner needs attention."
            await self._append_live_context(provider, epoch, "commentary", "I could not start that task. " + message, delegation_id)

    async def _relay_live_task(self, provider, epoch, task_id, delegation_id=None):
        previous = None
        while True:
            task = self.store.get(task_id)
            state = task["state"]
            if state != previous:
                previous = state
                if state == "accepted":
                    await self._append_live_context(provider, epoch, "thinking", "Hermes accepted the task.", delegation_id)
                elif state == "running":
                    await self._append_live_context(provider, epoch, "thinking", "The selected local agent is working on the task.", delegation_id)
                elif state == "awaiting_approval":
                    await self._append_live_context(provider, epoch, "commentary", "The task needs your approval in Voice before it can continue.", delegation_id)
                elif state == "waiting_input":
                    await self._append_live_context(provider, epoch, "commentary", "The task needs more information. Review it in Voice to continue.", delegation_id)
                elif state == "completed":
                    result = live_update_text(task.get("result") or "The task completed with no result summary.", 400)
                    await self._append_live_context(provider, epoch, "commentary", "The task completed. " + result, delegation_id)
                    return
                elif state in {"failed", "interrupted"}:
                    error = task.get("error") or {}
                    message = live_update_text(error.get("message") or "The task stopped before a verified result.", 400)
                    await self._append_live_context(provider, epoch, "commentary", message, delegation_id)
                    return
                elif state == "cancelled":
                    await self._append_live_context(provider, epoch, "commentary", "The task was cancelled.", delegation_id)
                    return
            if self.provider is not provider or self.provider_epoch is not epoch:
                return
            await asyncio.sleep(0.25)

    async def submit_intent(self, intent, turn_id=None):
        brief = validate_brief(intent)
        turn = self.turns.get(turn_id)
        if not self.provider or not turn or not turn["source"]:
            raise VoiceError("TRANSCRIPT_PENDING", "Wait for the request transcript before handing off work.")
        # Identity comes from the captured user turn. The model cannot replace
        # the project, execution mode, original words, or authorization policy.
        fingerprint = hashlib.sha256(json.dumps(brief, sort_keys=True).encode()).hexdigest()[:24]
        request_id = turn["session_id"] + ":" + turn_id + ":" + fingerprint
        original = turn["source"] + ("\nExplicit user context:\n" + turn["context"] if turn["context"] else "")
        task = await self.tasks.submit(request_id, brief, turn["project"], turn["mode"], original, turn["preferred_coder"],
                                       policy=turn.get("task_policy", "lab_auto"))
        self.voice.pop("task_error", None)
        self.audit.record("task", session_id=self.session["id"], task_id=task["id"], selected_agent=task.get("selected_agent"), state=task["state"])
        return {"id": task["id"], "state": task["state"], "title": task["title"], "owner": task["owner"],
                "selected_agent": task.get("selected_agent", task.get("preferred_coder", "auto"))}

    async def selected_secrets(self):
        mode = self.settings.value["mode"]
        names = {"offline": [], "server": ["server_token"], "openai": ["openai"], "gpt_live": ["openai"],
                 "livekit": ["livekit_key", "livekit_secret"], "gemini_live": ["google"]}[mode]
        return {name: await self.credentials.get(name) for name in names}

    async def offline_runtime(self, project=None):
        from .offline import OfflineRuntime
        source = Path(os.path.abspath(project)) if project else None
        if self.offline and self.offline.workspace and self.offline.workspace.source != source:
            if self.provider or self.store.active():
                raise VoiceError("OFFLINE_PROJECT_BUSY", "Finish current work and end this conversation before choosing another offline project.")
            await self.offline.stop()
            self.offline = None
            self.offline_clients.clear()
        if self.offline is None:
            self.offline = OfflineRuntime(self.directory, self.settings.value)
        runtime = self.offline
        async def isolated_tool(request):
            task = self.store.get(request.get("session_id"))
            if task["mode"] != "offline" or not runtime.workspace or str(runtime.workspace.source) != task["project"]:
                raise VoiceError("OFFLINE_BOUNDARY", "The offline tool request does not belong to this workspace.")
            return {"ok": True, "result": await self.tool_request(request)}
        runtime.tool_handler = isolated_tool
        await self.offline.open_display()
        await self.offline.start(project=project)
        return self.offline

    async def hermes_ready(self, task):
        if not shutil.which("hermes"):
            return False
        try:
            await self.hermes.model_config(task["mode"])
            return True
        except VoiceError:
            return False

    async def executor_client(self, task):
        if task["mode"] == "offline":
            async with self.offline_client_lock:
                runtime = await self.offline_runtime(task["project"])
                cached = self.offline_clients.get(task["project"])
                if cached and cached.discard_dead_process():
                    self.offline_clients.pop(task["project"], None)
                if task["project"] not in self.offline_clients:
                    model, environment = await self.hermes.model_config("offline")
                    configuration = hermes_configuration(model, "", 18000, "/project")
                    source = Path(__file__).resolve().parent.parent / "hermes_plugin"
                    endpoint = await runtime.launch_hermes(configuration, source, {"MASLOW_VOICE_TOOL_TOKEN": self.tool_token})
                    self.offline_clients[task["project"]] = HermesClient(endpoint["endpoint"], endpoint["token"], request=runtime.hermes_request,
                        discard_process=lambda project=task["project"]: self.offline_clients.pop(project, None))
                return self.offline_clients[task["project"]]
        return await self.hermes.ensure(task)

    async def start_voice(self, *, audio=True, project="", context=""):
        async with self.lifecycle_lock:
            self.startup_task = asyncio.current_task()
            epoch = None
            try:
                if self.provider_cleanup and not self.provider_cleanup.done():
                    await asyncio.shield(self.provider_cleanup)
                if self.provider:
                    if audio != self.voice["enabled"]:
                        await self._stop_provider()
                    else:
                        if audio:
                            await self.provider.mute(False)
                        return
                if project:
                    path = Path(project).expanduser()
                    if not path.is_absolute() or not path.is_dir():
                        raise VoiceError("PROJECT_REQUIRED", "Choose an existing project folder.")
                    self.project = str(path.resolve())
                self.context = text_field(context, "context", 12000)
                epoch = self.provider_epoch = object()
                connecting_started = time.monotonic()
                self.voice.pop("task_error", None)
                self.voice.update(error="", state="connecting", enabled=audio, microphone=False, speaking=False)
                await self.publish()
                config = dict(self.settings.value)
                config["piper_executable"] = "/usr/lib/maslow-voice-local/piper"
                if not config["speech_directory"]:
                    config["speech_directory"] = str(self.directory / "speech")
                if config["mode"] == "offline":
                    runtime = await self.offline_runtime(self.project or None)
                    config["model_request"] = runtime.model_request
                    config["server_url"] = "http://127.0.0.1:11434"
                    config["server_kind"] = "ollama"
                if config["mode"] in {"offline", "server"} and audio:
                    check = await asyncio.to_thread(verify_speech, config["speech_directory"])
                    if not check:
                        raise VoiceError("SPEECH_NOT_READY", "Download and verify the local speech models in Settings.")
                values = await self.selected_secrets()
                if self.provider_epoch is not epoch:
                    raise asyncio.CancelledError()
                async def emit(event):
                    if self.provider_epoch is epoch:
                        await self.provider_event(event)
                async def audio_error():
                    await emit({"type": "error", "code": "AUDIO_FAILED",
                                "message": "Microphone audio stopped. Check the selected microphone and speakers, then start talking again."})
                transport = self.audio_transport_factory(microphone_device=config["microphone_device"],
                                                         speaker_device=config["speaker_device"], on_error=audio_error)
                async def submit(intent, turn_id):
                    if self.provider_epoch is not epoch:
                        raise VoiceError("TURN_ENDED", "This conversation has ended. Please repeat the request.")
                    return await self.submit_intent(intent, turn_id)
                provider = self.provider_factory(config, values, emit, submit, transport)
                self.provider = provider
                await provider.start(audio=audio)
                if self.provider_epoch is not epoch:
                    raise asyncio.CancelledError()
                self.session_started = self.last_activity = time.monotonic()
                model = config.get("gemini_live_model") if config["mode"] == "gemini_live" else config.get("realtime_model") if config["mode"] == "openai" else config.get("model", "")
                self.audit.record("session_started", session_id=self.session["id"], provider=config["mode"], model=model,
                                  elapsed_ms=round((self.session_started - connecting_started) * 1000))
                await self.publish()
            except BaseException:
                if epoch is not None and self.provider_epoch is epoch:
                    await self._stop_provider()
                raise
            finally:
                if self.startup_task is asyncio.current_task():
                    self.startup_task = None

    def _detach_provider(self):
        self.provider_epoch = None
        self.turns.clear()
        self.live_transcript.clear()
        self.live_delegations.clear()
        provider, self.provider = self.provider, None
        if provider is not None:
            self.audit.record("session_ended", session_id=self.session["id"], provider=self.settings.value["mode"],
                              elapsed_ms=round((time.monotonic() - self.session_started) * 1000))
        self.voice.update(enabled=False, state="disabled", microphone=False, speaking=False, level=0)
        if provider:
            self.provider_cleanup = self.background(self._release_provider(provider))
        return self.provider_cleanup

    async def _release_provider(self, provider):
        # A device shutdown failure must not skip the cloud/session teardown.
        transport = getattr(provider, "audio_transport", None)
        if transport:
            try:
                await asyncio.wait_for(transport.stop(), 2)
            except Exception:
                pass
        try:
            timeout = getattr(provider, "cleanup_timeout", 3)
            if type(timeout) not in {int, float} or timeout < 3 or timeout > 30:
                timeout = 3
            await asyncio.wait_for(provider.stop(), timeout)
        except Exception:
            # The epoch has already been revoked. A remote cleanup failure
            # cannot reactivate this conversation.
            pass

    async def _stop_provider(self):
        cleanup = self._detach_provider()
        await self._cancel_level_publish()
        if cleanup:
            await asyncio.shield(cleanup)

    async def end_voice(self, preserve_error=False):
        # Do not wait for lifecycle_lock: its owner may be connecting indefinitely.
        cleanup = self._detach_provider()
        await self._cancel_level_publish()
        current = asyncio.current_task()
        pending = set(self.conversation_requests)
        if self.startup_task:
            pending.add(self.startup_task)
        for task in pending:
            if task is not current and not task.done():
                task.cancel()
        self.voice.update(enabled=False, state="disabled", microphone=False, speaking=False, level=0)
        self.voice.pop("task_error", None)
        if not preserve_error:
            self.voice["error"] = ""
        self.session = {"id": str(uuid.uuid4()), "transcript": []}
        self.source, self.turn_id = "", ""
        await self.publish()
        if cleanup:
            await asyncio.shield(cleanup)

    async def check_readiness(self, discover=False):
        config = self.settings.value
        if config["mode"] in {"gpt_live", "gemini_live"}:
            conversation_checks, task_checks = [], []
            gemini = config["mode"] == "gemini_live"
            try:
                key = (await self.selected_secrets()).get("google" if gemini else "openai", "")
                account_message = "The account is saved in the desktop keyring. Start talking to test the real session." if key else "Connect the selected conversation account in Voice Settings."
            except VoiceError as error:
                key, account_message = "", error.message
            conversation_checks.append({"name": "Google AI Studio account" if gemini else "GPT-Live account", "ok": bool(key),
                                        "message": account_message})
            if gemini:
                try:
                    from livekit.plugins import google
                    dependency_ready = True
                except ImportError:
                    dependency_ready = False
                conversation_checks.append({"name": "Gemini runtime", "ok": dependency_ready,
                    "message": "Gemini native audio support is installed." if dependency_ready else "Repair Voice through Hub to install Gemini support."})
            from .execution import ExecutionManager
            execution = self.execution or ExecutionManager(self.store, self.publish, settings=self.settings, credentials=self.credentials,
                                                            offline_runtime_factory=self.offline_runtime)
            agents = await execution.readiness({"mode": config["mode"]})
            agents["hermes"] = {"ready": await self.hermes_ready({"mode": config["mode"]}),
                                "message": "Install and configure Hermes through Hub for Hermes tasks."}
            coder = config["default_coder"]
            selected_ready = any(check["ready"] for check in agents.values()) if coder == "auto" else agents[coder]["ready"]
            task_checks.append({"name": "Task agent", "ok": selected_ready,
                "message": "An agent is configured; authentication and permissions are checked at task start." if selected_ready else "Set up the selected task agent through Hub. Conversation is available independently."})
            conversation_ready = all(check["ok"] for check in conversation_checks)
            tasks_ready = all(check["ok"] for check in task_checks)
            self.readiness = {"ready": conversation_ready, "checks": conversation_checks + task_checks, "models": [],
                              "conversation": {"ready": conversation_ready, "checks": conversation_checks},
                              "tasks": {"ready": tasks_ready, "checks": task_checks}}
            await self.publish()
            return {"readiness": self.readiness}
        checks, models = [], []
        testing_new_workspace = config["mode"] == "offline" and self.offline is None and not self.provider and not self.store.active()
        def add(name, ok, message):
            checks.append({"name": name, "ok": bool(ok), "message": message})
        add("Hermes coordinator", shutil.which("hermes"), "Install and configure Hermes through Hub for task handoff.")
        try:
            if config["mode"] == "offline":
                if discover:
                    from .models import discover_downloaded_ollama
                    models = await asyncio.to_thread(discover_downloaded_ollama, config["ollama_models"])
                    self.readiness = {"ready": False, "checks": [{"name": "Downloaded models", "ok": bool(models),
                        "message": "Choose a downloaded model, then test the isolated connection."}], "models": models}
                    await self.publish()
                    return {"readiness": self.readiness}
                runtime = await self.offline_runtime(self.project or None)
                data = await runtime.model_request("/api/tags")
                models = [{"id": entry["name"], "label": entry["name"]} for entry in data.get("models", [])]
                add("Isolated workspace", True, "The model runtime is inside its private network and filesystem boundary.")
                add("Selected model", config["model"] in [model["id"] for model in models], "Choose a model already downloaded in Ollama.")
            elif config["mode"] == "server":
                token = (await self.selected_secrets()).get("server_token", "")
                models = await discover_models(config, token)
                if not discover:
                    await test_model(config, token)
                add("Your model server", True, "The configured server responded.")
            else:
                values = await self.selected_secrets()
                add("Account credentials", all(values.values()), "Credentials are saved in the desktop keyring. Use Talk to test a real session.")
                if config["mode"] == "livekit":
                    add("LiveKit project", bool(config["livekit_url"]), "Enter your project's secure LiveKit URL.")
            if config["mode"] in {"offline", "server"}:
                check = await asyncio.to_thread(verify_speech, config["speech_directory"] or self.directory / "speech")
                add("Local speech", check and Path("/usr/lib/maslow-voice-local/piper").is_file(), "Speech models must be installed and verified; local speech support must be installed.")
        except VoiceError as error:
            add("Connection", False, error.message)
        except Exception:
            add("Connection", False, "The selected Voice runtime needs setup. No fallback was used.")
        finally:
            if testing_new_workspace and self.offline and not self.provider and not self.store.active():
                await self.offline.stop()
                self.offline = None
                self.offline_clients.clear()
        task_checks = [check for check in checks if check["name"] == "Hermes coordinator"]
        conversation_checks = [check for check in checks if check not in task_checks]
        conversation_ready = bool(conversation_checks) and all(check["ok"] for check in conversation_checks)
        self.readiness = {"ready": conversation_ready, "checks": checks, "models": models,
                          "conversation": {"ready": conversation_ready, "checks": conversation_checks},
                          "tasks": {"ready": bool(task_checks) and all(check["ok"] for check in task_checks), "checks": task_checks}}
        await self.publish()
        return {"readiness": self.readiness}

    async def dispatch(self, request):
        if request.get("action") in {"configure", "configure_livekit", "configure_gemini_live", "credential"}:
            async with self.configuration_lock:
                return await self._dispatch(request)
        if request.get("action") not in {"start_voice", "submit_text"}:
            return await self._dispatch(request)
        current = asyncio.current_task()
        self.conversation_requests.add(current)
        try:
            return await self._dispatch(request)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if isinstance(error, VoiceError) and error.code in {"INVALID_REQUEST", "INVALID_BRIEF", "PROJECT_REQUIRED", "SESSION_PROJECT_FIXED", "SESSION_CONTEXT_FIXED"}:
                raise
            self.voice["error"] = error.message if isinstance(error, VoiceError) else "Voice could not connect. Check its setup and try again."
            await self.end_voice(preserve_error=True)
            raise
        finally:
            self.conversation_requests.discard(current)

    async def _dispatch(self, request):
        action = request.get("action")
        allowed = {
            "status": set(), "configure": {"settings"}, "credential": {"name", "value"}, "test": set(), "models": set(),
            "configure_livekit": {"url", "api_key", "api_secret"},
            "configure_gemini_live": {"url", "api_key", "api_secret", "google_api_key"},
            "download_speech": set(), "start_voice": {"project", "context"}, "end_voice": set(), "mute": {"muted"},
            "silence": set(), "submit_text": {"text", "project", "context"},
            "task_action": {"id", "task_id", "operation", "text", "approval_id", "child_id", "review_id", "paths"},
        }
        if action not in allowed or set(request) - allowed[action] - {"action"}:
            raise VoiceError("INVALID_REQUEST", "That Voice action or field is not supported.")
        if action == "status":
            if not self.readiness.get("checks") and self.settings.value["mode"] in {"gemini_live", "gpt_live", "livekit", "openai"}:
                await self.check_readiness()
            return {"snapshot": self.snapshot()}
        if action in {"configure_livekit", "configure_gemini_live"}:
            return await self.configure_livekit(request, gemini=action == "configure_gemini_live")
        if action == "configure":
            changes = request.get("settings", {})
            if not isinstance(changes, dict):
                raise VoiceError("INVALID_SETTINGS", "Settings must be an object.")
            connection = set(changes) - {"reduced_motion", "fixed_position", "orb_position", "display", "retention_days", "idle_seconds"}
            if connection and self.store.active():
                raise VoiceError("TASKS_ACTIVE", "Finish or stop current tasks before changing their execution connection.")
            if connection:
                await self.end_voice()
                if self.offline:
                    await self.offline.stop()
                    self.offline = None
                    self.offline_clients.clear()
            self.settings.update(changes)
            self.readiness = {"ready": False, "checks": [], "models": []}
            if self.settings.value["mode"] in {"gemini_live", "gpt_live", "livekit", "openai"}:
                await self.check_readiness()
        elif action == "credential":
            await self.credentials.set(request.get("name"), request.get("value"))
            if self.settings.value["mode"] in {"gemini_live", "gpt_live", "livekit", "openai"}:
                await self.check_readiness()
        elif action in {"test", "models"}:
            return await self.check_readiness(discover=action == "models")
        elif action == "download_speech":
            if self.offline and self.offline.process:
                raise VoiceError("OFFLINE_ACTIVE", "Close the offline workspace before downloading model files.")
            target = self.settings.value["speech_directory"] or str(self.directory / "speech")
            await asyncio.to_thread(download_speech, target)
            return await self.check_readiness()
        elif action == "start_voice":
            await self.start_voice(project=request.get("project", ""), context=request.get("context", ""))
        elif action == "end_voice":
            await self.end_voice()
        elif action in {"mute", "silence"}:
            if self.provider:
                if action == "mute":
                    if type(request.get("muted")) is not bool:
                        raise VoiceError("INVALID_REQUEST", "Mute requires an on or off value.")
                    await self.provider.mute(request["muted"])
                else:
                    await self.provider.silence()
        elif action == "submit_text":
            text = text_field(request.get("text"), "message", 12000, True)
            async with self.turn_lock:
                if self.settings.value["mode"] == "gpt_live":
                    project = request.get("project", "")
                    if project:
                        path = Path(project).expanduser()
                        if not path.is_absolute() or not path.is_dir():
                            raise VoiceError("PROJECT_REQUIRED", "Choose an existing project folder.")
                        resolved = str(path.resolve())
                        if self.provider and self.project and resolved != self.project:
                            raise VoiceError("SESSION_PROJECT_FIXED", "End this conversation before choosing a different project.")
                        self.project = resolved
                    context = text_field(request.get("context", self.context), "context", 12000)
                    if self.provider and context != self.context:
                        raise VoiceError("SESSION_CONTEXT_FIXED", "End this conversation before changing its context.")
                    self.context = context
                    identity = uuid.uuid4().hex
                    self.session["transcript"] = [*self.session["transcript"], {"role": "user", "text": text}][-100:]
                    task, action = await self._prepare_live_task(
                        [{"role": "user", "text": text}], identity, session_id=self.session["id"], project=self.project,
                        context=self.context, preferred_coder=self.settings.value["default_coder"])
                    if self.provider:
                        provider, epoch = self.provider, self.provider_epoch
                        message = ("Maslow accepted the typed task locally. It remains active if audio stops." if action == "new"
                                   else "Maslow accepted the task cancellation." if action == "cancel"
                                   else "Maslow sent the correction to the active task.")
                        await self._append_live_context(provider, epoch, "thinking", message, None)
                        self.background(self._relay_live_task(provider, epoch, task["id"], None))
                    await self.publish()
                    return {"task": {"id": task["id"], "state": task["state"], "title": task["title"]}}
                if not self.provider:
                    await self.start_voice(audio=False, project=request.get("project", ""), context=request.get("context", ""))
                else:
                    if request.get("project"):
                        path = Path(request["project"]).expanduser()
                        if not path.is_absolute() or not path.is_dir():
                            raise VoiceError("PROJECT_REQUIRED", "Choose an existing project folder.")
                        resolved = str(path.resolve())
                        if self.project and resolved != self.project:
                            raise VoiceError("SESSION_PROJECT_FIXED", "End this conversation before choosing a different project.")
                        self.project = resolved
                        if (self.voice.get("task_error") or {}).get("code") == "PROJECT_REQUIRED":
                            self.voice.pop("task_error", None)
                    context = text_field(request.get("context", self.context), "context", 12000)
                    if context != self.context:
                        raise VoiceError("SESSION_CONTEXT_FIXED", "End this conversation before changing its context.")
                await self.provider.text(text, self.context)
        elif action == "task_action":
            if request.get("id") and request.get("task_id") and request["id"] != request["task_id"]:
                raise VoiceError("INVALID_REQUEST", "The task action has conflicting task identities.")
            task = self.store.get(request.get("id") or request.get("task_id"))
            operation = request.get("operation")
            approval = task.get("approval") or {}
            if operation in {"approve", "deny"} and approval.get("owner") == "child":
                await self.execution.handle(task, operation, {"approval_id": request.get("approval_id"), "child_id": approval.get("child_id")})
            elif operation in {"review", "export"}:
                if task["mode"] != "offline":
                    raise VoiceError("NOT_OFFLINE", "This task works directly in its selected project.")
                if self.store.active():
                    raise VoiceError("TASKS_ACTIVE", "Finish or stop tasks before reviewing the offline workspace.")
                await self.end_voice()
                if self.offline:
                    await self.offline.stop()
                else:
                    from .offline import OfflineRuntime
                    self.offline = OfflineRuntime(self.directory, self.settings.value)
                if not await asyncio.to_thread(self.offline.restore_workspace, task["project"]):
                    raise VoiceError("OFFLINE_WORKSPACE_MISSING", "Reopen this task's offline project to review its private files.")
                self.offline_clients.clear()
                if operation == "review":
                    review = await asyncio.to_thread(self.offline.workspace.review)
                    self.store.update(task["id"], export_review=review)
                else:
                    await asyncio.to_thread(self.offline.workspace.export, request.get("review_id"), request.get("paths"))
                    self.store.update(task["id"], export_review=await asyncio.to_thread(self.offline.workspace.review))
            else:
                await self.tasks.action(task["id"], operation, request.get("text", ""), request.get("approval_id"))
        await self.publish()
        return {}

    async def configure_livekit(self, request, *, gemini=False):
        """Save Google and/or Expressive setup, retaining blank account fields."""
        if self.store.active():
            raise VoiceError("TASKS_ACTIVE", "Finish or stop current tasks before changing their execution connection.")
        url = request.get("url", "" if gemini else None)
        if not isinstance(url, str) or (not gemini and not url.strip()):
            raise VoiceError("INVALID_ENDPOINT", "Enter your LiveKit project URL.")
        livekit = {"livekit_key": request.get("api_key", ""), "livekit_secret": request.get("api_secret", "")}
        if not all(isinstance(value, str) for value in livekit.values()):
            raise VoiceError("INVALID_CREDENTIAL", "Enter an account credential or leave it blank to keep the saved value.")
        # An untouched optional Expressive setup is independent of Google.
        # Do not even read its keyring entries when all three fields are blank.
        configure_project = not gemini or bool(url.strip() or any(value.strip() for value in livekit.values()))
        changes = {"mode": "gemini_live" if gemini else "livekit"}
        supplied = dict(livekit) if configure_project else {}
        if configure_project:
            project_url = url.strip() or self.settings.value["livekit_url"]
            if not project_url:
                raise VoiceError("LIVEKIT_SETUP_INCOMPLETE", "Complete the optional LiveKit URL, API key and API secret, or leave all three blank.")
            changes["livekit_url"] = project_url
        validate_settings(dict(self.settings.value, **changes))
        if gemini:
            supplied["google"] = request.get("google_api_key", "")
        for value in supplied.values():
            if not isinstance(value, str):
                raise VoiceError("INVALID_CREDENTIAL", "Enter an account credential or leave it blank to keep the saved value.")
            if value.strip():
                Credentials.validate_value(value)
        previous = {name: await self.credentials.get(name) for name in supplied}
        values = {name: value.strip() or previous[name] for name, value in supplied.items()}
        if gemini and not values["google"]:
            raise VoiceError("GEMINI_SETUP_INCOMPLETE", "Enter the Google AI Studio API key, or leave it blank to retain a saved key.")
        if configure_project and not all(values[name] for name in livekit):
            raise VoiceError("LIVEKIT_SETUP_INCOMPLETE", "Complete the LiveKit API key and API secret. Blank fields only keep credentials already saved.")
        # Validate all fields before interrupting the current conversation.
        await self.end_voice()
        async with self.lifecycle_lock:
            if self.store.active():
                raise VoiceError("TASKS_ACTIVE", "Finish or stop current tasks before changing their execution connection.")
            if self.provider:
                await self.end_voice()
            if self.offline:
                await self.offline.stop()
                self.offline = None
                self.offline_clients.clear()
            attempted = []
            try:
                for name, value in values.items():
                    if value != previous[name]:
                        attempted.append(name)
                        await self.credentials.set(name, value)
                self.settings.update(changes)
            except BaseException:
                async def restore():
                    failed = False
                    for name in reversed(attempted):
                        try:
                            if previous[name]:
                                await self.credentials.set(name, previous[name])
                            else:
                                await self.credentials.delete(name)
                            if await self.credentials.get(name) != previous[name]:
                                failed = True
                        except Exception:
                            failed = True
                    if failed:
                        raise VoiceError("GEMINI_RESTORE_FAILED" if gemini else "LIVEKIT_RESTORE_FAILED",
                                         "Voice setup was not saved completely. Unlock the desktop keyring and save the requested account setup again.")
                await asyncio.shield(restore())
                raise
            self.readiness = {"ready": False, "checks": [], "models": []}
        await self.check_readiness()
        return {"gemini_live_saved" if gemini else "livekit_saved": True}

    async def tool_request(self, request):
        if not isinstance(request, dict) or set(request) - {"operation", "params", "session_id", "token"}:
            raise VoiceError("INVALID_TOOL", "The coordinator tool request is invalid.")
        if not secrets.compare_digest(str(request.get("token", "")), self.tool_token):
            raise VoiceError("UNAUTHORIZED_TOOL", "The coordinator bridge is not authorized.")
        task = self.store.get(request.get("session_id"))
        if task["state"] in TERMINAL or task["state"] in {"stopping", "queued"}:
            raise VoiceError("TASK_NOT_RUNNING", "The owning task is not running.")
        operation = request.get("operation")
        if operation not in {"delegate_coding", "open_application", "open_website"}:
            raise VoiceError("INVALID_TOOL", "That coordinator tool is not available.")
        return await self.execution.handle(task, operation, request.get("params", {}))

    async def _tool_connection(self, reader, writer):
        try:
            if not peer_is_owner(writer):
                return
            line = await asyncio.wait_for(reader.readline(), 10)
            if len(line) > MAX_REQUEST:
                raise VoiceError("INVALID_TOOL", "The coordinator tool request is too large.")
            result = await self.tool_request(json.loads(line))
            await ControlServer.send(writer, {"ok": True, "result": result})
        except VoiceError as error:
            await ControlServer.send(writer, {"ok": False, "error": error.as_dict()})
        except (ValueError, OSError, TimeoutError):
            pass
        finally:
            writer.close()

    def session_expired(self, now=None):
        now = time.monotonic() if now is None else now
        return (now - self.session_started >= 30 * 60
                or (not self.voice["speaking"] and now - self.last_activity > self.settings.value["idle_seconds"]))

    async def maintenance(self):
        while True:
            await asyncio.sleep(2)
            if self.provider and self.session_expired():
                await self.end_voice()
            if self.provider:
                process = await asyncio.create_subprocess_exec("omarchy-shell", "lock", "status",
                                                               stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                try:
                    output, _ = await asyncio.wait_for(process.communicate(), 2)
                    status = json.loads(output) if process.returncode == 0 else {}
                    if status.get("requested") or status.get("secure"):
                        await self.end_voice()
                except (TimeoutError, ValueError):
                    if process.returncode is None:
                        process.kill()
                        await process.wait()

    async def run(self):
        from .execution import ExecutionManager
        from .routing import AgentRouter
        self.execution = ExecutionManager(self.store, self.publish, settings=self.settings, credentials=self.credentials,
                                           offline_runtime_factory=self.offline_runtime)
        self.agent_router = AgentRouter(self.execution, self.executor_client, settings=self.settings, hermes_readiness=self.hermes_ready)
        self.tasks.client_factory = self.agent_router.client
        self.tasks.agent_selector = self.agent_router.select_agent
        self.tasks.children = self.execution
        lock = open(self.runtime / "service.lock", "a")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise VoiceError("ALREADY_RUNNING", "Voice is already running in this desktop session.") from None
        await self.control.start()
        remove_stale_socket(self.tool_socket)
        self.tool_server = await asyncio.start_unix_server(self._tool_connection, str(self.tool_socket), limit=MAX_REQUEST + 1)
        self.tool_socket.chmod(0o600)
        await self.tasks.recover()
        self.background(self.maintenance())
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        try:
            await stop.wait()
        finally:
            await self.end_voice()
            await self.tasks.close()
            for task in tuple(self.work):
                task.cancel()
            await asyncio.gather(*self.work, return_exceptions=True)
            if self.offline:
                await self.offline.stop()
            self.tool_server.close()
            await self.tool_server.wait_closed()
            await self.control.close()
            self.tool_socket.unlink(missing_ok=True)
            self.store.close()
            lock.close()


def main():
    try:
        asyncio.run(VoiceService().run())
    except VoiceError as error:
        print(json.dumps({"ok": False, "error": error.as_dict()}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
