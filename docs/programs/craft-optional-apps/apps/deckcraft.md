# deckcraft

Disposition: evaluating. Experimental; no accepted capabilities or release readiness.

Reviewed release target: `v0.5.0` (from 2026-10-11 research; exact tag revision/archive hash must be verified before use). Repository: https://github.com/storytold/deckcraft.

Package: not built. Native recipe, GUI/CLI paths, dependencies, notices, checksum and pacman ownership gates open. Release archive preferred; same-tag locked source fallback only.

Compatibility: x86_64 Maslow OS/Hyprland only. GUI and headless saved-file MCP are separate gates; no live-window claim.

Confinement: not verified. Requires explicit existing project/output, selected agents, fixed fail-closed profile and negative tests. Project data can reach the agent/provider.

Workflow: GUI/CLI, file fidelity, Codex/Claude Code/Hermes, other adapter tests and actual spoken Voice gates open.

Evidence: prior source-only research in [Storytold review](../../../handoffs/2026-10-11-storytold-app-review.md); it is not installed acceptance. Task reports: `CRAFT-DECK-*`.

Blocker: prerequisites incomplete; not a final deferral. Next action: dependency-ready package evaluation.

Reconsideration: final deferral/exclusion, if any, must name evidence and a concrete condition.

## Starting research risks

These are upstream/source-review findings from the pinned source snapshots in the prior handoff, not reproduced failures in the selected release binaries. Verify the release tag separately; later main-branch repairs do not change selected package inputs.

No reviewed file-root flag. Live example port 7990 is unauthenticated. Test save/close behavior on generated copies.

Upstream says PPTX has never been corpus-tested on real decks; comments/media/rewind round-trip losses and EMF/SVG image gaps. Gap report identifies edited-deck Close discarding without prompt, startup driver crashes, and no long-session soak. These are upstream documented gaps at snapshot, not independently reproduced. PDF artwork is rasterized; no native printing; English-only; limited animation/chart depth and presenter display behavior.

Acceptance must declare the exact formats/features tested and preserve originals. A generic round-trip or MCP-presence claim cannot pass these risks. No final deferral is inferred from this starting list.
