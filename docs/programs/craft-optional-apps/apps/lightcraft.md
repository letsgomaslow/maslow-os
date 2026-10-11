# lightcraft

Disposition: evaluating. Experimental; no accepted capabilities or release readiness.

Reviewed release target: `v0.6.0` (from 2026-10-11 research; exact tag revision/archive hash must be verified before use). Repository: https://github.com/storytold/lightcraft.

Package: not built. Native recipe, GUI/CLI paths, dependencies, notices, checksum and pacman ownership gates open. Release archive preferred; same-tag locked source fallback only.

Compatibility: x86_64 Maslow OS/Hyprland only. GUI and headless saved-file MCP are separate gates; no live-window claim.

Confinement: not verified. Requires explicit existing project/output, selected agents, fixed fail-closed profile and negative tests. Project data can reach the agent/provider.

Workflow: GUI/CLI, file fidelity, Codex/Claude Code/Hermes, other adapter tests and actual spoken Voice gates open.

Evidence: prior source-only research in [Storytold review](../../../handoffs/2026-10-11-storytold-app-review.md); it is not installed acceptance. Task reports: `CRAFT-LIGHT-*`.

Blocker: prerequisites incomplete; not a final deferral. Next action: dependency-ready package evaluation.

Reconsideration: final deferral/exclusion, if any, must name evidence and a concrete condition.

## Starting research risks

These are upstream/source-review findings from the pinned source snapshots in the prior handoff, not reproduced failures in the selected release binaries. Verify the release tag separately; later main-branch repairs do not change selected package inputs.

--library selects and locks storage, not file confinement. Move imports remove originals without undo restoring their location. Use copy/add. Live 7980 lacks token authentication; connect when GUI owns the library lock.

Alpha; upstream estimates about 61% full-product readiness, 49% typical photographer, 64% essentials. Figures are self-assessments, not independently established. Camera color calibration is estimated rather than measured; compressed Olympus and unverified CR3 variants may use embedded previews. CR3 verified-body coverage is narrow; assess actual camera files before recommending RAW work. No Lightroom catalog interoperability; plugin/ecosystem and AI coverage remain weak. macOS gets more runtime coverage than Linux/Windows; source review cannot establish Hyprland quality.

Acceptance must declare the exact formats/features tested and preserve originals. A generic round-trip or MCP-presence claim cannot pass these risks. No final deferral is inferred from this starting list.
