# Voice execution bridge

The conversational provider emits a bounded task brief and never receives execution tools. `TaskManager` persists the original request, normalized brief, project, mode, `selected_agent`, and plain-language `routing_reason` before work starts. `AgentRouter` then supplies one TaskManager-compatible client for Codex, Hermes, or Claude.

An explicit `tool_preference` selects only that agent. If its readiness check fails, Voice returns `AGENT_UNAVAILABLE` and does not fall back. Automatic routing checks the configured ready default first, then Codex, Hermes, and Claude in that fixed order without checking the same candidate twice. A repeated request identity returns the saved task and route without repeating readiness or submission.

Hermes uses its loopback-only Runs service and stable idempotency key. Its terminal and file tools plus three reviewed plugin tools call the Voice daemon over a private authenticated Unix socket. The daemon resolves the immutable Hermes `session_id` to the saved Voice task before calling `ExecutionManager.handle(task, operation, params)`. Codex and Claude can instead own the top-level task through `DirectExecutionClient`, which exposes the same `submit`, `status`, `events`, `stop`, `steer`, and `approve` shape while running the existing structured adapter in the Voice daemon.

## Start policy and ownership

`lab_auto` starts a routed task immediately after a validated explicit work request. `review` stores the task in `proposed` and requires a Start action. The proposal already names the selected peer; Start revalidates that same peer and never chooses a different fallback. Neither policy approves a later command, file change, desktop action, or other executor request.

The selected peer is persisted independently from display text. `selected_agent` is one of `codex`, `hermes`, or `claude`; `routing_reason` records a bounded sentence such as an explicit selection, configured ready default, or automatic-order choice. `owner` is the corresponding display label. Older task records without `selected_agent` retain their historical Hermes route for upgrade compatibility.

## Gemini conversation boundary

New settings default to `gemini_live`; an existing valid saved mode survives upgrade. This mode constructs Gemini 3.8 Live through the LiveKit Agents Google realtime plugin with `vertexai=False` and the Google AI Studio key from Secret Service. The local native audio transport owns capture, acoustic processing, playback, interruption, and cleanup. The provider does not join a LiveKit room, call LiveKit Inference, or consume `livekit_url`, `livekit_key`, or `livekit_secret`. Those saved values remain available only when the person chooses the optional LiveKit Expressive mode.

Conversation readiness is separate from task readiness. A valid Google credential and installed Gemini plugin can make the ready orb start listening with one click even when no task agent is ready. Task routing reports its own setup failure only when needed. Advanced Voice settings exposes provider details, task-agent preference, and `lab_auto` or `review`; the active compact controls retain listening/mute/speaking state, Mute or Resume, End, Captions, Tasks, and Settings.

Inactivity is advanced by completed conversational turns and speaking-to-listening transitions, not arbitrary microphone level. The daemon ends a quiet non-speaking session after the configured idle interval and ends every conversation after 30 minutes. Desktop lock also ends the live provider while persisted tasks continue.

## Operations

| Operation | Parameters | Result |
| --- | --- | --- |
| `coding` or `delegate_coding` | `tool`: `auto`, `codex`, or `claude`; `instructions`: non-empty text | Runs a coding child and returns its saved child record and final text. Hermes invokes this through its reviewed plugin; a direct peer client invokes the selected adapter itself. |
| `open_application` | `application`: allowlisted name | Opens a packaged helper or explicitly configured desktop ID |
| `open_website` | `url`: complete HTTP or HTTPS URL without embedded credentials | Opens the approved host browser helper, or the fixed isolated browser in offline mode |
| `approve` or `deny` | `approval_id` and `child_id` | Resolves exactly one current child tool request |
| `cancel` | none | Interrupts every active coding child for the task and denies pending child approvals |
| `readiness` | none | Reports whether the selected mode can start Codex or Claude |

The supplied task is compared with the saved `id`, `request_id`, `project`, `mode`, and original source. The task UUID is also the immutable Hermes and Claude session ID. A mismatch fails before any process or desktop action starts.

## Recovery and idempotency

Hermes Runs are durable. A saved Hermes run ID is reconciled after daemon restart; a known run is never resubmitted, and a stable request/attempt key protects the initial handoff. Confirmed coordinator loss and uncertain handoff/stop states become interrupted for review.

