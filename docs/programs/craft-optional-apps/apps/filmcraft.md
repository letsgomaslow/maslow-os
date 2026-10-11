# filmcraft

Disposition: evaluating. Experimental; no accepted capabilities or release readiness.

Reviewed release target: `v0.6.0` (from 2026-10-11 research; exact tag revision/archive hash must be verified before use). Repository: https://github.com/storytold/filmcraft.

Package: not built. Native recipe, GUI/CLI paths, dependencies, notices, checksum and pacman ownership gates open. Release archive preferred; same-tag locked source fallback only.

Compatibility: x86_64 Maslow OS/Hyprland only. GUI and headless saved-file MCP are separate gates; no live-window claim.

Confinement: not verified. Requires explicit existing project/output, selected agents, fixed fail-closed profile and negative tests. Project data can reach the agent/provider.

Workflow: GUI/CLI, file fidelity, Codex/Claude Code/Hermes, other adapter tests and actual spoken Voice gates open.

Evidence: prior source-only research in [Storytold review](../../../handoffs/2026-10-11-storytold-app-review.md); it is not installed acceptance. Task reports: `CRAFT-FILM-*`.

Blocker: prerequisites incomplete; not a final deferral. Next action: dependency-ready package evaluation.

Reconsideration: final deferral/exclusion, if any, must name evidence and a concrete condition.

## Starting research risks

These are upstream/source-review findings from the pinned source snapshots in the prior handoff, not reproduced failures in the selected release binaries. Verify the release tag separately; later main-branch repairs do not change selected package inputs.

Docs explicitly reject PhotoCraft-style root flags. --project selects a document, not confinement. Live --bridge on 9876 lacks token authentication. Independent isolation is new work.

Alpha; upstream reports 86% breadth and 56% professional readiness. Linux/Windows are explicitly less exercised than macOS; wild camera/phone files less tested than conformance streams. Cannot open .prproj; import via FCP7 XML/AAF/OTIO. No VST3/AudioUnits/OpenFX plugin hosting. GPU effects exist, but Lumetri/keys/export rendering remain CPU-heavy. Linux H264/HEVC hardware decode requires VAAPI or NVIDIA; VP9/AV1 decode is software. H264 is software delivery export; H265 requires supported hardware and AV1 export is absent.

Acceptance must declare the exact formats/features tested and preserve originals. A generic round-trip or MCP-presence claim cannot pass these risks. No final deferral is inferred from this starting list.
