# CRAFT-PDF-GUI-CLI

Objective: Verify packaged pdfcraft GUI/CLI and file fidelity

Repository: packages. Phase: 1.

Permitted files: docs/programs/craft-optional-apps/tasks/CRAFT-PDF-GUI-CLI.md. Coordinator owns ledger and shared integration.

Dependencies: CRAFT-PDF-PACKAGE.

Acceptance: Fresh optional install before OS update, offline GUI/CLI, upgrade/remove/reinstall, app-specific save/reopen fidelity, VM/Lenovo evidence

Attempt history: not dispatched. No completion or test claims.

Next action: Verify packaged pdfcraft GUI/CLI and file fidelity

## Dispatch, 2026-10-11

Worker /root/pilot_gui, actual gpt-6.1-sol medium. Own this report only; all source/package/ledger changes remain with coordinator/other owner. Execute bounded normal GUI/CLI and basic save/reopen fidelity in disposable Docker with headless Weston/XWayland/software rendering. Build/test artifacts under `/home/maslow/Maslow-ai-os/craft-build/gui/`, no host app install, session configuration, accounts, real documents or mouse/keyboard changes. Package worker final f211378; exact app archives/hashes in package report and candidate manifest. Source isolation is separately blocked on reproduced defects; GUI result does not waive it. Fresh Maslow/Hyprland/VM/Lenovo and advanced fidelity gates remain explicitly unverified if this worker cannot run them.

Heavy builder slot is released by coordinator; use sequential app checks, retain derived image/fixtures/screenshots with exact hashes and inspect actual images. Return precise partial acceptance facts, blockers and tests without marking app or whole GUI task complete when physical/VM gates remain.

## Bounded installed GUI/CLI evidence, 2026-10-11

Worker `/root/pilot_gui`, actual `gpt-6.1-sol` medium; runtime branch `codex/craft-optional-apps`, dispatch baseline `be34e89e`. No source/recipe/ledger changes. Result: the bounded disposable-container checks pass; this task's full acceptance remains incomplete. Source confinement is a separate gate and is not established by normal GUI execution.

Exact input is installed `pdfcraft 0.6.0-1`, final recipe `f211378f416f50d63d4352b2049758a7aaa0996e`, archive `/home/maslow/Maslow-ai-os/craft-build/pdf/pdfcraft-0.6.0-1-x86_64.pkg.tar.zst`, SHA-256 `afa9eb1146696fd1feb0840fdbd8a6b3dc5cec6751dd86d6198b07a826f445c2`, upstream tag commit `53a5880386789fc3531e54f6e6ffdef9a8e41f1a`. Pacman installed the exact archive with networking disabled and confirmed ownership of `/usr/bin/pdfcraft` and `/usr/bin/pdfcraft-cli`.

Runtime: disposable Arch Docker, synthetic `builder` UID 1000 home, Docker `--network none`, read-only exact archive binds and writable synthetic evidence directory only. No host home, desktop/audio/session sockets, accounts, real documents or GPU binds. Derived image `maslow-craft-gui-dialog:2026-10-11` ID `sha256:a39edba2b12dbb5c700ec86b15eb442b2d7254d65d13dc14398a220e7ff86bdd` extends retained Connect builder; its parent GUI image ID is `sha256:368efd77939fc52de190826ec661669bc7d99d3854fdb3cbc78ae686068c429a`. Only image dependency retrieval used network. Xvfb `21.1.25-1` display 1440×1000, Mesa `26.2.4-1` llvmpipe/GL, DejaVu/fontconfig; nested Weston `15.0.1-3` x11 backend/pixman output 1400×950 accepted native Wayland clients with `DISPLAY` removed. This is neither a fresh Maslow/Hyprland VM nor Lenovo acceptance. Both retained GUI containers were stopped after tracked child cleanup.

Verified CLI: `--version`, known one-page 400×300 pt Helvetica fixture `info`/`text`/`render` (96 dpi, 534×400 PNG), then `edit --rotate 1:90 --title 'Verified fixture'`. App reopened output with one page, rotated dimensions and title; independent Poppler `pdfinfo` reported rotation 90/title and `pdftotext` preserved `Known text 12345`. Artifact `edited.pdf` SHA-256 `dc0eade21d1b1b3a6a9084f27489b3313b9d3a5783d60f949a44510dbc5bfbcc`. No complex-document fidelity inference follows from this small fixture.

Verified GUI: actual captured PNGs inspected with `view_image`. X11 open shows both known text lines, readable menus/icons and system font fallback; Save As via isolated Ctrl+Shift+S and zenity Name/OK controls created `/home/maslow/Maslow-ai-os/craft-build/gui/pdf-gui-saved.pdf`. New-process reopen shows the same fixture and actual saved tab name. Saved PDF SHA-256 `7385195b0c63dbc1663fb1a440e4c4619e5b5d797147008e1d7323eb7f75922d` is byte-identical to source; CLI text also matches. Native Wayland startup shows rotated saved CLI output; the selected 235% zoom places part of the page beyond the viewport, so this capture is startup/rotation evidence rather than full-page-fit acceptance. UI reports software rendering honestly.

Inspected screenshots under `/home/maslow/Maslow-ai-os/craft-build/gui/`:

| PNG | SHA-256 |
| --- | --- |
| `pdf-open-x11.png` | `ba828b8c6c4955add559034ce711d63b5c6811b00ab617c23715eaf5caf79f85` |
| `pdf-save-dialog-fallback.png` | `5a76fd2ac0f12ff6f3e3a2fb2b1ef4d323bb4f29a19d10660bf17b7698b9bd34` |
| `pdf-gui-reopened.png` | `009fc2a97a2df70cd70a3621afeb7cbd9874764ffb05ed9f6b72849a5221f8f9` |
| `pdf-open-wayland.png` | `5283533ee49204af658bdd398c4052875eb9269e54f85a2d35f5b982c91a3cc9` |

Environment limitations observed, not hidden: original image lacked session portal and zenity, so Save As logged portal failure and missing fallback; adding container-only zenity made fallback work. GTK4's initial software dialog capture was black; `GSK_RENDERER=cairo` rendered its actual controls correctly. Native xdg-desktop-portal integration remains untested. Native Wayland clipboard initialization fails in this Weston environment without an available X11 clipboard; clipboard behavior remains unverified. Xvfb warnings about zero physical display size/XSETTINGS are recorded.

Retained reproducibility/evidence: `Dockerfile`, `Dockerfile.dialog`, `installed-tests.sh`, `fixtures.py`, `cli-tests.sh`, `x11-launch.sh`, `dialog-actions.sh`, `wayland-startup.sh`, `verify-fidelity.py`, `reproduce.txt`, exact output/JSON/text/PNG files, image/install/runtime/application logs, `runtime-versions.txt`, binary ownership, container configuration and `SHA256SUMS` in that directory. Coordinator's separately recorded install/remove/reinstall/mtree preservation checks are not worker GUI evidence.

Remaining gates: fresh optional install before first OS update in exact Maslow VM, Hyprland/native portal/scaling/clipboard behavior, Lenovo, representative PDF fonts/forms/encryption/annotations/printing/complex fidelity, and separate confinement/MCP/selected-agent/Voice gates. Next action: coordinator review this evidence, then run exact installed Maslow VM/Lenovo and representative corpus acceptance. Do not mark this task or app candidate-ready from these container checks.
