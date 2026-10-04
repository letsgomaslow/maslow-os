# Voice websites, visible Codex terminal and action captions

Date: 2026-10-03. Goal: make Maslow Voice useful beyond conversation while keeping the design simple. Voice now opens websites, talks to a Codex session the person can watch, names each action on the orb before it runs, and can hand web tasks to an agent-driven visible browser. Source is committed on local branch `voice-agent-terminal` in `maslow-os` and in `maslow-os-pkgs`. Nothing is pushed, merged, packaged, installed or published.

## Commits

- `maslow-os` (`voice-agent-terminal`, from `main` at `85ef7ea2`):
  - `adafbe63`: websites and action captions.
  - `f25ade72`: visible tmux-backed Codex and `tell_agent`.
  - `e2b092bd`: opt-in browser-agent setup.
  - A documentation commit records this handoff and the fixture hook.
- `maslow-os-pkgs` (`voice-agent-terminal`, from `maslow` at `4488564`):
  - `3b690c9`: adds `tmux` to `maslow-voice` depends and advances the recipe to `0.1.5-20`. No package was built.

## What changed

- **Websites:** `desktop_action` accepts an optional `url` for Browser.
  - `validate_url` checks it, and it always goes through `omarchy-launch-browser <url>`.
  - The model writes searches as DuckDuckGo search URLs.
- **Captions:** before a desktop or agent action, the daemon publishes `voice.action_caption`, composed from validated fields.
  - The status pill shows it after errors and pause, elides long text, and clears it four seconds after the latest caption.
- **Visible Codex:** "Open Codex" runs `tmux -L maslow-voice new-session -A -s maslow-codex -c ~/Projects/Maslow Voice -- codex` inside the `maslow.voice.codex` terminal.
  - The terminal creates the session, so Codex gets the desktop environment.
  - The session ends when Codex exits, so text never reaches a shell.
  - No approval or bypass flags are added.
- **`tell_agent`:**
  - Opens or focuses the window first.
  - Requires the pane's foreground command to be `codex`.
  - Holds words while a decision is on screen and returns `needs_answer` with the prompt.
  - Otherwise types literally with `send-keys -l`, waits 0.25 seconds, then sends Enter.
  - `reply` approve sends `y` and deny sends `Escape`, only while a decision is shown.
  - Per-turn receipts prevent duplicate typing.
- **Prompt text:** the markers come from strings in the installed Codex 0.157.1 binary:
  - "Would you like to …"
  - "Trust this folder?"
  - "Yes, provide the requested info"
  - The `y`/`Escape` key bindings were not observed in a live session.
- **`omarchy setup voice browser`:** after confirmation, it registers pinned `@playwright/mcp@0.0.83` with Codex, and with Claude Code if installed. It is idempotent through `mcp get`.
- **Docs:** `voice/docs/execution.md` and `docs/maslow-voice.md` now describe the narrowed approval boundary and the user-facing commands.

## Checks

- Pinned Voice suite (`bash test/shell.d/voice-test.sh`) passed: 384 unit tests run (two expected skips), plus the UI and orb contracts.
  - New coverage in `voice/tests/test_agent_terminal.py` and additions to the desktop, service and Gemini tool tests.
- `node voice/tests/ui-controller-test.mjs`, `bash test/shell.d/voice-launch-test.sh` and `./test/cli` passed.
- `bash -n` passed on the new command and the recipe; `git diff --check` was clean.
- Real tmux 3.7c on a throwaway server confirmed the exact argv shape:
  - literal delivery of `$(...)`, `C-c` and `Enter` words;
  - the pane state format;
  - no session remaining after the server ends.
- Native caption render: `voice/tests/ui-preview.qml` (new `caption` IPC) ran on the live Hyprland layer-shell with the Canvas fallback at 88 px. The inspected PNGs showed:
  - a short caption;
  - an elided 80-character caption;
  - paused winning over a caption;
  - the cleared state.
  - The GPU shader path and the 56 px orb size were not rendered.
- The full `./test/all` aggregate was not rerun. The runtime-smoke lockscreen failure from the merge handoff remains unresolved and is unrelated to these files.

## Not verified

- No live Gemini conversation called the new tools.
- No real Codex session received typed text or approval keys.
- The paste-burst delay and the approve key `y` need confirming in a live Codex session.
- Prompt detection reads the screen, so a Codex TUI change can break the markers. A missed marker means words could land on a decision screen.
- Claude Code is deliberately not reachable through `tell_agent` until its prompt text ("Do you want to proceed?", "Yes, I trust this folder") and keys are confirmed.
- Playwright MCP was not run, and the headed browser from the tmux-started agent is unverified.
- Package build, install and rollback were not done.

## Next action

With authorization, build and locally install `maslow-voice 0.1.5-20` from these branches. Then on the Lenovo:

1. Say "go to github.com" and "search for tmux".
2. Say "open Codex", close the window, and say "open Codex" again.
3. Say "tell Codex to list the files here", and confirm it submits once.
4. Make Codex ask for approval, then say "approve"; repeat and say "deny".
5. Run `omarchy setup voice browser`, then ask Codex for a web task.

Record the exact prompt text and keys observed.
