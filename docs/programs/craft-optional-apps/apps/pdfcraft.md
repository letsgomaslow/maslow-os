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

## Package implementation, 2026-10-11

Exact tag `v0.6.0` is `53a5880386789fc3531e54f6e6ffdef9a8e41f1a`; its archive SHA-256 is `9a136e71e37b459ed5746dbe19a364ce84cf5d995c6f6c98af6147d818390a53`. Native package `pdfcraft 0.6.0-1` built from recipes `f211378f416f50d63d4352b2049758a7aaa0996e`, SHA-256 `afa9eb1146696fd1feb0840fdbd8a6b3dc5cec6751dd86d6198b07a826f445c2`. Direct ELF paths `/usr/bin/pdfcraft` and `/usr/bin/pdfcraft-cli`; desktop, icons, MIME, AppStream and notices retained. Upstream update checks do not replace package files. See [package task](../tasks/CRAFT-PDF-PACKAGE.md) for clean build, same-publisher digest, notices and offline unpacked MCP evidence.

Disposition remains evaluating. Package is built; registered install, lifecycle, GUI, confinement, actual agents/Voice and fresh VM/Lenovo gates are open. No accepted capabilities or release-readiness change.

## Bounded GUI/CLI evidence, 2026-10-11

[GUI/CLI report](../tasks/CRAFT-PDF-GUI-CLI.md) records offline installed source-tag artifacts, software X11/Wayland rendering, real inspected save/reopen captures and a small known-answer fixture. PDF metadata/rotation/text was independently checked with Poppler; GUI save retained exact fixture bytes. Native portal/clipboard, exact Maslow VM/Lenovo and representative complex-format corpus gates remain open. GUI evidence does not waive the failed first confinement implementation. Disposition remains evaluating.
