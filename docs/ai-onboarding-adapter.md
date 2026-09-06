# AI onboarding runtime adapter contract

`omarchy-setup-ai-tool` is the non-persistent runtime boundary for the Maslow AI onboarding UI. It reports sanitized capability, installation ownership, provider authentication status, and an explicit bounded Hermes operational check. It never reads credential files, returns provider output, stores proof, or changes the progress-only choices owned by `omarchy-setup-ai-state`.

## Actions

- `catalog` keeps schema 1 and lists the existing setup tools plus `hermes-desktop` and `chatgpt-desktop`.
- `status TOOL_ID` keeps every existing schema 1 key: `schemaVersion`, `id`, `name`, `supported`, `planned`, `available`, `installed`, `prerequisiteInstalled`, `setupOnly`, `userConfirmable`, and `authentication`, with optional `reason` and `reasonCode`. It adds `runtimeOwner` and `runtimeState` for every tool, `desktopInstalled` for desktop tools and Hermes, and `checkAvailable` for Hermes.
- `install TOOL_ID` keeps the existing action and delegates to existing visible installers. Core terminal tools use `omarchy-agent-install`; desktop tools use `omarchy-install-ai-hermes` or `omarchy-install-ai-chatgpt`. The adapter never removes software or runs an installation/package-mutation process in its cancellable status worker.
- `open TOOL_ID` keeps the existing compatibility action. Codex and Claude Code open their official login flows. Desktop tools open their existing desktop launchers. Memory and MCP cards continue to open the official Hermes wizards and require user confirmation.
- `launch TOOL_ID` opens the normal interactive Codex, Claude Code, or Hermes client without automatic approval flags. It does not imply sign-in or readiness. Other tool IDs are rejected.
- `check hermes` is the only operational-check command. It accepts no provider or model argument. For the shipped Hermes version it returns the unavailable result described below without starting Hermes.

No other `check` target is accepted. Provider selection remains in Hermes' own guided flow so the adapter cannot choose a paid provider, enable fallback, or claim that the configured provider is the user's preferred provider or the coding account chosen in onboarding. The UI must disclose that this checks Hermes' currently configured provider.

## Sanitized status fields

`authentication` is one of `signed-in`, `signed-out`, or `unknown`.

