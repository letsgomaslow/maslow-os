# Voice websites, visible Codex terminal and action captions

Date: 2026-10-03. Goal: make Maslow Voice useful beyond conversation while keeping the design simple. Voice now opens websites, talks to a Codex session the person can watch, names each action on the orb before it runs, and can hand web tasks to an agent-driven visible browser. Source is committed on local branch `voice-agent-terminal` in `maslow-os` and in `maslow-os-pkgs`. Nothing is pushed, merged or published; `0.1.5-20` is installed locally on the Lenovo only.

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
  - The model writes searches as Google search URLs (DuckDuckGo was an early placeholder).
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

## Live Lenovo test (source checkout through the installed service)

The installed `maslow-voice 0.1.5-18` service ran the source checkout through a temporary runtime drop-in, `/run/user/1000/systemd/user/maslow-voice.service.d/source-test.conf`, which sets `PYTHONPATH` to `voice/`. No installed files changed; the installed orb UI was used, so captions were not visible.

- **First attempt failed.** Every Gemini session was refused at setup: `function_declarations[3].parameters.properties[reply].enum[0]: cannot be empty`.
  - The OpenAI-format schema test missed it.
  - Fixed in `24a27547`: "no answer" is now `none`, and a Google-format schema test rejects empty enum values.
- **Person-reported results:**
  - "go to github.com" and "search for tmux" worked.
  - "Open Codex" with the trust prompt answered worked.
  - "Tell Codex to list the files in this folder" was typed and submitted once.
  - Close and reopen reattached the same session.
- **Missing feature found:** closing windows. Added in `c0e9838f`, along with a per-action journal line.
- **Journal evidence (21:59–22:07 local):**
  - `desktop codex: opened`
  - `desktop codex close: closed`
  - `agent codex: sent`
  - `agent codex approve: answered`
  - `desktop codex close: closed`
- **Codex screen evidence:**
  - The sandbox blocked `curl -I example.com` ("Could not resolve host").
  - The spoken approval produced "You approved codex to run curl -I example.com this time", confirming `y` maps to the one-time option.
  - The rerun returned HTTP 200.
- **Open observations:**
  - "Close the browser" produced no action line.
  - Gemini rewrote the spoken request into a literal command instead of passing the words through.

## Claude Code, guidance fixes and local install

- **`18780937`:**
  - Adds Claude Code: session `maslow-claude`, class `maslow.voice.claude`, approve `1`, deny `Escape`.
  - Tells the model to pass the person's own words as plain-language instructions and to use `action close` for windows.
  - Holds typing only for dialog-specific text. Claude's generic "Do you want to…" counts only with a following `1. Yes` option, so ordinary questions in replies no longer block typing.
  - Pinned suite: 388 tests passed (two expected skips).
- **Build:** `maslow-voice 0.1.5-20` was built in the existing builder (`makepkg -d`, because only the runtime `tmux` dependency was absent there).
  - Frozen inputs: runtime `git archive` of `18780937` and recipe `3b690c9`.
  - `check()` passed. Archive SHA-256 `d178212b6b968c4eaf143fd4c66bda83e572edaf804b74d273fb8047a6fdb161`.
  - `.PKGINFO` lists `tmux`. Packaged `agent_terminal.py`, `desktop.py`, `daemon.py`, `gemini_tools.py` and `Panel.qml` match the frozen source.
- **Install:** installed locally with `pkexec pacman -U`.
  - The temporary source drop-in was then removed. The service runs `PYTHONPATH=/usr/lib/maslow-voice`.
  - `pacman -Qkk` reports zero altered files among 9123.
  - The queued plugin refresh was consumed by the packaged launcher, and the 0.1.5-20 Panel was inspected on screen.
  - Rollback archive: `voice-mvp-build/voice-theme/maslow-voice-0.1.5-18-x86_64.pkg.tar.zst`.
  - Build and install logs: `voice-mvp-build/voice-agent-terminal/`.

## Second live round and 0.1.5-21

- **Journal (22:23–22:27):**
  - Browser URL open and **browser close** worked.
  - Codex was sent the request and the spoken approve was answered.
  - Claude opened and the request was sent. Claude listed the files under its own "auto mode", which comes from the person's Claude settings, not from Voice flags.
  - **Gemini then issued `agent claude approve` one second later with no prompt on screen and no spoken answer.** The screen check refused it (`NO_PENDING_PROMPT`).
  - A 22:15 Gemini `1011 Internal error` came from the provider before the reinstall.
