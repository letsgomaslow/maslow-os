# Maslow multi-repository Lenovo workspace

This file is a template copied to `~/Projects/Maslow/AGENTS.md`. Paths below are relative to that workspace, not to this file's source location. Read repository-local instructions before editing.

Start with `maslow-os/AGENTS.md`, `maslow-os/docs/maslow-development.md`, `maslow-os/docs/lenovo-development.md`, and `maslow-os/docs/handoffs/2026-09-16-lenovo-voice-development-handoff.md`. The user reports Voice updated and OpenAI/Hermes configured on Lenovo but not working. The failing layer/root cause is unknown; LiveKit is PENDING. Do not infer success from installation or repeat publication/bootstrap.

- `maslow-os/`: installed runtime source and `voice/`; active branch `codex/livekit-setup`; Voice procedures in `agents/skills/voice-development.md`.
- `maslow-os-shipped-voice9/`: detached exact shipped runtime `675019e5`; preserve as a comparison baseline. Latest integration includes unpublished LiveKit changes.
- `maslow-hub/`: independent Hub UI, onboarding, bounded updater; branch `codex/gpt-live-test-release`; read its `AGENTS.md`.
- `maslow-os-pkgs/`: Voice/Hermes/Hub package recipes and dependencies; branch `codex/linux-live-packages`; read its `AGENTS.md`.
- `maslow-os-iso/`: installer and headless installed-system harness; branch `codex/maslow-hub`; read its `AGENTS.md`.
- `maslow-connect/`: separate portal/gateway/MCP bridge; branch `codex/maslow-connect-org-control-plane`; read `README.md` and `docs/serverless-local-roadmap.md`, and any applicable instructions present.
- `maslow-releases/`: public signed metadata/status; branch `main`; read its `AGENTS.md`. Source backup does not authorize channel changes or new release publication.

Voice is source inside maslow-os, not a missing standalone repository. Hermes integration lives in runtime/packages; Codex/Claude and Hermes account setup remain separate. Runtime product branch is main; package/ISO product branches are maslow. Preserve worktrees, user edits, immutable released bytes, signing boundaries and the supported update path.

Keep source outside installed runtime; do not set global OMARCHY_PATH, overwrite package files, reset credentials/settings, or run concurrent daemons. Diagnose installed versions and the failing layer before a reversible source-run setup. Never commit secrets, credential stores, raw private logs, screenshots, binaries, VM overlays, or ISOs. Use at most two bounded workers with disjoint scope when useful and route economical models for inventory/docs, stronger review for safety/integration.

Validate focused changes in the owning repository. Fast visual iteration uses Docker + headless Weston + real Quickshell/software rendering with inspected PNGs. Installed proof uses ISO QEMU/TCG/CIDATA/SSH/QMP, no UTM. Actual Lenovo audio/task acceptance is separate. End each session by updating the runtime development index and dated handoff with commits, tests/failures/skips, observed results, unknowns and one next action.
