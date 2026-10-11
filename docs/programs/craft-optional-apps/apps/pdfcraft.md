# pdfcraft

Disposition: evaluating. Experimental; no accepted capabilities or release readiness.

Reviewed release target: `v0.6.0` (from 2026-10-11 research; exact tag revision/archive hash must be verified before use). Repository: https://github.com/storytold/pdfcraft.

Package: not built. Native recipe, GUI/CLI paths, dependencies, notices, checksum and pacman ownership gates open. Release archive preferred; same-tag locked source fallback only.

Compatibility: x86_64 Maslow OS/Hyprland only. GUI and headless saved-file MCP are separate gates; no live-window claim.

Confinement: not verified. Requires explicit existing project/output, selected agents, fixed fail-closed profile and negative tests. Project data can reach the agent/provider.

Workflow: GUI/CLI, file fidelity, Codex/Claude Code/Hermes, other adapter tests and actual spoken Voice gates open.

Evidence: prior source-only research in [Storytold review](../../../handoffs/2026-10-11-storytold-app-review.md); it is not installed acceptance. Task reports: `CRAFT-PDF-*`.

Blocker: prerequisites incomplete; not a final deferral. Next action: dependency-ready package evaluation.

Reconsideration: final deferral/exclusion, if any, must name evidence and a concrete condition.

## Starting research risks

These are upstream/source-review findings from the pinned source snapshots in the prior handoff, not reproduced failures in the selected release binaries. Verify the release tag separately; later main-branch repairs do not change selected package inputs.

Use --root explicitly; without it ordinary user file access remains. MCP is headless. Live GUI control is a separate authenticated control-file/CLI interface, not an MCP bridge. Exports ignore MCP progress/cancellation.

Upstream reports fuzz-discovered crashes/hangs on hostile files, with regressions being fixed. Corpus success claims are upstream results, not rerun here. Encryption interoperability, existing-text editing (especially CJK/RTL), OCR beyond Latin, Office-to-PDF/export fidelity, token/online signature validation, advanced preflight/PDF-X/UA and XFA remain weak or missing. MCP progress/cancellation notifications are ignored; exports synchronous. No HTTP/SSE MCP transport found in inspected implementation.

Acceptance must declare the exact formats/features tested and preserve originals. A generic round-trip or MCP-presence claim cannot pass these risks. No final deferral is inferred from this starting list.
