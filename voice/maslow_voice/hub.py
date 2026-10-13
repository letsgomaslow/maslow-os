"""Bounded, cached Hub view of the existing Voice service. No provider probes."""

import asyncio
import math
import re

from .errors import VoiceError
from .store import STATES
from .voice_preview import VOICES as GEMINI_VOICES
from .voices import LIVEKIT_VOICES, LIVE_VOICES, OPENAI_VOICES

SETTINGS = {
    "mode", "execution_connection", "default_coder", "task_policy",
    "gemini_live_model", "gemini_live_voice", "realtime_model", "realtime_voice",
    "live_voice", "livekit_voice", "server_kind", "server_url", "livekit_url",
    "model", "execution_model", "reduced_motion", "fixed_position", "idle_seconds", "retention_days",
}
VOICE_STATES = {"disabled", "idle", "connecting", "listening", "thinking", "working", "speaking", "paused", "error"}
IDENTITY = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
# Labels are user-controlled. Strip common credentials and endpoint/private path
# material; full requests, transcripts, results and errors never enter this view.
SENSITIVE = re.compile(
    r"(?i)(?:\b(?:api[_ -]?key|api[_ -]?secret|token|password|secret|authorization)\b\s*[:=]\s*\S+"
    r"|\bbearer\s+\S+|\b(?:sk|gsk|ghp|github_pat)[_-][A-Za-z0-9_-]+"
    r"|\bAIza[A-Za-z0-9_-]+|https?://\S+|wss?://\S+|(?:/|~\/)[^\s]+"
    r"|[A-Za-z0-9_+/=-]{40,})")


def label(value):
    if not isinstance(value, str):
        return "Saved task"
    value = SENSITIVE.sub("[private]", value[:1000])
    return " ".join("".join(c for c in value if ord(c) >= 32 and ord(c) != 127).split())[:160] or "Saved task"


def task_summary(task):
    identity = task.get("id")
    if not isinstance(identity, str) or not IDENTITY.fullmatch(identity):
        return None
    updated = task.get("updated_at")
    updated = updated if type(updated) in {int, float} and math.isfinite(updated) and updated >= 0 else None
    state = task.get("state")
    connection = task.get("execution_connection")
    return {"id": identity, "label": label(task.get("title")),
            "connection": connection if isinstance(connection, str) and connection in {"existing", "free-cloud"} else "unknown",
            "status": state if isinstance(state, str) and state in STATES else "unknown", "updatedAt": updated,
            "handoff": {"kind": "voice-task", "taskId": identity}}


def snapshot(service):
    readiness = service.readiness if isinstance(service.readiness, dict) else {}
    conversation = readiness.get("conversation") or {}
    tasks = readiness.get("tasks") or {}
    current = asyncio.current_task()
    pending = any(task is not current for task in service.control_requests)
    session_active = bool(service.provider or service.voice.get("enabled") or service.startup_task
                          or service.conversation_requests or service.preview_task
                          or (service.reconnect_task and not service.reconnect_task.done())
                          or (service.provider_cleanup and not service.provider_cleanup.done())
                          or service.lifecycle_lock.locked())
    # Match the existing delivery boundary's active-work predicates while
    # excluding this read/configure request and its own configuration lock.
    active_tasks = service.store.active()
    tasks_active = bool(active_tasks or service.tasks.assistant_reservations
                        or any(not worker.done() for worker in service.tasks.monitors.values())
                        or service.agent_jobs or service.action_work or service.action_lock.locked()
                        or any(job.get("state") not in {"finished", "closed"} for job in service.jobs.values()))
    recent = {task["id"]: task for task in active_tasks if not task.get("dismissed")}
    for task in service.store.list(50):
        if len(recent) >= 50:
            break
        if not task.get("dismissed"):
            recent.setdefault(task["id"], task)
    summaries = [task_summary(task) for task in list(recent.values())[:50]]
    settings = {key: value for key, value in service.settings.value.items() if key in SETTINGS}
    # String preferences are display data only. A malicious/corrupt old setting
    # must not become a secret-bearing Hub payload.
    for key, value in tuple(settings.items()):
        if isinstance(value, str) and key not in {"server_url", "livekit_url"}:
            settings[key] = label(value) if value else ""
    for key in ("server_url", "livekit_url"):
        # URLs are edited in Voice's existing settings surface; expose only a
        # presence bit here, never account identifiers embedded in URL paths.
        settings.pop(key, None)
    state = service.voice.get("state")
    maintenance = bool(service.delivery.closed)
    return {"schemaVersion": 1, "running": True, "ready": not maintenance and readiness.get("ready") is True,
            "enabled": service.voice.get("enabled") is True,
            "state": "maintenance" if maintenance else state if isinstance(state, str) and state in VOICE_STATES else "unknown",
            "maintenance": maintenance,
            "capabilities": {"taskSummaries": True, "taskOpen": not maintenance, "typeOpen": not maintenance, "settings": not maintenance},
            "tasks": [task for task in summaries if task is not None], "settings": settings,
            "voices": {"gemini_live_voice": list(GEMINI_VOICES), "realtime_voice": list(OPENAI_VOICES),
                       "live_voice": list(LIVE_VOICES), "livekit_voice": list(LIVEKIT_VOICES)},
            "endpoints": {key: bool(service.settings.value.get(key)) for key in ("server_url", "livekit_url")},
            "readiness": {"ready": not maintenance and readiness.get("ready") is True,
                          "conversationReady": not maintenance and isinstance(conversation, dict) and conversation.get("ready") is True,
                          "tasksReady": not maintenance and isinstance(tasks, dict) and tasks.get("ready") is True,
                          "checked": bool(readiness.get("checks"))},
            "sessionActive": session_active, "tasksActive": tasks_active,
            "canConfigure": not session_active and not tasks_active and not pending and not service.hub_configuring and not service.delivery.closed}


def configuration(request):
    if not isinstance(request, dict):
        raise VoiceError("INVALID_REQUEST", "Send one supported Voice settings request.")
    fields = {"configure": {"settings"}, "configure_livekit": {"url", "api_key", "api_secret"},
              "configure_gemini_live": {"url", "api_key", "api_secret", "google_api_key"},
              "credential": {"name", "value"}}
    action = request.get("action")
    if not isinstance(action, str) or action not in fields or set(request) - fields[action] - {"action"}:
        raise VoiceError("INVALID_REQUEST", "This Voice settings action is unavailable in Hub.")
    if action == "configure":
        settings = request.get("settings")
        if not isinstance(settings, dict) or not settings or set(settings) - SETTINGS:
            raise VoiceError("INVALID_SETTINGS", "Choose supported Voice settings.")
        if "gemini_live_voice" in settings and settings["gemini_live_voice"] not in GEMINI_VOICES:
            raise VoiceError("INVALID_SETTINGS", "Choose one of the supported Gemini voices.")
    elif action == "credential":
        if request.get("name") not in {"google", "openai", "anthropic", "server_token"} or not isinstance(request.get("value"), str):
            raise VoiceError("INVALID_CREDENTIAL", "Choose a supported Voice account credential.")
    return request
