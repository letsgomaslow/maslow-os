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

## Package implementation, 2026-10-11

Exact tag `v0.7.0` is `79261615956ab21334e49ca1d384390272e647da`; its archive SHA-256 is `641f831252fd31b43ee1a12e572d7442e5652c2e5bf623de085741c370f0c91d`. Native package `photocraft 0.7.0-1` built from recipes `f211378f416f50d63d4352b2049758a7aaa0996e`, SHA-256 `22c553446baae55603c202a4090340961044cd779d3084c2a687eb0b9a5a92c5`. Direct ELF paths `/usr/bin/photocraft` and `/usr/bin/photocraft-cli`; desktop, icons, MIME, AppStream and notices retained. Upstream update checks do not replace package files. See [package task](../tasks/CRAFT-PHOTO-PACKAGE.md) for clean build, same-publisher digest, notices and offline unpacked MCP evidence.

Disposition remains evaluating. Package is built; registered install, lifecycle, GUI, confinement, actual agents/Voice and fresh VM/Lenovo gates are open. No accepted capabilities or release-readiness change.

## Bounded GUI/CLI evidence, 2026-10-11

[GUI/CLI report](../tasks/CRAFT-PHOTO-GUI-CLI.md) records offline installed source-tag artifacts, software X11/Wayland rendering, real inspected save/reopen captures and a small known-answer fixture. CLI and GUI native .pcraft saves exported with exact RGBA equality for a 320×240 flat PNG; Wayland drag/drop and tablet pressure are unsupported at this tag. Native portal/clipboard, exact Maslow VM/Lenovo and representative complex-format corpus gates remain open. GUI evidence does not waive the failed first confinement implementation. Disposition remains evaluating.
