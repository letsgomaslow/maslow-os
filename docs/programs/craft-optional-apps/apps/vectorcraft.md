# vectorcraft

Disposition: evaluating. Experimental; no accepted capabilities or release readiness.

Reviewed release target: `v0.9.0` (from 2026-10-11 research; exact tag revision/archive hash must be verified before use). Repository: https://github.com/storytold/vectorcraft.

Package: not built. Native recipe, GUI/CLI paths, dependencies, notices, checksum and pacman ownership gates open. Release archive preferred; same-tag locked source fallback only.

Compatibility: x86_64 Maslow OS/Hyprland only. GUI and headless saved-file MCP are separate gates; no live-window claim.

Confinement: not verified. Requires explicit existing project/output, selected agents, fixed fail-closed profile and negative tests. Project data can reach the agent/provider.

Workflow: GUI/CLI, file fidelity, Codex/Claude Code/Hermes, other adapter tests and actual spoken Voice gates open.

Evidence: prior source-only research in [Storytold review](../../../handoffs/2026-10-11-storytold-app-review.md); it is not installed acceptance. Task reports: `CRAFT-VECTOR-*`.

Blocker: prerequisites incomplete; not a final deferral. Next action: dependency-ready package evaluation.

Reconsideration: final deferral/exclusion, if any, must name evidence and a concrete condition.

## Starting research risks

These are upstream/source-review findings from the pinned source snapshots in the prior handoff, not reproduced failures in the selected release binaries. Verify the release tag separately; later main-branch repairs do not change selected package inputs.

Root flags imply headless mode. Without explicit mode MCP tries localhost:7979 before falling back; select headless deliberately. Live control lacks authentication. Path checks have documented app-owned-folder exceptions and a check/open race.

Reliable editable Illustrator .ai exchange remains incomplete; PDF-compatible .ai is not a guarantee that Illustrator editing metadata/layers survive. Affinity import is read-only and reports unsupported content. Interaction fidelity, many raster effects, 3D/materials, vertical CJK composition, scripting and generative features remain incomplete. Native Wayland file drops are not delivered by winit 0.30; File Open/file-manager paste or XWayland mode is documented. KDE tablet input issue is specifically reported, not established for Hyprland.

Acceptance must declare the exact formats/features tested and preserve originals. A generic round-trip or MCP-presence claim cannot pass these risks. No final deferral is inferred from this starting list.