- Codex uses only `codex login status`. Packaged Codex tag `rust-v0.152.0`, commit `316795b3cf2a45e90d121d9f46499d4658b2645c`, writes every recognized successful status to stderr and exits zero; it writes exactly `Not logged in` to stderr and exits 1 for signed-out ([`codex-rs/cli/src/login.rs` lines 443-505](https://github.com/openai/codex/blob/316795b3cf2a45e90d121d9f46499d4658b2645c/codex-rs/cli/src/login.rs#L443-L505)). Its own ChatGPT-auth test also asserts the success message on stderr ([`codex-rs/cli/tests/cloud_auth.rs` lines 48-53](https://github.com/openai/codex/blob/316795b3cf2a45e90d121d9f46499d4658b2645c/codex-rs/cli/tests/cloud_auth.rs#L48-L53)). The adapter requires stdout to be empty and accepts only those exact exit/status combinations, including only the source-defined API-key redaction shapes ([`codex-rs/cli/src/login.rs` lines 579-585](https://github.com/openai/codex/blob/316795b3cf2a45e90d121d9f46499d4658b2645c/codex-rs/cli/src/login.rs#L579-L585)). Exit 1 with any error line, any other exit code, timeout, signal, missing command, wrong stream, or unrecognized output is `unknown`. It recognizes status text only to classify it and never returns it.
- Claude Code uses only `claude auth status --json`. Packaged Claude Code 2.1.252 returns an object with required boolean `loggedIn` plus `authMethod`, `apiProvider`, `analyticsDisabled`, and `projectsDirectory`; depending on the auth mode it may also include `forcedLoginMethod`, `apiKeySource`, `email`, `orgId`, `orgName`, and `subscriptionType`. The adapter reads only `loggedIn`. Missing or non-boolean `loggedIn`, malformed JSON, extra top-level output, timeout, signal, missing command, or nonzero exit is `unknown`.
- Other tools report `unknown`. Hermes operational response and desktop presence never imply provider authentication.

Authentication is credential status reported by the provider CLI. It is distinct from operational inference: the adapter does not send a live prompt to infer Codex or Claude sign-in and does not inspect token, API-key, account, subscription, or configuration files. Raw command stdout and stderr are discarded after parsing and never appear in adapter JSON or errors.

The whole read-only `status` action runs in one process group. Provider and capability probes have a five-second default deadline; the test-only seconds override accepts a positive integer or decimal and is clamped to eight seconds. The outer status supervisor adds one second for sanitized JSON assembly, so its maximum deadline is nine seconds. Probe timeout preserves discovered ownership and reports `authentication: "unknown"`; whole-worker timeout, cancellation, or malformed worker output fails closed to sanitized `reasonCode: "status-unavailable"` state. After the worker exits, the supervisor terminates any remaining member of its process group; installation and package-mutation actions never run under this supervisor. Focused fixtures cover the pinned Codex stderr outcomes, Claude JSON outcomes, output limits, parent-exits-first descendants, and cancellation during Hermes Desktop capability help.

`runtimeOwner` is one of:

- `packaged`: the command resolves to the executable owned by the Maslow package.
- `desktop`: Hermes Desktop owns the Hermes lifecycle. `runtimeState` separately reports whether its managed runtime is preparing, ready, or needs attention.
- `foreign`: a command exists but is not the package-owned executable or verified Hermes Desktop runtime.
- `none`: no command is present.

`runtimeState` is one of `none`, `preparing`, `ready`, or `attention`. `installed` remains true only for a ready owning runtime on terminal-tool cards. A foreign PATH command is reported with `runtimeOwner: "foreign"`, `runtimeState: "attention"`, `installed: false`, and `reasonCode: "path-shadow"`; status never exposes the path. After Hermes Desktop takes over, the desktop runtime must resolve as `runtimeOwner: "desktop"`, `runtimeState: "ready"`, and `installed: true` rather than remaining a generic foreign override.

The desktop IDs report package/app state directly with `desktopInstalled`. `installed` has the same value on a desktop card for compatibility with existing card behavior. `hermes-desktop` uses the `hermes-desktop` package and launcher; `chatgpt-desktop` uses `openai-codex-desktop` and its launcher. Desktop sign-in remains `unknown`. An installed desktop stays installed and openable when its repository is currently unavailable; `available` remains false so only a new install is gated.

Hermes Desktop states are exact and sanitized:

- Package absent: `desktopInstalled: false`, `runtimeOwner: "none"`, `runtimeState: "none"`.
- Package and launcher present, bootstrap marker and runtime command absent: `desktopInstalled: true`, `runtimeOwner: "desktop"`, `runtimeState: "attention"`, `reasonCode: "desktop-setup-required"`. Missing artifacts do not prove active preparation. The shipped desktop exposes no supported active-bootstrap status, so this adapter does not emit `preparing` based on their absence.
- Bootstrap marker present and its Hermes command is the resolved runnable command with the pinned noninteractive capability: `desktopInstalled: true`, `runtimeOwner: "desktop"`, `runtimeState: "ready"`.
- Package metadata, launcher, bootstrap marker, resolved command, or capability disagree: `desktopInstalled: true`, `runtimeOwner: "desktop"`, `runtimeState: "attention"`, with a sanitized reason code.

ChatGPT Desktop has no separately managed terminal runtime. Package plus executable launcher reports `desktopInstalled: true`, `runtimeOwner: "desktop"`, and `runtimeState: "ready"`; a partial package/launcher state reports `runtimeState: "attention"`; absence reports `runtimeOwner: "none"` and `runtimeState: "none"`.

`open hermes-desktop` remains available whenever the desktop package and its executable launcher exist, including `attention`, so the user can finish or retry setup. It invokes that fixed packaged launcher, never a foreign Hermes CLI. Bootstrap logs are not read: failed, retry, stale, unknown, and oversized log contents cannot establish active preparation or override a verified ready runtime. No bootstrap error text is returned.

## Hermes operational check

The packaged tag `v2026.8.31` is annotated object `6e8f8418e6378eb2617e4de074e13dedd091b8af`, peeled source commit `29112bef099274229cadff79cdff7bf7b99c4b77`. Its parser exposes `-z/--oneshot` and `--toolsets` and states that one-shot approvals are auto-bypassed ([`hermes_cli/_parser.py` lines 150-217](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/hermes_cli/_parser.py#L150-L217)). The one-shot implementation then sets `HERMES_YOLO_MODE=1` and `HERMES_ACCEPT_HOOKS=1` unconditionally ([`hermes_cli/oneshot.py` lines 253-256](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/hermes_cli/oneshot.py#L253-L256)) and loads the configured fallback chain into `fallback_model` ([`hermes_cli/oneshot.py` lines 487-504](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/hermes_cli/oneshot.py#L487-L504)). Those exact shipped paths do not provide the required operational-tool and fallback isolation. The adapter therefore reports `checkAvailable: false`, and `check hermes` returns sanitized `operational: "unavailable"` with `reasonCode: "check-unavailable"` without invoking Hermes. The UI should keep the guided launch path available and explain that the installed release cannot run the safety-constrained automatic check.

The shipped check result is:

```json
{"schemaVersion":1,"id":"hermes","operational":"unavailable","reasonCode":"check-unavailable"}
```

The shipped unavailable result exits nonzero without including raw output. No response-ready behavior is implemented for this pinned release.

## Persistence boundary

The adapter writes no state. `omarchy-setup-ai-state choice` may persist only the user's explicit progress choices: `account` as `codex|claude`, `hermes` as `recommended|deferred`, `memory` as `builtin|honcho|hindsight|deferred`, and `desktop` as `hermes-desktop|chatgpt-desktop|none`. Those values are navigation preferences and never proof of installation, authentication, ownership, configuration, or an operational response.

## First-login launch acknowledgement

`omarchy-setup-ai --first-login` gives its single shell summon a 60-second IPC acknowledgement budget after the existing completed/deferred skip gate. Cold native startup can accept the request before the shell replies; the ordinary two-second shell budget produced a false optional-setup failure in a clean automatic-only emulated installation even though the panel opened. The launcher does not retry or convert failures into success. Manual launch retains the caller/default shell timeout. This budget does not establish account readiness or guarantee a rendered panel; native window acceptance remains separate.
