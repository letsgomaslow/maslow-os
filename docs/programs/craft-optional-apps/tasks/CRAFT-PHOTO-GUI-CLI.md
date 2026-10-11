# CRAFT-PHOTO-GUI-CLI

Objective: Verify packaged photocraft GUI/CLI and file fidelity

Repository: packages. Phase: 1.

Permitted files: docs/programs/craft-optional-apps/tasks/CRAFT-PHOTO-GUI-CLI.md. Coordinator owns ledger and shared integration.

Dependencies: CRAFT-PHOTO-PACKAGE.

Acceptance: Fresh optional install before OS update, offline GUI/CLI, upgrade/remove/reinstall, app-specific save/reopen fidelity, VM/Lenovo evidence

Attempt history: not dispatched. No completion or test claims.

Next action: Verify packaged photocraft GUI/CLI and file fidelity

## Dispatch, 2026-10-11

Worker /root/pilot_gui, actual gpt-6.1-sol medium. Own this report only; all source/package/ledger changes remain with coordinator/other owner. Execute bounded normal GUI/CLI and basic save/reopen fidelity in disposable Docker with headless Weston/XWayland/software rendering. Build/test artifacts under `/home/maslow/Maslow-ai-os/craft-build/gui/`, no host app install, session configuration, accounts, real documents or mouse/keyboard changes. Package worker final f211378; exact app archives/hashes in package report and candidate manifest. Source isolation is separately blocked on reproduced defects; GUI result does not waive it. Fresh Maslow/Hyprland/VM/Lenovo and advanced fidelity gates remain explicitly unverified if this worker cannot run them.

Heavy builder slot is released by coordinator; use sequential app checks, retain derived image/fixtures/screenshots with exact hashes and inspect actual images. Return precise partial acceptance facts, blockers and tests without marking app or whole GUI task complete when physical/VM gates remain.

## Bounded installed GUI/CLI evidence, 2026-10-11

Worker `/root/pilot_gui`, actual `gpt-6.1-sol` medium; runtime branch `codex/craft-optional-apps`, dispatch baseline `be34e89e`. No source/recipe/ledger changes. Result: bounded disposable-container startup and synthetic lossless round-trip checks pass; full task acceptance remains incomplete. Normal GUI evidence does not establish source confinement or MCP isolation.

Exact input is installed `photocraft 0.7.0-1`, final recipe `f211378f416f50d63d4352b2049758a7aaa0996e`, archive `/home/maslow/Maslow-ai-os/craft-build/photo/photocraft-0.7.0-1-x86_64.pkg.tar.zst`, SHA-256 `22c553446baae55603c202a4090340961044cd779d3084c2a687eb0b9a5a92c5`, upstream tag commit `79261615956ab21334e49ca1d384390272e647da`. Pacman installed the exact archive offline and confirmed `/usr/bin/photocraft` and `/usr/bin/photocraft-cli` ownership.

Runtime: disposable Arch Docker with synthetic `builder` UID 1000 home, `--network none`, exact package archives mounted read-only and synthetic evidence directory writable. No host home, desktop/audio/session sockets, accounts, real documents or GPU binds. Retained image `maslow-craft-gui-dialog:2026-10-11` ID `sha256:a39edba2b12dbb5c700ec86b15eb442b2d7254d65d13dc14398a220e7ff86bdd`; parent GUI image `sha256:368efd77939fc52de190826ec661669bc7d99d3854fdb3cbc78ae686068c429a` extends retained Connect builder. Only dependency retrieval during image build used network. Xvfb `21.1.25-1`, 1440×1000, Mesa `26.2.4-1` llvmpipe software GL; Weston `15.0.1-3` nested x11 backend/pixman output 1400×950 for native Wayland clients with `DISPLAY` removed. DejaVu/fontconfig installed. This is not fresh Maslow/Hyprland VM or Lenovo proof. Both retained GUI containers were stopped after tracked children cleanup; PDF and Photo checks ran sequentially.

