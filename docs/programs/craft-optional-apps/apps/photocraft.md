# photocraft

Disposition: evaluating. Experimental; no accepted capabilities or release readiness.

Reviewed release target: `v0.7.0` (from 2026-10-11 research; exact tag revision/archive hash must be verified before use). Repository: https://github.com/storytold/photocraft.

Package: not built. Native recipe, GUI/CLI paths, dependencies, notices, checksum and pacman ownership gates open. Release archive preferred; same-tag locked source fallback only.

Compatibility: x86_64 Maslow OS/Hyprland only. GUI and headless saved-file MCP are separate gates; no live-window claim.

Confinement: not verified. Requires explicit existing project/output, selected agents, fixed fail-closed profile and negative tests. Project data can reach the agent/provider.

Workflow: GUI/CLI, file fidelity, Codex/Claude Code/Hermes, other adapter tests and actual spoken Voice gates open.

Evidence: prior source-only research in [Storytold review](../../../handoffs/2026-10-11-storytold-app-review.md); it is not installed acceptance. Task reports: `CRAFT-PHOTO-*`.

Blocker: prerequisites incomplete; not a final deferral. Next action: dependency-ready package evaluation.

Reconsideration: final deferral/exclusion, if any, must name evidence and a concrete condition.

## Starting research risks

These are upstream/source-review findings from the pinned source snapshots in the prior handoff, not reproduced failures in the selected release binaries. Verify the release tag separately; later main-branch repairs do not change selected package inputs.

Read/write authority fails closed without explicit roots. Live bridge uses a private token file and port 7878. Roots and authentication were also verified in v0.7.0 source; binaries remain untested.

Upstream describes early alpha, approximately 45% professional readiness; its feature counts and corpus success rates are upstream measurements, not our runtime verification. PSD render round trips are not byte-identical and the broad menu wiring metric is explicitly not behavior parity. AI/generative functions, tool coverage, typography/pro workflows and plugin compatibility remain incomplete. README documents no native Wayland file drag/drop with winit 0.30. FileOpen/paste workarounds, or XWayland via WAYLAND_DISPLAY=, are offered; verify current pinned build on Hyprland.

Acceptance must declare the exact formats/features tested and preserve originals. A generic round-trip or MCP-presence claim cannot pass these risks. No final deferral is inferred from this starting list.
