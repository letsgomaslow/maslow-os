# Storytold optional app review for Maslow OS

Reviewed 11 October 2026. Scope: all 56 public repositories listed by [Storytold](https://github.com/orgs/storytold/repositories), with deeper installation, release, MCP and source reviews of the 12 Craft desktop applications. This is an integration proposal, not a release or compatibility certification.

Maslow OS can offer a useful selection of these applications as optional downloads. Start with **PdfCraft and PhotoCraft**, then **VectorCraft**, and evaluate **WordCraft, GridCraft and DeckCraft** for a second productivity pilot. All 12 Craft desktop applications have MCP implementations, so MCP presence alone does not distinguish them. Filesystem controls, package contents, useful workflows and document fidelity should determine rollout order. Retain LibreOffice and present the Craft apps as experimental alternatives while they mature.

In plain English: put a small app card in Maslow Hub, download the software only when someone chooses Install, then offer a separate “Use with my AI tools” step. Maslow Connect can make the command-line tool available to supported agents. Maslow Voice can pass the person's request to an agent, which uses the app's MCP tools and returns a saved result. Working on files in the background is the simpler first milestone; visibly editing an already-open application needs additional process, session and permission handling.

## What was checked

The organization API returned 56 public repositories. Root READMEs were retrieved for 54; GitHub's README endpoints returned 404 for `hanashi-graphics-demo` and `html_test`. Two independent research agents inspected six Craft desktop repositories each; the coordinator reviewed the other 44 repositories and the local Maslow runtime, Hub and Connect sources. The desktop review included actual MCP dispatch code, CLI entry points, Linux packaging scripts and release listings, rather than relying on README badges alone.

No Storytold binaries, installers or repository programs were executed. No build, Hyprland session, performance benchmark, real document round-trip, MCP connection or Voice workflow was tested. Release asset listings establish availability, not successful download, verified checksums, absence of malware or runtime compatibility. README maturity and feature percentages are upstream claims; they are not Maslow acceptance evidence. The inventory is a dated snapshot, not a guarantee about future releases.

Current default-branch source and latest release artifacts are separate evidence. Several repositories have commits after their release tags. Before using any command or access-control flag in a package, verify it in that exact release revision; otherwise build and test an explicitly pinned newer source revision. The presence of a release tarball does not prove it contains every capability in today's README.

Local source baselines: runtime `969f2960` on `codex/maslow-cli-update-retry`; Connect `0c6f7b9` on `codex/local-connect`; Hub `33940d2` on `codex/hub-0.3.6-health`. These are development checkouts. They do not establish what every installed or publicly distributed Maslow image contains. The pre-existing uncommitted development-index changes were preserved.

## How Maslow installs applications today

| Existing mechanism | Source finding | Implication for Craft apps |
| --- | --- | --- |
| Base packages | `install/omarchy-base.packages` includes `openai-codex-bin`, `claude-code`, and `libreoffice-fresh`. | These examples are already packaged in the inspected base; do not assume they are all first-launch downloads. |
| True lazy CLI wrappers | `bin/omarchy-mise-install` creates a small user command which runs `mise use -g` and then `mise x` when invoked. | Suitable precedent for download-on-first-use, but a consumer Craft app should not compile Rust or chase an unpinned branch at first launch. |
| Agent installation | `install/helpers/agent.sh` recognizes packaged Codex, Claude and Hermes, checks runtime ownership/PATH, and retains mise fallbacks for other cases. | Installation, correct executable, provider sign-in and readiness are separate states. |
| Optional desktop installs | `omarchy-install-app` and `omarchy-install-and-launch` show package installation in a terminal; the latter launches the desktop ID only after success. | Reuse this flow once a reviewed Arch package exists. |
| Package manager | The actual `omarchy-pkg-add` implementation calls `pacman -S --needed` and verifies with `pacman -Q`. AUR has separate commands. | A README with `apt install` or `dnf install` is not directly usable. The package must be available in a configured repository or use a separately designed reviewed delivery path. |
| Menu | `default/omarchy/omarchy-menu.jsonc` uses fixed install actions and installed-package guards. | A menu entry can be small and present before an optional app is downloaded. |
| Hub catalog | `catalog/featured.json` is data-only. `helper/catalog.py` permits 1–30 items with only id, name, description and status. | Adding a JSON card does not create an installer. Use fixed, locally implemented actions; remote catalog content must not become executable commands. |
| Connect MCP catalog | `packages/bridge/src/server-catalog.ts` holds pinned stdio/HTTP server definitions, added on user choice. | Add reviewed Craft CLI definitions after the binaries and desired access boundaries exist. |

Relevant runtime sources: [package list](../../install/omarchy-base.packages), [agent helper](../../install/helpers/agent.sh), [lazy wrapper](../../bin/omarchy-mise-install), [install and launch](../../bin/omarchy-install-and-launch), [package helper](../../bin/omarchy-pkg-add), [menu](../../default/omarchy/omarchy-menu.jsonc). Repository boundaries remain runtime → package recipes → ISO; Hub and Connect have their own source repositories. Optional network-delivered apps need not increase the ISO payload, although any new required baseline infrastructure must be separately validated.

## Recommended installation approach

### Preferred product path

Build version-pinned Arch packages in `maslow-os-pkgs`, initially consuming the upstream Linux tarball where it passes inspection, or building pinned source with the lockfile in a clean builder. The inspected Linux packaging scripts stage both the GUI binary and `<app>-cli`; the tarball provides a straightforward way to install both with normal file ownership. PdfCraft also publishes a separate CLI-only Linux archive.

The package should own stable executable paths, desktop launchers, icons, MIME integration and license notices. Derive actual shared-library dependencies from the chosen release/build instead of copying Debian `-dev` packages into Arch recipes. Test Wayland and XWayland, graphics initialization, file dialogs, clipboard, fonts, scaling and application startup on the supported Maslow image. SoundCraft additionally needs audio/MIDI testing; video and effects tools need codec/export testing. Keep Rust, Node, Cargo caches, test corpora and model downloads out of the base installation unless a specific runtime dependency requires them.

Use one update owner per installation. Pacman-owned binaries should be updated by the package channel; an upstream launcher must not independently replace them. Pin source or release URLs and hashes, retain attribution, build an auditable package, and use the approved signing/publication workflow when distribution is authorized. A SHA-256 file downloaded alongside a binary is useful for integrity checks, but is not independent publisher authentication or Maslow release approval.

The reviewed app release lists expose Linux AppImage, tarball and other distro formats. They do not establish native Arch packages. `.deb` and `.rpm` are unsuitable as direct Maslow installation commands. AppImage is useful for a disposable evaluation, but needs a dependable CLI path and desktop/update handling for a supported offering. Flatpak introduces filesystem/IPC permissions that must be tested for MCP; a sandboxed GUI does not automatically provide a usable host CLI.

### Fast experimental alternative

[Craft Launcher](https://github.com/storytold/craft-launcher#downloads) already offers install, update and launch controls for the suite. Its inspected `v0.2.0` release contains Linux x86_64/aarch64 AppImages and tarballs, among other formats. The README documents Linux installation through apt/dnf/zypper, otherwise Flatpak or an AppImage under `~/Applications`. It also describes self-updating and early-alpha status.

Offering one launcher is a plausible low-effort discovery experiment. It is not the complete Maslow Connect integration: CLI locations, installation ownership, update behavior and agent registration still need implementation and testing. For an initial experiment, keep its user-managed installs separate from any Maslow package-managed apps. Do not describe the launcher's published checksum checks as a substitute for Maslow's package trust model. Native per-app packaging is the stronger long-term fit for consistent updates and MCP paths.

## Connect and Voice integration

The inspected Connect implementation already supports stdio and HTTP server definitions, per-agent enable/disable, namespaced `maslow-<id>` entries, registration verification and rollback. Its current source recognizes eight agent IDs: Codex, Claude Code, Hermes, Grok, Pi, OpenCode, VS Code and LM Studio. Five use CLI adapters and three use configuration adapters. Source support is not a successful Craft-app test in every agent. See the reviewed [server registry and launcher](https://github.com/letsgomaslow/maslow-connect/blob/0c6f7b9/packages/bridge/src/servers.ts), [agent wiring](https://github.com/letsgomaslow/maslow-connect/blob/0c6f7b9/packages/bridge/src/server-wiring.ts), [CLI operations](https://github.com/letsgomaslow/maslow-connect/blob/0c6f7b9/packages/bridge/src/servers-cli.ts) and [starter catalog](https://github.com/letsgomaslow/maslow-connect/blob/0c6f7b9/packages/bridge/src/server-catalog.ts). The Hub's [catalog validator](https://github.com/letsgomaslow/maslow-hub/blob/33940d2/helper/catalog.py) and [panel](https://github.com/letsgomaslow/maslow-hub/blob/33940d2/ui/Panel.qml) show the existing display and Connect controls. These repositories may require project access.

**Local MCP servers are user-trusted and not policy-gated.** This is explicitly stated in `packages/bridge/src/servers.ts`. The separate `maslow-apps` Composio relay's read-only and forbidden-tool rules do not apply to an arbitrary Craft server. A stdio child inherits the process environment and runs with the user's permissions. Connect's current definition accepts command, argv, environment and secret names; it does not itself impose an OS filesystem sandbox or an isolated working directory.

For a first pilot, register a fixed CLI path with a specific project input/output boundary using the app's own supported flags. Prefer explicitly headless execution. Do not assume that merely setting the current directory restricts file access, or that adding a server proves it connects. Run `initialize`, `tools/list`, one bounded read, one authorized write and one denied out-of-root operation. Confirm agent selection and saved output independently.

For example, the existing Connect CLI can express these proposed registrations after packaging. These commands were not executed; `/home/example/Work/Craft` represents an existing project folder selected by the person, and `/usr/bin` paths represent the proposed package layout. Confirm flags against the pinned application version first.

```sh
maslow-connect servers add-custom --id pdfcraft --name PdfCraft \
  --command /usr/bin/pdfcraft-cli --arg mcp \
  --arg --root --arg /home/example/Work/Craft --agents codex

maslow-connect servers add-custom --id photocraft --name PhotoCraft \
  --command /usr/bin/photocraft-cli --arg mcp \
  --arg --automation-read-root --arg /home/example/Work/Craft \
  --arg --automation-write-root --arg /home/example/Work/Craft/output --agents codex
```

The app's path checks are application-level controls, not an OS sandbox against other local processes or a complete security audit. Review their documented limitations and test symlink/path-escape cases. Where an app lacks adequate controls, an OS sandbox or a constrained proxy would be new integration work; do not claim Connect already supplies one.

The desired flow is:

1. **Install:** show version, source, download requirement and experimental status; install only after the person's choice and report actual completion.
2. **Connect:** offer selected supported agents and explain the project folders/tools being enabled. Register only after the CLI exists; preserve unrelated MCP entries and roll back partial registration failures.
3. **Verify:** connect and complete an app-specific sample task. Keep “installed,” “configured,” “connected” and “workflow tested” distinct.
4. **Use by voice:** Voice routes a bounded request to an agent that has the connection, preserves that agent's approvals, and reports the result with the saved artifact location.
5. **Remove:** disconnect only Maslow-owned entries before removing the package; retain user documents/preferences unless separately requested. Test reinstall and reconnect.

There is an important Voice distinction. The visible Codex/Claude terminal paths use the person's agent configuration, whereas the cloud Claude SDK adapter intentionally uses a private configuration and excludes arbitrary saved MCP servers. Registering a server in Claude Code therefore does not automatically enable it in every Voice execution route. Pilot the visible configured agent path first; separately design and test any allowlisted MCP injection into the SDK route. See [Voice execution boundaries](../../voice/docs/execution.md).

Headless and live-window modes must have separate labels. A headless MCP session can create a file without changing the open GUI document. To drive a visible window, start or attach to the intended application control endpoint, establish any required per-window token, and prove that the tools affect that window. Several apps document port 7979, creating collisions if their examples are copied unchanged. Allocate distinct loopback ports and manage process lifetime, reconnect and simultaneous-agent behavior. A loopback TCP JSON control endpoint is not automatically an HTTP MCP endpoint; usually the CLI bridges it back to stdio.

## Pilot order and acceptance

| Order | Apps | Rationale | First acceptance workflow |
| --- | --- | --- | --- |
| 1 | PdfCraft, PhotoCraft | Broad daily utility and explicit automation file-access controls. | PDF merge/extract to a new file; image resize/layer edit/export on copies; reject an out-of-root path. |
| 2 | VectorCraft | Strong agent-oriented illustration use; headless root flags make a bounded pilot feasible. | Create an SVG, modify objects, export PNG and inspect both outputs. Explicitly avoid accidental auto-attachment to an unrelated window. |
| 3 | WordCraft, GridCraft, DeckCraft | Highest general productivity value after installation/MCP mechanics work. | Document formatting and DOCX/PDF round-trip; known-answer spreadsheet formulas and XLSX reopen; PPTX creation/export/reopen. Compare with established tools and record losses. |
| 4 | LightCraft, FilmCraft, EffectCraft | Valuable creative workflows with larger media, graphics, export and filesystem-access test surfaces. | RAW import/export on copies; small timeline/audio export; short motion graphic render with cancellation and resource limits. |
| 5 | DesignCraft, CADCraft, SoundCraft | More specialized users and substantial print/CAD/audio acceptance needs; DesignCraft and SoundCraft identify as pre-alpha. | Multi-page export; DXF dimensions/units round-trip; recording/playback/export with PipeWire and representative devices. |

This order applies the user's MCP-first, productivity/creativity-second priorities, then uses readiness to break ties. It is a proposed sequence, not a measured quality ranking. Source-visible MCP support is sufficient to select a pilot; it is insufficient to award a “Tested” badge.

Before a pilot becomes a consumer option, verify fresh install before the first OS update, package dependency/ownership checks, launch/relaunch, offline behavior after installation, interrupted download recovery, uninstall/reinstall, upgrade without user-data loss, and compatible rollback. Test actual MCP and spoken workflows in the chosen agents, permission refusal/cancellation, concurrent sessions and generated files. No feature-parity percentage should replace these checks.

Implementation ownership: package recipes in `maslow-os-pkgs`; optional menu/launch commands in `maslow-os`; fixed UI/helper operations and status presentation in `maslow-hub`; MCP definitions/registration and health checks in `maslow-connect`; agent-routing or permission-boundary changes in runtime `voice/`. Preserve the current signed catalog schema unless a separately reviewed change is necessary. Do not place all 56 repositories in the 30-item featured catalog: most are not consumer apps.

## Licensing and product claims

The Craft apps generally document MIT OR Apache-2.0 licensing, with notices and separate licenses for assets/fonts. Their clean-room descriptions are upstream statements, not independent proof that every implementation and bundled asset is clear for every distribution scenario. Market them by their own names and actual tested tasks; do not promise complete Adobe, Microsoft, Autodesk or Avid compatibility.

The organization is not uniformly permissively licensed. [`artcraft-services/LICENSE.md`](https://github.com/storytold/artcraft-services/blob/main/LICENSE.md) is a custom work-in-progress fair-source license with commercial/competition restrictions. [`craft-launcher`](https://github.com/storytold/craft-launcher#license-and-credits) separately restricts ArtCraft brand assets. Several older repositories have no license detected in GitHub metadata; that means license review is unresolved, not that copying them is authorized. `EventCenterPlugin` explicitly depends on a paid Unreal plugin, and `StreamTwo` describes third-party game assets. Treat these as concrete reasons to exclude those projects from a blanket free-software offering.

The AI studio `artcraft` is separate from the 12 desktop Craft editors. Its inspected latest release, `artcraft-v0.41.0`, lists Windows/macOS assets; Linux is described as a source-development setup. Its hosted generation services may have provider accounts and usage costs. `artcraftx` describes builds as forthcoming. Neither is currently as direct a Linux optional-app candidate as the 12 editors.

## Repository findings

The following sections cover every repository in the dated organization inventory. For non-app projects, “no MCP documented” is limited to the reviewed README and is not a complete negative source audit. License metadata is informational; the actual license/NOTICE/asset files govern packaging review.

### The 12 desktop editors

All 12 have source-visible stdio MCP servers and published Linux release assets. GUI and CLI membership was checked directly in archive headers for PdfCraft, WordCraft, GridCraft, DeckCraft, VectorCraft and DesignCraft; the other six were checked in packaging source and release listings. No executable was run.

| Application | Inspected release | Upstream stage | File-access controls in reviewed MCP source |
| --- | --- | --- | --- |
| [pdfcraft](https://github.com/storytold/pdfcraft) | [v0.6.0](https://github.com/storytold/pdfcraft/releases/tag/v0.6.0) | Alpha | Explicit controls available |
| [photocraft](https://github.com/storytold/photocraft) | [v0.7.0](https://github.com/storytold/photocraft/releases/tag/v0.7.0) | Alpha | Explicit controls available |
| [vectorcraft](https://github.com/storytold/vectorcraft) | [v0.9.0](https://github.com/storytold/vectorcraft/releases/tag/v0.9.0) | Alpha | Explicit controls available |
| [wordcraft](https://github.com/storytold/wordcraft) | [v0.5.0](https://github.com/storytold/wordcraft/releases/tag/v0.5.0) | Alpha | No project-root restriction found |
| [gridcraft](https://github.com/storytold/gridcraft) | [v0.5.0](https://github.com/storytold/gridcraft/releases/tag/v0.5.0) | Alpha | No project-root restriction found |
| [deckcraft](https://github.com/storytold/deckcraft) | [v0.5.0](https://github.com/storytold/deckcraft/releases/tag/v0.5.0) | Alpha | No project-root restriction found |
| [lightcraft](https://github.com/storytold/lightcraft) | [v0.6.0](https://github.com/storytold/lightcraft/releases/tag/v0.6.0) | Alpha | No project-root restriction found |
| [effectcraft](https://github.com/storytold/effectcraft) | [v0.8.0](https://github.com/storytold/effectcraft/releases/tag/v0.8.0) | Alpha | Explicit controls available |
| [filmcraft](https://github.com/storytold/filmcraft) | [v0.6.0](https://github.com/storytold/filmcraft/releases/tag/v0.6.0) | Alpha | No project-root restriction found |
| [designcraft](https://github.com/storytold/designcraft) | [v0.6.0](https://github.com/storytold/designcraft/releases/tag/v0.6.0) | Pre-alpha | No project-root restriction found |
| [cadcraft](https://github.com/storytold/cadcraft) | [v0.5.0](https://github.com/storytold/cadcraft/releases/tag/v0.5.0) | Pre-alpha | No project-root restriction found |
| [soundcraft](https://github.com/storytold/soundcraft) | [v0.5.0](https://github.com/storytold/soundcraft/releases/tag/v0.5.0) | Pre-alpha | No project-root restriction found |

For all 12, upstream instructions offer Linux release formats rather than a verified native Arch package. Prefer a pinned tarball for GUI and CLI together. Common graphics/windowing dependencies need translation and verification on Arch; x86_64/aarch64 releases generally target glibc 2.35 or newer. Source commands below are upstream development instructions, not the proposed user-facing installer. Build in a builder, not on first launch. All 12 document MIT OR Apache-2.0 code licenses, with notices and separately licensed assets/branding.

#### pdfcraft

PDF workbench: view/search, page organization/combine/split, annotations, forms, encryption, redaction, basic signing, and headless inspection/rendering.

**Installation:** [v0.6.0](https://github.com/storytold/pdfcraft/releases/tag/v0.6.0); inspected source [bbbe60015c57](https://github.com/storytold/pdfcraft/tree/bbbe60015c571ebfc39708ee07777b89e267122a). Workspace core minimum Rust 1.90; docs/development.md explicitly requires Rust 1.95+ for UI/desktop/web because of craft-ui. Cargo workspace pins craft-libs by git revision. Releases embed craft-fonts; packaging also fetches OCR models. Headless-only source build: cargo build --release --locked -p pdfcraft-cli. MCP is a default CLI feature; --no-default-features omits it.

```sh
git clone https://github.com/storytold/pdfcraft
cd pdfcraft
cargo run --release -p pdfcraft -- some.pdf
```

**Headless MCP launch:**

```sh
pdfcraft-cli mcp --root /absolute/existing/pdf-workspace --compact
```

**Access and session handling:** Use --root explicitly; without it ordinary user file access remains. MCP is headless. Live GUI control is a separate authenticated control-file/CLI interface, not an MCP bridge. Exports ignore MCP progress/cancellation.

**Readiness limits:** Upstream reports fuzz-discovered crashes/hangs on hostile files, with regressions being fixed. Corpus success claims are upstream results, not rerun here. Encryption interoperability, existing-text editing (especially CJK/RTL), OCR beyond Latin, Office-to-PDF/export fidelity, token/online signature validation, advanced preflight/PDF-X/UA and XFA remain weak or missing. MCP progress/cancellation notifications are ignored; exports synchronous. No HTTP/SSE MCP transport found in inspected implementation.

Sources: [README](https://github.com/storytold/pdfcraft/blob/bbbe60015c571ebfc39708ee07777b89e267122a/README.md), [Linux packaging](https://github.com/storytold/pdfcraft/blob/bbbe60015c571ebfc39708ee07777b89e267122a/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/pdfcraft/blob/bbbe60015c571ebfc39708ee07777b89e267122a/docs/mcp.md), [crates/automation/README.md](https://github.com/storytold/pdfcraft/blob/bbbe60015c571ebfc39708ee07777b89e267122a/crates/automation/README.md).

#### photocraft

Layered image editing and digital painting: PSD/PSB, masks, adjustment layers, smart objects, type, brushes, color management and raster exports. Useful for agent-edited assets and batch image work.

**Installation:** [v0.7.0](https://github.com/storytold/photocraft/releases/tag/v0.7.0); inspected source [2e0c42669299](https://github.com/storytold/photocraft/tree/2e0c42669299e428884d9dde229283d1299bd821). Workspace rust-version 1.95; native egui/wgpu app. Optional craft-fonts input for Japanese glyphs; releases include it. Official Linux packages build with heif enabled.

```sh
git clone https://github.com/storytold/photocraft
cd photocraft
cargo run --release -p photocraft -- image.psd
```

**Headless MCP launch:**

```sh
photocraft-cli mcp --automation-read-root /work/project --automation-write-root /work/project
```

**Access and session handling:** Read/write authority fails closed without explicit roots. Live bridge uses a private token file and port 7878. Roots and authentication were also verified in v0.7.0 source; binaries remain untested.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
photocraft --control 7878 --control-token-file /private/path/control.token --automation-read-root /work/project --automation-write-root /work/project
photocraft-cli mcp --bridge 127.0.0.1:7878 --control-token-file /private/path/control.token
```

**Readiness limits:** Upstream describes early alpha, approximately 45% professional readiness; its feature counts and corpus success rates are upstream measurements, not our runtime verification. PSD render round trips are not byte-identical and the broad menu wiring metric is explicitly not behavior parity. AI/generative functions, tool coverage, typography/pro workflows and plugin compatibility remain incomplete. README documents no native Wayland file drag/drop with winit 0.30. FileOpen/paste workarounds, or XWayland via WAYLAND_DISPLAY=, are offered; verify current pinned build on Hyprland.

Sources: [README](https://github.com/storytold/photocraft/blob/2e0c42669299e428884d9dde229283d1299bd821/README.md), [Linux packaging](https://github.com/storytold/photocraft/blob/2e0c42669299e428884d9dde229283d1299bd821/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/photocraft/blob/2e0c42669299e428884d9dde229283d1299bd821/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/photocraft/blob/2e0c42669299e428884d9dde229283d1299bd821/docs/control-protocol.md).

#### vectorcraft

Vector illustration and agent-driven drawing: paths, shapes, gradients, type, artboards, layers, effects, SVG/PDF and other vector/raster interchange.

**Installation:** [v0.9.0](https://github.com/storytold/vectorcraft/releases/tag/v0.9.0); inspected source [24eaf5e037ca](https://github.com/storytold/vectorcraft/tree/24eaf5e037caf77d3bbf446c63fd81bf414a8033). Workspace Rust 1.95+, edition 2024, egui/eframe 0.36 and pinned craft-ui git input. Release builds embed optional craft-fonts; local builds can point CRAFT_FONTS_DIR at its absolute path. Cargo CLI build documented in docs/mcp.md.

```sh
cargo run --release -p vectorcraft
cargo run --release -p vectorcraft -- examples/dusk-poster.vectorcraft
cargo run --release -p vectorcraft -- --control 7979
cargo run --release -p vectorcraft-cli -- mcp
```

**Headless MCP launch:**

```sh
vectorcraft-cli mcp --headless --automation-read-root /absolute/existing/project --automation-write-root /absolute/existing/project/out
```

**Access and session handling:** Root flags imply headless mode. Without explicit mode MCP tries localhost:7979 before falling back; select headless deliberately. Live control lacks authentication. Path checks have documented app-owned-folder exceptions and a check/open race.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
vectorcraft --control 7979 --automation-read-root /work/project --automation-write-root /work/project/out
vectorcraft-cli mcp --connect 127.0.0.1:7979
```

**Readiness limits:** Reliable editable Illustrator .ai exchange remains incomplete; PDF-compatible .ai is not a guarantee that Illustrator editing metadata/layers survive. Affinity import is read-only and reports unsupported content. Interaction fidelity, many raster effects, 3D/materials, vertical CJK composition, scripting and generative features remain incomplete. Native Wayland file drops are not delivered by winit 0.30; File Open/file-manager paste or XWayland mode is documented. KDE tablet input issue is specifically reported, not established for Hyprland.

Sources: [README](https://github.com/storytold/vectorcraft/blob/24eaf5e037caf77d3bbf446c63fd81bf414a8033/README.md), [Linux packaging](https://github.com/storytold/vectorcraft/blob/24eaf5e037caf77d3bbf446c63fd81bf414a8033/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/vectorcraft/blob/24eaf5e037caf77d3bbf446c63fd81bf414a8033/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/vectorcraft/blob/24eaf5e037caf77d3bbf446c63fd81bf414a8033/docs/control-protocol.md).

#### wordcraft

Word-style word processor with DOCX and other text formats, typography, references, tables, review/track changes, mail merge, PDF export and headless document automation.

**Installation:** [v0.5.0](https://github.com/storytold/wordcraft/releases/tag/v0.5.0); inspected source [1d4f741f2377](https://github.com/storytold/wordcraft/tree/1d4f741f23773f47a27a5a017ba47e59629caee5). Workspace Rust 1.90, edition 2024, egui/eframe 0.36; effective dependency minimum not build-tested. Prefer published tarball. CLI links wordcraft-mcp by default.

```sh
git clone https://github.com/storytold/wordcraft
cd wordcraft
cargo run --release -p wordcraft -- --sample
cargo run --release -p wordcraft -- report.docx
```

**Headless MCP launch:**

```sh
wordcraft-cli mcp --author "Maslow (assistant)"
```

**Access and session handling:** No reviewed file-root flag. --author attributes agent edits; tracked changes can be enabled separately. Live bridge at 7981 has a per-window key, which authenticates control but does not restrict file scope.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
wordcraft --control 7981
wordcraft-cli mcp --connect 127.0.0.1:7981
```

**Readiness limits:** DOCX corpus/real-world pagination fidelity not proven; current gaps list says ink/drawing canvases lost, OLE preview-only, move tracking/content controls lossy. ROADMAP still says charts/SmartArt dropped, but newer gaps.md says rendered and preserved with parts after recent changes; avoid repeating the stale broader claim. Upstream reports startup crashes/freezes; fonts/columns/footnote pagination can differ from Word. Native printing is delegated to PDF system viewer.

Sources: [README](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/README.md), [Linux packaging](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/docs/control-protocol.md).

#### gridcraft

Excel-style spreadsheet editing, calculation, tables/charts, sort/filter and agent-driven data/formula operations; XLSX native interchange.

**Installation:** [v0.5.0](https://github.com/storytold/gridcraft/releases/tag/v0.5.0); inspected source [9f896c1249f4](https://github.com/storytold/gridcraft/tree/9f896c1249f40d18bf182199dc03042959be5f3f). Workspace Rust 1.90, edition 2024, egui/eframe 0.36; effective dependency compiler minimum may exceed workspace declaration, so prefer releases and verify any source-build toolchain. Release embeds craft-fonts.

```sh
cargo run --release -p gridcraft
cargo run --release -p gridcraft -- --sample sales
cargo run --release -p gridcraft -- book.xlsx
```

**Headless MCP launch:**

```sh
gridcraft-cli mcp --sample budget
```

**Access and session handling:** No reviewed file-root flag. --in selects a workbook, not a sandbox. Live example port 7979 is unauthenticated; prefer independently isolated headless sessions.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
gridcraft --control 7979
gridcraft-cli mcp --connect 7979
```

**Readiness limits:** Upstream says real-world XLSX corpus/Excel no-repair verification is missing. Unmodelled content and chart types/options can be lost on save. Legacy .xls absent; large ~100 MB workbooks fail; calculation single-threaded; non-Latin shaping/PDF coverage incomplete. Several usability/printing/pivot/chart-depth gaps remain. Avoid treating generated outputs as audited financial calculations.

Sources: [README](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/README.md), [Linux packaging](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/docs/control-protocol.md).

#### deckcraft

Presentation creation/editing and slideshow: themes/layouts, text/shapes/pictures, tables/charts, transitions/animations, PPTX exchange, PDF and image output.

**Installation:** [v0.5.0](https://github.com/storytold/deckcraft/releases/tag/v0.5.0); inspected source [a98df49b2163](https://github.com/storytold/deckcraft/tree/a98df49b21632d69a3da994d35df1ea91dab41af). Workspace Rust 1.90, edition 2024; Linux ALSA headers explicitly required (Arch package alsa-lib) for slideshow audio, plus build toolchain/pkg-config. Optional sibling craft-fonts; releases include fonts. egui/wgpu desktop and CPU slide renderer.

```sh
git clone https://github.com/storytold/deckcraft
cd deckcraft
cargo run --release -p deckcraft-cli -- render --sample --all --scale 1 out/
```

**Headless MCP launch:**

```sh
deckcraft-cli mcp --sample
```

**Access and session handling:** No reviewed file-root flag. Live example port 7990 is unauthenticated. Test save/close behavior on generated copies.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
deckcraft --control 7990
deckcraft-cli mcp --connect 7990
```

**Readiness limits:** Upstream says PPTX has never been corpus-tested on real decks; comments/media/rewind round-trip losses and EMF/SVG image gaps. Gap report identifies edited-deck Close discarding without prompt, startup driver crashes, and no long-session soak. These are upstream documented gaps at snapshot, not independently reproduced. PDF artwork is rasterized; no native printing; English-only; limited animation/chart depth and presenter display behavior.

Sources: [README](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/README.md), [Linux packaging](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/docs/control-protocol.md).

#### lightcraft

Photo library, culling and non-destructive RAW development: import, ratings, albums, presets, crop/masks, grading and batch exports. Useful for local photo automation after camera/format validation.

**Installation:** [v0.6.0](https://github.com/storytold/lightcraft/releases/tag/v0.6.0); inspected source [0ba118de92a8](https://github.com/storytold/lightcraft/tree/0ba118de92a81f7463ca0e6d79e1323137b1adae). Entire current workspace, including CLI and web, requires Rust 1.95. Native egui/wgpu; source includes pureRust RAW decoders and CPU fallback. Optional craft-fonts input; release fonts included. Nix build/run is documented, but not needed for Arch catalog packaging.

```sh
git clone https://github.com/storytold/lightcraft && cd lightcraft
cargo run --release -p lightcraft
cargo run --release -p lightcraft -- --control 7980
```

**Headless MCP launch:**

```sh
lightcraft-cli mcp --library /work/LightCraft-library --compact
```

**Access and session handling:** --library selects and locks storage, not file confinement. Move imports remove originals without undo restoring their location. Use copy/add. Live 7980 lacks token authentication; connect when GUI owns the library lock.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
lightcraft --library /work/LightCraft-library --control 7980
lightcraft-cli mcp --connect 127.0.0.1:7980 --compact
```

**Readiness limits:** Alpha; upstream estimates about 61% full-product readiness, 49% typical photographer, 64% essentials. Figures are self-assessments, not independently established. Camera color calibration is estimated rather than measured; compressed Olympus and unverified CR3 variants may use embedded previews. CR3 verified-body coverage is narrow; assess actual camera files before recommending RAW work. No Lightroom catalog interoperability; plugin/ecosystem and AI coverage remain weak. macOS gets more runtime coverage than Linux/Windows; source review cannot establish Hyprland quality.

Sources: [README](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/README.md), [Linux packaging](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/docs/control-protocol.md).

#### effectcraft

Motion graphics/compositing and visual effects: compositions, layered properties, animation/keyframes, expressions, text/shapes, render queue and exports. Useful for agent-generated titles, animations and simple compositions.

**Installation:** [v0.8.0](https://github.com/storytold/effectcraft/releases/tag/v0.8.0); inspected source [9a7d3e76991d](https://github.com/storytold/effectcraft/tree/9a7d3e76991d5372448033b473dc12c2480a6a04). Rust 1.95; native egui/wgpu with cpal audio. Many media/codec crates are pinned Git dependencies on FilmCraft; craft-libs is pinned too. A source build therefore downloads more than this repository. README headless render and web xtask builds are documented.

```sh
git clone https://github.com/storytold/effectcraft
cd effectcraft
cargo run --release -p effectcraft
```

**Headless MCP launch:**

```sh
effectcraft-cli mcp --automation-read-root /work/project --automation-write-root /work/project
```

**Access and session handling:** Root flags are optional; supply them. Confined mode blocks scripting and bridge UI/control escape surfaces. Desktop 9877 lacks token authentication; prefer scoped headless rendering.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
effectcraft --control 9877
effectcraft-cli mcp --bridge 9877 --automation-read-root /work/project --automation-write-root /work/project
```

**Readiness limits:** Alpha; upstream weighted estimate around 45% readiness despite 91% feature breadth. Only one narrow live AfterEffects fidelity comparison is documented. Cannot open .aep projects; existing professional templates/plugins/presets and project interchange are major blockers. Reliability and preview/performance outside macOS remain concerns. Codec/format presence does not establish mature camera-footage support or encoder efficiency. Windows/Linux get less live testing.

Sources: [README](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/README.md), [Linux packaging](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/docs/control-protocol.md).

#### filmcraft

Nonlinear video editing: timeline cuts/trims, color/effects, titles/captions, audio mixing and export. Useful for agent-generated sequences and bounded test footage workflows.

**Installation:** [v0.6.0](https://github.com/storytold/filmcraft/releases/tag/v0.6.0); inspected source [4e2d0bc2d364](https://github.com/storytold/filmcraft/tree/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe). Current workspace Rust 1.95, egui/wgpu and cpal; optional craft-fonts input embedded in releases. In-house Rust codecs; FFmpeg described as external test oracle rather than a shipped runtime dependency.

```sh
cargo run --release -p filmcraft
cargo run --release -p filmcraft -- --control 9876
cargo run --release -p filmcraft-cli -- mcp
```

**Headless MCP launch:**

```sh
filmcraft-cli mcp --project /work/test.fcproj
```

**Access and session handling:** Docs explicitly reject PhotoCraft-style root flags. --project selects a document, not confinement. Live --bridge on 9876 lacks token authentication. Independent isolation is new work.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
filmcraft --control 9876
filmcraft-cli mcp --bridge 127.0.0.1:9876
```

**Readiness limits:** Alpha; upstream reports 86% breadth and 56% professional readiness. Linux/Windows are explicitly less exercised than macOS; wild camera/phone files less tested than conformance streams. Cannot open .prproj; import via FCP7 XML/AAF/OTIO. No VST3/AudioUnits/OpenFX plugin hosting. GPU effects exist, but Lumetri/keys/export rendering remain CPU-heavy. Linux H264/HEVC hardware decode requires VAAPI or NVIDIA; VP9/AV1 decode is software. H264 is software delivery export; H265 requires supported hardware and AV1 export is absent.

Sources: [README](https://github.com/storytold/filmcraft/blob/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe/README.md), [Linux packaging](https://github.com/storytold/filmcraft/blob/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe/packaging/linux/package.sh), [docs/control-protocol.md](https://github.com/storytold/filmcraft/blob/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe/docs/control-protocol.md).

#### designcraft

InDesign-style page layout/publishing: pages/spreads, frames/stories/styles, swatches/images, CPU typography/rendering, IDML, PDF/PNG/EPUB output and layout automation.

**Installation:** [v0.6.0](https://github.com/storytold/designcraft/releases/tag/v0.6.0); inspected source [16a7365701f9](https://github.com/storytold/designcraft/tree/16a7365701f9ce8f93ca77a27a8dc2fffb807869). Explicit Rust 1.95+ frontend/workspace, edition 2024; pinned craft-ui git revision; releases embed optional craft-fonts. CPU canvas (vello_cpu), wgpu composites GUI, Vulkan/OpenGL fallback documentation.

```sh
cargo run --release -p designcraft
cargo run --release -p designcraft -- --sample
cargo run --release -p designcraft -- --sample --control 7979
cargo run --release -p designcraft-cli -- run --sample --all-pages out/
```

**Headless MCP launch:**

```sh
designcraft-cli mcp --sample
```

**Access and session handling:** No reviewed file-root flag. Live example 7979 lacks authentication. Basic editing and frame-threading maturity gates remain.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
designcraft --control 7979
designcraft-cli mcp --connect 7979
```

**Readiness limits:** ROADMAP/gaps report manual frame-to-frame threading unavailable; autoflow/primary-text-frame bugs remain. Engine Document::thread existing is not the same as a usable UI/MCP command. INDD cannot be opened; IDML not corpus-proven; composition not compared to InDesign; real file/layout fidelity uncertain. Basic copy/paste/context menus/caret formatting reported broken on Linux/Windows; PDF production/printing and long-document typography gaps.

Sources: [README](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/README.md), [Linux packaging](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/docs/control-protocol.md).

#### cadcraft

2D CAD drawing and drafting: command-line geometry, layers, snaps, annotations, hatches/blocks, layouts and DXF/DWG/SVG/PNG/PDF handling. Useful for scratch drawings generated by agents.

**Installation:** [v0.5.0](https://github.com/storytold/cadcraft/releases/tag/v0.5.0); inspected source [699dd1aeca1d](https://github.com/storytold/cadcraft/tree/699dd1aeca1dba018931d2eb95e92c0cf2033bbd). Desktop/web need Rust 1.95 although core workspace declares 1.90; native egui 0.36. Uses installed TrueType/OpenType fonts; no SHX reader. Pinned craft-libs and acadrust for DWG. Browser build uses trunk.

```sh
git clone https://github.com/storytold/cadcraft
cd cadcraft
cargo run --release -p cadcraft -- --sample
```

**Headless MCP launch:**

```sh
cadcraft-cli mcp
```

**Access and session handling:** No reviewed file-root flag. Live example 7979 lacks authentication. Use scratch drawings; never overwrite the only original DWG/DXF.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
cadcraft --control 7979
cadcraft-cli mcp --connect 127.0.0.1:7979
```

**Readiness limits:** Pre-alpha; upstream estimates 38% full-target / 28% working 2D-drafter readiness. Four of five core workflows fail its alpha gate. Object snap tracking and basic TRIM/EXTEND/OFFSET options have gaps; block editing/REFEDIT/xrefs and plot styles incomplete. DWG save always R2000 and drops unmodeled content; no save verification in AutoCAD is documented. SHX fonts are substituted; 3D/full CAD parity is distant.

Sources: [README](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/README.md), [Linux packaging](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/docs/control-protocol.md).

#### soundcraft

Digital audio workstation for editing, recording and mixing: tracks, clips, automation, MIDI editing, built-in instruments/effects, native plugin hosting and audio bounce. Useful for scripted offline mixes and simple music experiments.

**Installation:** [v0.5.0](https://github.com/storytold/soundcraft/releases/tag/v0.5.0); inspected source [7414719f3760](https://github.com/storytold/soundcraft/tree/7414719f3760de1c9359ec9723351a7232442e61). Desktop/web require Rust 1.95 while core workspace declares 1.90. cpal provides ALSA on Linux; Arch builds require alsa-lib headers and pkgconf. Headless CLI links no ALSA according to release workflow.

```sh
git clone https://github.com/storytold/soundcraft
cd soundcraft
cargo run --release -p soundcraft -- --demo
```

**Headless MCP launch:**

```sh
soundcraft-cli mcp --demo
```

**Access and session handling:** No reviewed file-root flag. Headless avoids requiring audio hardware but does not sandbox files. Live 7801 lacks token authentication; native plugins introduce another code-execution surface.

Live-window bridge, when separately enabled (allocate unique example ports):

```sh
soundcraft --control 7801
soundcraft-cli mcp --connect 7801
```

**Readiness limits:** Pre-alpha; upstream estimates 40% professional readiness and 57% essentials. Menu breadth 94% is explicitly not equivalent to finished workflows. Only default audio devices/fixed 512-sample blocks; audio interface/channel/buffer selection and durable record-to-disk path incomplete. No hardware MIDI input/output. No AAF/OMF/.ptx interchange; no ProTools fidelity harness. Compressed delivery exports, localization and platform coverage incomplete. VST3/AU support has platform-specific caveats, including macOS entitlements/editors.

Sources: [README](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/README.md), [Linux packaging](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/packaging/linux/package.sh), [docs/mcp.md](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/docs/mcp.md), [docs/control-protocol.md](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/docs/control-protocol.md).

### Supporting projects and miscellaneous repositories

These 44 entries complete the organization inventory beyond the 12 desktop editors. Their install instructions are upstream guidance summarized for evaluation, not commands run on this machine.

| Repository | Purpose and upstream installation | Maslow decision | License signal |
| --- | --- | --- | --- |
| [ActorSpawningPlugin](https://github.com/storytold/ActorSpawningPlugin/blob/master/README.md) | Unreal actor-spawning plugin. README only says no dependencies yet; no full installation procedure. | **Developer resources.** Engine component, not independent app. | Not detected |
| [AnimationTest](https://github.com/storytold/AnimationTest/blob/main/README.md) | UE5 VTuber experiment. Root README contains only title/one-line description. | **Exclude: experiment.** No documented installation or consumer release workflow. | Not detected |
| [artcraft](https://github.com/storytold/artcraft/blob/main/README.md) | AI image/video/3D creation studio. README directs Windows/macOS users to releases; Linux source setup uses Rust, Node20+, npm, Tauri2 CLI and ./script/artcraft/unix_dev.sh. | **Later evaluation; no easy Linux catalog entry yet.** Inspected artcraft-v0.41.0 assets are macOS/Windows only. Linux development instructions do not establish supported Linux release packaging. Generation uses provider accounts/services; free source does not make model usage free. | README states MIT OR Apache-2.0; inspect NOTICE and bundled materials separately. |
| [artcraft-services](https://github.com/storytold/artcraft-services/blob/main/README.md) | Backend APIs, billing, workers and web frontends. Rust/Node/npm; SQLX_OFFLINE=true cargo run -p storyteller-web; frontend npm install and VITE_USE_LOCAL_API=true npx nx dev artcraft-webapp. Requires MySQL, Redis, Elasticsearch/object storage and provider configuration. | **Do not distribute as a routine app.** A service platform with operational and account requirements, not a desktop optional app. Its API is HTTP, not documented MCP. | LICENSE.md is a custom WIP fair-source license with commercial/competition/branding restrictions; unlike the permissive Craft app licenses. |
| [artcraftx](https://github.com/storytold/artcraftx/blob/main/README.md) | Minimal AI creation desktop experiment. Node20+, npm, Rust and Tauri2 CLI; ./script/unix_dev.sh. | **Watchlist.** README explicitly says experimental and builds forthcoming. Development launcher rather than consumer install. | Not detected |
| [Azure-Kinect-Sample-for-Unity](https://github.com/storytold/Azure-Kinect-Sample-for-Unity/blob/master/README.md) (fork) | Unity Kinect sample. Install KinectSDK1.4.1, copy Windows DLLs into Unity Plugins, run example scenes; tested Unity2019.4. | **Specialist hardware only.** Windows-oriented hardware sample, not native Maslow app. | MIT |
| [bevy-mocap](https://github.com/storytold/bevy-mocap/blob/main/README.md) | ARKit facial-animation import into Bevy. Add Bevy0.12 and bevy-facial-mocap Git dependency; cargo run --example simple_example. | **Developer resources.** Library requiring a Bevy project; README dependency still points to another owner with a transfer TODO. | Not detected |
| [cloud-worker](https://github.com/storytold/cloud-worker/blob/main/README.md) | RunPod/ComfyUI video-model operations. Deploy scripts to a GPU pod, install ComfyUI/weights, tunnel UI and run Python benchmark harness. | **Specialist infrastructure only.** README targets a B200-class cloud test machine. Cloud resource setup and model downloads, not local lightweight desktop installation. | Not detected |
| [cloudcam](https://github.com/storytold/cloudcam/blob/master/README.md) | Azure Kinect point-cloud streaming to Unreal. Build Kinect SDK and Rust/native dependencies; dated Ubuntu setup and device/udev instructions. | **Specialist hardware only.** Hardware-specific WIP with old Ubuntu repositories, manual library copying and boot/device changes; unsuitable for general optional-app installer. | Not detected |
| [CloudCamPlugin](https://github.com/storytold/CloudCamPlugin/blob/main/README.md) | Unreal point-cloud rendering/plugin. Copy to project Plugins, possibly rename to CloudCam; requires UnrealZeroMQ. | **Developer resources.** Engine integration with historical Windows-specific build patches. | Not detected |
| [craft-fonts](https://github.com/storytold/craft-fonts/blob/main/README.md) | Shared fonts and optional embedding support. Build with CRAFT_FONTS_DIR pointing to pinned checkout; cargo test --workspace and feature embed tests. | **Build infrastructure.** Optional build input; preserve font manifests/checksums/licenses and verify language coverage. Not an end-user app. | Code MIT OR Apache-2.0; listed fonts OFL-1.1. |
| [craft-launcher](https://github.com/storytold/craft-launcher/blob/main/README.md) | Suite installer and updater. Download official Linux AppImage, chmod +x, run; or tar.gz tree. Also .deb/.rpm/.flatpak. Source: cargo run --release -p artcraft-launcher. Rust >=1.90 and native windowing headers. | **Optional experimental suite entry.** Latest inspected release v0.2.0 actually lists x86_64 and aarch64 AppImage/tar.gz assets and SHA256SUMS.txt. Linux install flow prefers apt/dnf/zypper, then Flatpak or AppImage. No documented pacman install path. Possible fast experimental entry, but updater ownership and CLI discovery must be tested; do not have launcher and pacman both replace the same files. | MIT OR Apache-2.0 code; separate brand terms and asset attributions. |
| [craft-libs](https://github.com/storytold/craft-libs/blob/main/README.md) | Shared Rust libraries for Craft applications. Add pinned Git dependency craft-<name> using a commit rev; craft-ui requires Rust>=1.95. | **Build infrastructure.** Build dependency only; pin with each app package instead of exposing an install tile. | MIT OR Apache-2.0 plus asset licenses. |
| [craft-repo-status-app](https://github.com/storytold/craft-repo-status-app/blob/main/README.md) | Maintainer dashboard for GitHub issues/builds. Rust stable, cargo install tauri-cli --version ^2, gh login; make install builds macOS .app and login item. | **Internal tooling watchlist.** Useful internally for watching suite health. Documented install is macOS-specific; Linux port and packaging not established. GitHub credentials required for regular use. | Not detected |
| [discord-vocodes](https://github.com/storytold/discord-vocodes/blob/master/README.md) | Discord voice bot. README lists libssl-dev, libsodium-dev and Serenity dependencies; no complete end-user installer. | **Exclude.** External service bot with legacy documentation, not a creative desktop app. | Not detected |
| [EventCenterPlugin](https://github.com/storytold/EventCenterPlugin/blob/master/README.md) | Unreal event/websocket integration WIP. Python venv and requirements, commercial BlueprintWebSocket plugin, edit project Build.cs. | **Exclude from free consumer catalog.** Requires an explicitly paid plugin; counters the idea that every repository is a free replacement for paid software. | Not detected |
| [fakeyou-recast](https://github.com/storytold/fakeyou-recast/blob/master/README.md) | Voice conversion prototype. Rust, libtorch1.13 C++ ABI, CUDA and downloaded external models; cargo run --release --bin fakeyou-recast --features=devmode. | **Specialist research only.** Dependency/model-heavy prototype with uncertain setup documentation. Not a ready Voice provider or MCP app. | Not detected |
| [FineTrainers-Conditioning](https://github.com/storytold/FineTrainers-Conditioning/blob/main/README.md) | Video-model fine-tuning toolkit. pip install -r requirements.txt plus diffusers from Git; download models/data; accelerate launch train.py. | **Specialist research only.** GPU-heavy research environment. README examples report model-dependent 11–42GB minimum LoRA VRAM under specific settings. Prefer a separate specialist environment, not a consumer one-click app. | Apache-2.0 |
| [github-media](https://github.com/storytold/github-media/blob/main/README.md) | README videos and images. No software installer; media publishing notes. | **Exclude: media only.** Not an application. | Not detected |
| [hanashi-graphics-demo](https://github.com/storytold/hanashi-graphics-demo) | Fyrox/WASM graphics demo. No README found; GitHub README endpoint returned404. | **Exclude: undocumented demo.** Insufficient installation documentation for an optional consumer app. | Not detected |
| [html_test](https://github.com/storytold/html_test) (archived) | HTML test project. No README found; GitHub README endpoint returned404. | **Exclude: archived test.** Archived test repository. | Not detected |
| [HyperJail](https://github.com/storytold/HyperJail/blob/main/README.md) | UE5 VTubing experiment. Root README contains only title/one-line description. | **Exclude: experiment.** No documented installation or consumer release workflow. | Not detected |
| [irsa-manager](https://github.com/storytold/irsa-manager/blob/main/README.md) (fork) | Kubernetes AWS IAM service-account controller. Helm chart installation, Kubernetes cluster and AWS credentials; configure custom resources. | **Specialist infrastructure only.** Infrastructure administration with account/cloud permissions; not desktop productivity. | MIT |
| [k4a-sys-temp](https://github.com/storytold/k4a-sys-temp/blob/master/README.md) | Temporary Rust Azure Kinect bindings. Install libk4a1.3 or Kinect SDK, then Cargo examples. | **Exclude: upstream warning.** README explicitly says not to use this temporary fork. | MIT |
| [LiveScan3D](https://github.com/storytold/LiveScan3D/blob/master/README.md) (fork) | Multiple-Kinect 3D reconstruction. Windows machine plus Kinect; Visual Studio2019 source build or binary release. | **Exclude from native Linux catalog.** README requires Windows. Hardware and engine-specific workflow outside Arch catalog. | MIT |
| [motion-capture-data](https://github.com/storytold/motion-capture-data/blob/master/README.md) | Motion-capture recordings. No installer; use/convert recording data. | **Exclude: data only.** Data repository; verify recording/asset rights before any redistribution. | Not detected |
| [photocraft-corpus](https://github.com/storytold/photocraft-corpus/blob/main/README.md) | Real-file rendering/round-trip test fixtures. From PhotoCraft: cargo xtask corpus --photoshop or cargo xtask test-corpus. Pinned commit and SHA256 manifest. | **Test infrastructure.** Useful for package QA, not installed desktop payload. Fixture generation itself needs Photoshop on macOS, whereas consuming fixtures is separate. | MIT OR Apache-2.0 stated; keep provenance and separate asset terms. |
| [placeholder-artcraft](https://github.com/storytold/placeholder-artcraft/blob/main/README.md) (archived) | Historical staging copy of ArtCraft. README describes an old publication placeholder; no end-user install. | **Exclude: superseded.** Archived; use the active artcraft repository. | Not detected |
| [point-generator](https://github.com/storytold/point-generator/blob/master/README.md) | Generate ZeroMQ points for Unreal point-cloud demo. README describes Windows Rust zmq vendored libraries and historical vcpkg/CMake attempts; no consumer package. | **Exclude: deprecated demo.** Organization description marks it deprecated; developer demo rather than app. | Not detected |
| [realtime-voice-conversion](https://github.com/storytold/realtime-voice-conversion/blob/master/README.md) (archived) | Rust audio IO with Python CycleGAN sidecar. Python sidecar, CUDA optional selection, protoc generation; README lacks complete consumer install. | **Exclude: archived experiment.** Archived; README records accumulating 4.39–6 second latency. Not suitable as Maslow Voice baseline. | Not detected |
| [redirect-vocodes](https://github.com/storytold/redirect-vocodes/blob/master/README.md) | Netlify redirect configuration. No app install; repository config redirects vo.codes to fakeyou.com. | **Exclude.** Website infrastructure only. | Not detected |
| [RuntimeAudioImporter](https://github.com/storytold/RuntimeAudioImporter/blob/main/README.md) (fork) | Unreal runtime audio import plugin. Root README links external plugin documentation; use inside Unreal project. | **Developer resources.** MIT fork; no standalone desktop installation. | MIT |
| [RuntimeFilesDownloader](https://github.com/storytold/RuntimeFilesDownloader/blob/main/README.md) (fork) | Unreal HTTP download plugin. Root README links external plugin documentation; use inside Unreal project. | **Developer resources.** MIT fork; no standalone desktop installation. | MIT |
| [spark](https://github.com/storytold/spark/blob/main/README.md) (fork) | THREE.js Gaussian-splat renderer library. npm install @sparkjsdev/spark; examples: npm install, npm run build, npm start; Rust builds WASM. | **Developer resources.** A web-development library/fork, not a standalone creative desktop editor. Could support a future viewer but would be separate product work. | MIT |
| [storyteller-bevy](https://github.com/storytold/storyteller-bevy/blob/main/README.md) | Bevy/WASM studio prototype. Rust, Node LTS, npm ci, wasm32 target; npx nx serve studio-frontend. | **Prototype watchlist.** Development server/workspace rather than a release installer. | Not detected |
| [storyteller-ml](https://github.com/storytold/storyteller-ml/blob/master/README.md) | Machine-learning monorepo. Root README points to _develop and project-specific documentation; no root install procedure. | **Specialist research only.** Research components, not an end-user application. | Not detected |
| [StreamTwo](https://github.com/storytold/StreamTwo/blob/master/README.md) | Unreal Twitch-stream project. README says install other plugins; links Xsens integration notes. | **Exclude: project/asset review needed.** Project assets rather than app; README mentions third-party game assets, so do not assume redistribution rights. | Not detected |
| [terraform-aws-observability-accelerator](https://github.com/storytold/terraform-aws-observability-accelerator/blob/main/README.md) (fork) | AWS observability Terraform modules. Consume pinned module sources and apply to existing AWS/EKS/Grafana setup; Terraform>=1.1. | **Specialist infrastructure only.** Cloud infrastructure with resource/account costs; no local end-user app. | Apache-2.0 |
| [torchscript-models](https://github.com/storytold/torchscript-models/blob/master/README.md) | Convert PyTorch models into TorchScript. README gives scripting/tracing development guidance rather than a package install. | **Developer resources.** Developer utility material; no consumer workflow or MCP documented. | Not detected |
| [UE4-OSC](https://github.com/storytold/UE4-OSC/blob/master/README.md) (archived) (fork) | OSC messaging plugin for Unreal4. Put OSC in project Plugins, open C++ project and compile with Visual Studio2015 or Xcode. | **Exclude: archived plugin.** Archived MIT fork for older engine versions. | MIT |
| [UnrealZeroMQ](https://github.com/storytold/UnrealZeroMQ/blob/master/README.md) (fork) | Unreal ZeroMQ bindings. Copy into project Plugins, enable plugin, add ZeroMQ to module dependencies. | **Developer resources.** Lists Linux/Windows/macOS, but engine component rather than app. License metadata absent. | Not detected |
| [vits-finetuning](https://github.com/storytold/vits-finetuning/blob/main/README.md) | TTS model training/export. Python requirements, espeak, datasets; python train.py; export_ts.py and infer_ts.py. | **Specialist research only.** Training/model workflow; documented training uses approximately 11–14GB VRAM. Could be researched independently for Voice, but provides no turnkey realtime Voice or MCP integration. | MIT |
| [voder-proxy](https://github.com/storytold/voder-proxy/blob/master/README.md) (archived) | TTS backend request router. No installation procedure in root README. | **Exclude: archived infrastructure.** Archived backend component. | Not detected |
| [xsens-packet-send](https://github.com/storytold/xsens-packet-send/blob/master/README.md) | Replay recorded Xsens packets into Unreal. Rust/MSVC on Windows; cargo run or cargo build --release; --file and --host options. | **Specialist investigation only.** Niche packet replay utility with Windows-focused instructions, no reviewed Linux install. No license detected in org metadata. | Not detected |

No MCP support was documented in the reviewed READMEs for these 44 projects. The supporting repositories may still be valuable build/test inputs or development resources; that does not make them installable consumer applications.



## Outcome and next action

The research supports a bounded experimental offering, not wholesale inclusion of all Storytold repositories. The next concrete implementation is a PdfCraft and PhotoCraft package-and-MCP proof on a disposable Maslow installation, using fixed versions, project-scoped access and the existing install/Connect conventions. Measure successful user tasks before expanding the catalog.

This session changes research documentation only. No dependency, public API, schema, deployment setting, credential, installed application or release channel was changed; nothing was published. Documentation verification checks inventory coverage, source paths/revisions and whitespace. Application builds and runtime tests remain the next implementation phase.