Verified CLI: version, `info` on known 320×240 RGB PNG with red/green/blue/yellow quadrants, conversion to native `.pcraft`, native `info`, conversion back to PNG. Dimensions and every RGBA byte match original using Pillow assertions. Synthetic source PNG SHA-256 `70622d29341425f9391fb2b8a63dc1204d2843f5f081c47e8ede3cc2e9b3b45a`. `cli-verification.json` SHA-256 `5911696f27082f5783b648b6dd108ff778b58ab5f588924b772bd6eae68a5f92` records this and the separate PDF fixture assertions.

Verified GUI: captured actual PNGs inspected using `view_image`. Initial X11 native-file open displays all four quadrants, readable menus/tools/properties and one Background layer at 320×240. Software-only startup presented `Switched to CPU rendering`; expanded details said `No compatible hardware graphics adapter; using software graphics`. `Keep Using CPU` dismissed it and left the fixture usable. This does not establish hardware acceleration or acceptable performance. Later launches used `--safe-gpu` and software window rendering.

Isolated Ctrl+Shift+S, zenity Name field and visible OK control saved `/home/maslow/Maslow-ai-os/craft-build/gui/photo-gui-saved.pcraft`, SHA-256 `fefbfbe00f936bf7e924da9a6a3cecc7adc9dcb87825f3a636e450e248032bd5`. Fresh-process X11 and native Wayland reopen display the same quadrants/properties/layer. Native document internal name remains `known.png`; the bottom status reports actual opened `.pcraft` path. GUI-saved native file converted to `photo-gui-saved-export.png`, SHA-256 `899a4500b92c8b6a751f3e0f77c852f1a3ed71784d5e1515d6aed2797f376e32`; every RGBA byte and dimensions equal original. This covers one flat synthetic raster, not general layered/color-managed fidelity.

Inspected screenshots under `/home/maslow/Maslow-ai-os/craft-build/gui/`:

| PNG | SHA-256 |
| --- | --- |
| `photo-cpu-open.png` | `2c19f827d57eb09152b1f1f7ee108cb9dd0b5ba6c95655652a19b7d31dc0b338` |
| `photo-save-dialog.png` | `fb73bcfa44585d72b232eba97c6c448d99feacf09bb42e811ca08c6fb6d9e682` |
| `photo-gui-reopened.png` | `088817f10c6a5cdfd4e31b7ed960f66515471de242726f6e1ea6c1fdef4a71bb` |
| `photo-open-wayland.png` | `8134c23972d05d3107be8dd881d0891c9a4bbd7136e7905f02f799ae64b7fac6` |

Observed capability limits: native Wayland screenshot explicitly reports `Native file drag-and-drop is not supported on Wayland yet` and suggests File > Open; exact tag startup log says tablet pressure unavailable on Wayland. Clipboard initialization failed because this Weston lacks ext-data-control/wlr-data-control and no X11 clipboard was exposed to the Wayland app; clipboard remains unverified. Native portal was not available, so verified save uses container-only zenity fallback with `GSK_RENDERER=cairo`; native xdg portal acceptance remains open. No claim that all GUI operations or displays work follows from startup/save.

Retained commands/fixtures/images/logs/hashes: `Dockerfile`, `Dockerfile.dialog`, `installed-tests.sh`, `fixtures.py`, `cli-tests.sh`, `x11-launch.sh`, `wayland-startup.sh`, `verify-fidelity.py`, `reproduce.txt`, output files, app/runtime/install/image logs, `runtime-versions.txt`, ownership, container configuration and `SHA256SUMS`. A control rehearsal clicked a canvas after the CPU notice was already dismissed, producing an unsaved brush mark; no output file was rewritten. The accepted reopened screenshot was recaptured from a fresh process without input; it has no dirty marker, and file fidelity assertions use saved bytes. Coordinator's earlier install/remove/reinstall/preservation checks remain separate evidence.

Remaining gates: exact fresh Maslow optional install before OS update, Hyprland/portal/scaling/clipboard and Lenovo, hardware acceleration/tablet behavior, representative layered PSD/TIFF, alpha/color profiles/high-bit-depth/RAW/HEIF and native project fidelity, separate confinement/MCP/selected-agent/Voice gates. Next action: coordinator review this bounded evidence and preserve explicit Wayland drag-drop/tablet limitations, then run exact installed VM/Lenovo and representative corpus acceptance. This task/app is not candidate-ready.