Direct Codex and Claude jobs are in-process and are explicitly `resumable = False`. If Voice restarts after a direct task reaches submitting, accepted, running, awaiting approval, or stopping, recovery writes `DIRECT_RUN_LOST` and marks it interrupted. It does not reconstruct the client, resume the adapter, or resubmit the request. A still-queued task is safe to start because no adapter received it. Continue creates a new explicit attempt after the person reviews partial changes.

## Child records and approvals

Coding children are persisted in `task.children`. Each record includes its Voice child UUID, tool, status, summarized instructions, result or safe error, and the provider's session, thread, and turn identifiers when supplied. These identifiers allow the UI and support tooling to distinguish a Voice task from a provider conversation and a single provider turn.

For a direct peer run, `DirectExecutionClient` creates exactly one child using the persisted original request and brief. Its synthetic run identity is local to the current daemon attempt. Status is derived from that exact child; a new client cannot claim or rediscover an earlier direct run. Direct steering returns `STEERING_UNAVAILABLE` because the current Codex and Claude adapters do not implement mid-turn redirection. The person can stop the task and use Continue with revised instructions.

Codex command and file-change requests and Claude `can_use_tool` callbacks create a new Voice approval UUID. The top-level `task.approval` is set to `{owner: "child", request_id, child_id, ...}` so the existing task UI can show it. Approval lookup includes all three of the task ID, child ID, and approval ID. An answer applies once; a stale, cross-task, or cross-child answer fails with `APPROVAL_EXPIRED`. Approving one request never changes a session-wide permission policy.

Cancellation interrupts Codex with `turn/interrupt`, interrupts and disconnects Claude, cancels an offline isolated invocation, rejects pending approvals, and leaves the persisted child in `cancelled`. A cancelled or failed parent task calls `ExecutionManager.cancel(task_id)` through the existing `TaskManager.children` hook.

## Codex

The online Codex adapter starts `codex app-server --listen stdio://` directly, without a shell. It performs the required JSON-RPC `initialize` / `initialized` handshake, then calls `thread/start` and `turn/start`. It retains the returned Codex `sessionId`, thread UUID, and turn UUID. The adapter requests the `workspace-write` sandbox, the `untrusted` approval policy, and the `user` approval reviewer. It never requests `danger-full-access`, automatic review, session-wide approval, or a bypass flag.

The wire fields are based on the installed Codex app-server schema generated by `codex app-server generate-ts --experimental`. The generated schema is a verification input and is not checked into this repository. Codex is optional; readiness reports a missing binary and delegation returns `CODEX_MISSING` instead of silently selecting an unsafe fallback. The adapter reads the person's existing Codex configuration and does not write or replace it. OpenAI's public documentation currently describes Codex configuration and metrics but does not publish the complete experimental app-server schema, so the installed versioned generator remains authoritative for this internal adapter.

## Claude

The Claude adapter uses `ClaudeSDKClient` in streaming mode with `permission_mode="default"` and a `can_use_tool` callback. It supplies the Voice task UUID through `ClaudeAgentOptions.session_id`, retains message/result identifiers, and calls `interrupt()` followed by `disconnect()` on cancellation. The SDK and API key are optional readiness dependencies.