- **`b108ff29`:**
  - Switches spoken searches to Google.
  - Adds a daemon guard: approve or deny is accepted only when the person's own words in that turn say so, and negated approvals are refused.
  - Pinned suite: 389 tests passed (two expected skips).
- **Build and install:**
  - Recipe `3eeb83c` advances to `0.1.5-21`, built from a `git archive` of `b108ff29`.
  - Archive SHA-256 `deaff2a9041dd1c13dfb1c61507d1150dd02709dafe3862b483d81374f11df87`.
  - Installed with `pkexec`. Integrity reports 0 altered files among 9123. The plugin refreshed to `0.1.5-21/Panel.qml`.
  - Logs: `voice-mvp-build/voice-agent-terminal-21/`.

## Web tasks through Codex and Playwright (0.1.5-22)

Design decisions:
- Gemini stays the decision model; no separate router.
- Web tasks go to Codex with Playwright in a visible, isolated browser.
- Browsing steps are pre-approved, as the person chose.
- Personal context is to come from Maslow's central memory (Hermes built-in, Honcho or Hindsight); Voice keeps no copy, so `profile_context()` is an empty hook for now.

Live Codex 0.157.1 findings, observed directly through Voice's tmux session:

- **Built-in browser:** Codex's built-in computer and browser tool fails in the CLI with `CUA_REPL_ENABLED_SURFACES is required`. Playwright is therefore the path.
- **Headless until the display was forwarded:** Playwright ran without a window until `env_vars = ["WAYLAND_DISPLAY", "DISPLAY", "XDG_RUNTIME_DIR"]` was added. A visible "Example Domain – Google Chrome" window was then observed.
- **Approvals saved as permanent:** selecting "1. Allow" (Enter on the highlighted once-option) on an MCP tool dialog wrote `approval_mode = "approve"` to `~/.codex/config.toml`. The saved approvals were removed (backup in the session scratchpad). Voice now holds words on these dialogs and refuses spoken answers (`ANSWER_IN_WINDOW`).
- **Inconsistent tool choice:** without explicit tool names, Codex tried the computer tool, Node scripts and text web search. The web-task frame now names the playwright MCP tools.
- **Words left unsent in three cases:**
  - the transcript was scrolled, so Enter only returned to the latest messages;
  - Codex was starting, showing "tab to queue message";
  - long dictation, where Enter became a newline.
- **Window switched to Claude:** a session ending moved its window onto Claude's session, because of the person's `detach-on-destroy off`.
- **Fixed in `ccdea17b`:**
  - a private `tmux.conf`;
  - one bracketed paste with confirmed submission;
  - no key presses after a decision appears;
  - replacement of stale windows.
  - A long multi-clause message then submitted first time live.
- `5256bbac` adds web-task framing, the watcher, keeping the session open, spoken or notified results, `agent_status`, the isolated pre-approved setup and `voice/dev/route_eval.py`. Pinned suite: 400 tests passed (two expected skips).
- **Routing check** (`route_eval.py`, `gemini-flash-latest` standing in for Live): all 15 answered requests routed as expected, including the flight request as `tell_agent:web_task`, plus opens, closes and talk. The remaining 15 hit the key's quota (`429 RESOURCE_EXHAUSTED`) and are untested, not failed.
- **Package:** recipe `0ea9677` advances to `0.1.5-22`, built from a `git archive` of `5256bbac`.
  - Archive SHA-256 `b25770dc0fdce7b1531d1722963773112924aa065fa602137be1b4ed466e36a5`; includes `tmux.conf`.
  - Installed with `pkexec`: 0 altered files among 9124. The plugin refreshed to `0.1.5-22/Panel.qml`.
  - Voice's tmux server was restarted to load its configuration.
- **Setup command not yet installed:** the updated `omarchy-setup-voice-browser` belongs to the runtime package and is not installed. Run it from the source checkout. The current Codex entry is the earlier non-isolated server with display forwarding and no saved approvals.

## Not verified

- No live Gemini conversation called the new tools.
- No real Codex session received typed text or approval keys.
- The approve key `y` is now confirmed live. The 0.25-second Enter delay worked for short requests; long dictation is untested.
- Prompt detection reads the screen, so a Codex TUI change can break the markers. A missed marker means words could land on a decision screen.
- Claude Code's dialog text and keys (`1`, `Escape`) are taken from its binary and still need a live test.
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
