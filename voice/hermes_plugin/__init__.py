"""Only loaded into the dedicated execution profile, never into the voice model."""

import json
import os
import socket


def _request(operation, params, context):
    # Hermes supplies session_id out of band. The model schema cannot set it.
    session_id = context.get("session_id")
    if not session_id:
        return json.dumps({"error": "The coordinator did not supply the task session."})
    request = {"operation": operation, "params": params, "session_id": session_id,
               "token": os.environ.get("MASLOW_VOICE_TOOL_TOKEN", "")}
    try:
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(3600)
            client.connect(os.environ["MASLOW_VOICE_TOOL_SOCKET"])
            client.sendall(json.dumps(request).encode() + b"\n")
            with client.makefile("rb") as stream:
                raw = stream.readline(1048577)
            if len(raw) > 1048576:
                return json.dumps({"error": "The task result exceeded the supported size."})
            return json.dumps(json.loads(raw))
    except (OSError, ValueError, KeyError):
        return json.dumps({"error": "The local task bridge is unavailable. Do not retry this action through a different tool."})


def register(ctx):
    schemas = {
        "maslow_delegate_coding": ("delegate_coding", "Delegate a coding deliverable to an eligible coding tool, preserving its permissions and returning the actual result.",
                                  {"tool": {"type": "string", "enum": ["codex", "claude", "auto"]}, "instructions": {"type": "string"}}, ["tool", "instructions"]),
        "maslow_open_application": ("open_application", "Open a supported installed application; offline applications stay inside the offline workspace.",
                                    {"application": {"type": "string"}}, ["application"]),
        "maslow_open_website": ("open_website", "Open the explicitly requested HTTP(S) website, or an offline localhost preview.",
                                {"url": {"type": "string"}}, ["url"]),
    }
    for name, (operation, description, properties, required) in schemas.items():
        schema = {"name": name, "description": description,
                  "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}}
        def handler(params, _operation=operation, **kwargs):
            return _request(_operation, params, kwargs)
        ctx.register_tool(name=name, toolset="maslow_voice", schema=schema, handler=handler)
