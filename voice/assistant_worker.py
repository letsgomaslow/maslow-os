"""Small compatibility boundary around the separately packaged Hermes Runs API.

This executes only with Hermes' private interpreter. Fail closed on upstream
changes to the actual agent tool list. Never load project instructions/skills.
"""

import ctypes
import json
import os
import signal
import sys
from pathlib import Path

TOOLS = {"maslow_list_documents", "maslow_read_document", "maslow_create_note"}


def install_boundary():
    root = "/opt/hermes-agent/app" if Path("/opt/hermes-agent/app").is_dir() else "/opt/hermes-agent"
    sys.path.insert(0, root)
    import run_agent
    original = run_agent.AIAgent

    class ManagedAgent(original):
        def __init__(self, *args, **kwargs):
            if args:
                raise RuntimeError("Managed assistant requires the reviewed keyword API")
            kwargs.update(enabled_toolsets=["maslow_assistant"], skip_context_files=True, load_soul_identity=False,
                skip_memory=True, skip_background_review=True, fallback_model=None,
                max_iterations=12, max_tokens=2048, run_budget_seconds=180, verbose_logging=False, save_trajectories=False)
            super().__init__(**kwargs)
            expected = TOOLS | ({"maslow_read_calendar"} if os.environ.get("MASLOW_ASSISTANT_ACCOUNTS") == "1" else set())
            if set(self.valid_tool_names) != expected:
                raise RuntimeError("Managed assistant tool compatibility gate failed: " + json.dumps(sorted(self.valid_tool_names)))

    run_agent.AIAgent = ManagedAgent
    return ManagedAgent


def main():
    # The service owns this child's lifetime even across a crash/restart. Set
    # parent-death handling before imports and check the original parent again.
    parent = int(os.environ["MASLOW_ASSISTANT_PARENT"])
    if ctypes.CDLL(None).prctl(1, signal.SIGTERM, 0, 0, 0) != 0 or os.getppid() != parent:
        raise SystemExit(1)
    agent_class = install_boundary()
    if sys.argv[1:] == ["--probe"]:
        from hermes_cli.plugins import get_plugin_manager
        get_plugin_manager().discover_and_load()
        agent = agent_class(model="openai/gpt-oss-120b", provider="custom", base_url="http://127.0.0.1:18573/v1",
            api_key="local-probe-only", quiet_mode=True, platform="api_server")
        print(json.dumps({"tools": sorted(agent.valid_tool_names), "skip_context_files": agent.skip_context_files,
            "memory_store": getattr(agent, "_memory_store", None) is not None,
            "memory_manager": getattr(agent, "_memory_manager", None) is not None}))
        return
    if sys.argv[1:]:
        raise SystemExit(1)
    from hermes_cli.main import main as hermes_main
    sys.argv = ["hermes", "gateway", "run"]
    hermes_main()


if __name__ == "__main__":
    main()