Cloud Claude execution accepts only the `anthropic` API key retrieved from the Voice keyring. It creates a private temporary `CLAUDE_CONFIG_DIR`, clears inherited Claude OAuth token variables for the child, and does not read, copy, extract, or replace Claude subscription credentials. User, local, and project settings are disabled and MCP configuration is strict, so saved hooks, credentials, and custom MCP servers cannot override Voice routing or permissions. Anthropic documents `ClaudeSDKClient` as the stateful bidirectional client, `can_use_tool` as the per-tool permission callback, and API keys as the supported local SDK credential: [Python Agent SDK](https://platform.claude.com/docs/en/agent-sdk/python), [Claude authentication](https://platform.claude.com/docs/en/manage-claude/authentication).

## Offline mode

Offline coding never starts a host coding child. `ExecutionManager` requires an injected isolated runtime; without it the operation fails with `OFFLINE_ISOLATION_REQUIRED`. The runtime snapshots the selected project into its bwrap workspace, exposes it as `/project`, and provides the configured local model endpoint inside that namespace.

Both Codex and Claude run inside the same private namespace. Codex uses its interactive app-server protocol through `runtime.create_process`; Claude uses `execution_worker.py` under `/usr/lib/maslow-voice/venv/bin/python3`, and that worker owns the SDK and CLI. Only framed progress, result, and permission messages cross the worker pipe. Each permission answer must match the current opaque request ID and contain an explicit Boolean. No coder starts on the host when the private runtime is absent or fails.

The namespace worker exposes process start/readline/write/wait/stop RPCs with random handles; host PIDs cannot be supplied. Working directories must remain under `/project`, reserved environment fields cannot be overridden, output frames and child counts are bounded, and stop kills the entire child process group. Codex records its returned session/thread/turn IDs and retains interactive single-request approval. Claude uses the same SDK approval callback as cloud mode, with an empty private config directory and only a dummy local Ollama token.

The isolated model base URLs are fixed to `http://127.0.0.1:11434/v1` for [Codex Responses](https://docs.ollama.com/api/openai-compatibility) and `http://127.0.0.1:11434` for Claude Messages. Ollama starts inside the namespace using downloaded model files and `OLLAMA_NO_CLOUD=1`; there is no host network, native cloud configuration, or fallback provider. Ollama officially supports Claude Code through its [Anthropic-compatible API](https://docs.ollama.com/integrations/claude-code). This compatibility still depends on the installed Ollama version and selected model supporting the required protocol and tools.

## User server mode

Both coders receive the selected execution model and explicit server endpoint. Codex uses a custom Responses provider with `requires_openai_auth=false`; Claude uses `ANTHROPIC_BASE_URL` and a server token, never the cloud Anthropic credential. Both Ollama and [LM Studio](https://lmstudio.ai/docs/developer/anthropic-compat) document Claude Code support. If configured, the Voice `server_token` is used only for that server. Missing models or unsupported server kinds fail before launch. Readiness reports configuration prerequisites; the starting connection/protocol exchange remains the live compatibility check, and a failed exchange never selects a cloud provider.

Offline URLs are still validated as HTTP or HTTPS, then passed only to `runtime.open_url`, which owns the fixed private browser profile and network boundary. Offline applications require `runtime.open_application` and its internal allowlist. There is no fallback to the host browser, host desktop, or host subprocess when either isolated launcher is absent.

## Desktop boundary

Host applications resolve through a fixed mapping of friendly names to packaged argv arrays or explicitly configured `.desktop` IDs. Commands are started with an argv API and never through a shell. Arbitrary executable names, command-line fragments, URL schemes, credentials in URLs, control characters, and application names outside the mapping are rejected.

The default packaged names are `browser`, `files`, `hub`, and `terminal`. A deployment can supply a different allowlist to `ExecutionManager`; adding an entry is a reviewed daemon configuration change, not something Hermes or the conversational model can request at runtime.

## Bounded audit

`SessionAudit` appends local JSONL records under the private Voice state directory. Its field allowlist covers the session, provider, model, safe state/error code, task ID, selected agent, elapsed milliseconds, and provider token/audio/seconds counters when reported. Strings are capped at 200 characters. Rotation keeps the current and previous files at approximately 2 MiB each, with owner-only permissions and no symlink following.

Transcript text, raw audio, credentials, prompts, source requests, task briefs, tool arguments, file contents, and reasoning are not accepted audit fields. A failed audit write is ignored so diagnostics cannot hold the microphone open or block shutdown.

## Verification boundary

On September 13, 2026, the installed Codex 0.153.4 JSON schema and a real `initialize` / `thread/start` exchange verified the required session ID, selected custom provider/model, user approval reviewer, and workspace-write sandbox with network access disabled. The probe used a fresh temporary configuration and an unreachable loopback endpoint, so it performed no model inference. Claude Agent SDK 0.2.152 constructors and message fields were checked against the installed package. The newer staging source has automated coverage for Gemini model construction/events, one-click UI contracts, peer selection, explicit-unavailable behavior, proposal review, idempotent duplicate submission, direct approvals/cancellation, and nonresumable direct recovery.

These source checks do not establish Google account authentication, physical microphone/speaker/echo behavior, latency, long-session reliability, live Codex/Hermes artifacts, rollback, package installation, or visual behavior on the Lenovo. The candidate remains staging-only. Package signing, publication, stable promotion, and rebuilding the verified ISO require the separate reviewed release and hardware acceptance gates.
