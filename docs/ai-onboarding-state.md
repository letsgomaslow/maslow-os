# AI onboarding state contract

`omarchy-setup-ai-state` is the persistence boundary for the Maslow AI setup panel. It stores progress only; it never stores credentials, tokens, vault contents, or provider configuration.

The command supports these JSON reads:

- `omarchy-setup-ai-state catalog` prints the ordered identity catalog. Capability and availability come only from `omarchy-setup-ai-tool catalog` and `status`.
- `omarchy-setup-ai-state show` prints the saved onboarding state without changing it.
- `omarchy-setup-ai-state open` records the first display time and prints the state.

Schema 2 stores one entry in `tools` for each catalog ID. A tool has `selected`, `status`, and `updatedAt` fields. Supported statuses are `not-started`, `selected`, `in-progress`, `action-required`, `ready`, `needs-attention`, and `skipped`.

The panel updates cards with `tool-select TOOL_ID true|false` and `tool-status TOOL_ID STATUS`. Those commands print nothing on success; read the resulting state with `show`. `ready` is historical onboarding progress, including explicit user confirmations from earlier versions. It is not durable proof of authentication or successful inference. The current panel must obtain fresh, sanitized runtime evidence from the adapter before presenting a connection as verified.

The existing `step`, `select`, `defer`, `complete`, and `reset` actions remain available to the current panel. A valid schema 1 file is converted in memory and written as schema 2 on the next state-changing action. Unknown or invalid schemas are reported and left unchanged.

## Safe tool actions

`omarchy-setup-ai-tool` is the action boundary for setup cards. It supports `catalog`, `status TOOL_ID`, `install TOOL_ID`, and `open TOOL_ID`. Its additive runtime contract is documented in [AI onboarding adapter](ai-onboarding-adapter.md). Authentication checks are separate from installation, Hermes response checks, and user-confirmed wizard completion. Provider output and credentials are never returned or stored.

The release image owns the normal installation of core AI tools. In onboarding, an installed core tool is opened for configuration or provider sign-in. If a core tool is unexpectedly missing, `install` is an explicit repair path; deselecting a card changes onboarding state only and never removes software. If a packaged Codex, Claude Code, or Hermes command is shadowed by a user override, status reports only the safe `reasonCode` value `path-shadow`; it exposes no path, disables Repair, and asks the user to review the override instead of claiming the package is missing.

Bitwarden, Codex, Claude Code, and Hermes reuse their existing Omarchy install paths. Their open actions start only the provider's desktop or official login flow, without autonomous launch flags or agent trust records. The action catalog is authoritative for current support; the identity catalog does not duplicate capability fields.

Hermes built-in memory is always active and needs no separate installation. Honcho and Hindsight open Hermes' official `memory setup` wizard, which owns the single external-provider choice and any provider credentials. MCP opens Hermes' own interactive picker and applies only to Hermes; it is not a universal MCP manager for other agents. Local Hindsight services and MCP servers start only after the user explicitly chooses them in the Hermes flow.

Honcho, Hindsight, and MCP are setup-only integrations. Their status always reports `installed: false` because Maslow does not inspect Hermes configuration or secrets. `prerequisiteInstalled` separately reports whether Hermes is ready, while `setupOnly: true` and `userConfirmable: true` tell the panel it may let the user mark the guided step complete after the official wizard exits. That confirmation is onboarding progress only, not proof of provider authentication or installation.

## Optional resume choices

`choice KEY VALUE` records only one of the following setup preferences in optional `setupChoices`, without changing schema 2 or completion/defer semantics:

| Key | Values |
| --- | --- |
| `account` | `codex`, `claude` |
| `hermes` | `recommended`, `deferred` |
| `memory` | `builtin`, `honcho`, `hindsight`, `deferred` |
| `desktop` | `hermes-desktop`, `chatgpt-desktop`, `none` |

Choices do not save a personal profile, authentication, an inference result, provider configuration, or memory content. Each write preserves unknown fields and historical tool status. Reset clears these known choices while preserving unknown fields. A saved desktop choice does not establish installation or runtime ownership; those are rediscovered on return. `complete` retains its existing guard for selected tools, and `defer` remains the safe finish-for-now path for incomplete setup.
