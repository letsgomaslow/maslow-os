# CRAFT-PDF-PACKAGE

Objective: Evaluate pinned pdfcraft 0.6.0 release archive, ABI, notices and native package

Repository: packages. Phase: 1.

Permitted files: pkgbuilds/pdfcraft/**. Coordinator owns ledger and shared integration.

Dependencies: CRAFT-P0-GATE.

Acceptance: Reviewed archive hash/source tag, clean build/contents/deps/ownership; same-tag locked fallback or evidenced deferral

Attempt history: not dispatched. No completion or test claims.

Next action: Evaluate pinned pdfcraft 0.6.0 release archive, ABI, notices and native package

## Dispatch 1, 2026-10-11

Worker /root/craft_packages; actual model gpt-6.1-sol, medium. Worktree `/home/maslow/Projects/Maslow/craft-packages`, branch `codex/craft-packages`, base `448856485e710caedfc24f544a027aea8652dd33`. Build PDF then Photo sequentially. Own only named app recipe directories; coordinator owns `pkgbuilds/maslow-connect/**` and ledger. Artifact/build directories outside source. Do not install on host or change base payload; record hash/tag/ABI/deps/notices and any same-tag fallback blocker.

## Implementation checkpoint, 2026-10-11

Recipe and supplemental notices prepared in `pkgbuilds/pdfcraft/`; package `pdfcraft 0.6.0-1` consumes official Linux x86_64 release tarball. Exact tag `v0.6.0` resolves to `53a5880386789fc3531e54f6e6ffdef9a8e41f1a` (research main revision is not an input). Archive SHA-256 `9a136e71e37b459ed5746dbe19a364ce84cf5d995c6f6c98af6147d818390a53` matches the official GitHub API asset digest; this is same-publisher integrity evidence, not independent publisher trust. Raw release/tag API JSON and source/asset bytes are retained outside Git at `/home/maslow/Maslow-ai-os/craft-build/pdf/`.

Archive members inspected before extraction: no absolute paths, parent traversal, symlinks, hard links or devices. Recipe repeats safety validation with Python before extraction. Stable GUI and CLI are direct ELF `/usr/bin/pdfcraft` and `/usr/bin/pdfcraft-cli`; original desktop, icon, MIME and AppStream assets retained. NEEDED libraries are libgcc_s, libc, libm and ld-linux; max GLIBC symbol 2.35. Arch GUI dependencies cover dlopen X11/Wayland, OpenGL/Vulkan and fonts. Actual installed shared-library ownership and unpacked smoke checks remain to be captured in clean build logs.

Code licenses/craft-fonts notices remain in upstream documentation and `/usr/share/licenses/pdfcraft`. Added exact-tag NOTICE, ATTRIBUTION, branding and asset font/icon notices; epaint_default_fonts 0.36.2 default-font notices come from crate bytes matching Cargo.lock SHA-256 `773fa9c96dd0dbef887e39d0ed6177f141cce4d68e6041df77570aa3702dfa13`. App icons have independent MIT/Apache permission; restricted ArtCraft branding is preserved unmodified within upstream binaries. No base/ISO payload changes or host installs.

Clean disposable Docker builder bootstrap is active, based on `omarchy-pkg-builder:latest-x86_64-edge` image ID `sha256:b31326ed586c849b305eda5cc0f20fd7a152543fc1545568e5c72b43d8e9bfac`; dependency upgrades are inside this builder only. Package builds remain sequential PDF then Photo. Repository `./test/maslow-packaging`, recipe Bash syntax, and `git diff --check` pass. Package build/output hashes/MCP evidence are pending; this checkpoint does not establish task completion or candidate readiness.

## Implementation complete, 2026-10-11

Package commits `7d8dfd1` and `f211378f416f50d63d4352b2049758a7aaa0996e` (final package recipe). Clean unprivileged Docker makepkg completed twice; the second build followed notice-only trailing-space normalization. Original release archive and every upstream executable/resource remain unchanged. Package `pdfcraft-0.6.0-1-x86_64.pkg.tar.zst` at `/home/maslow/Maslow-ai-os/craft-build/pdf/pdfcraft-0.6.0-1-x86_64.pkg.tar.zst`, SHA-256 `afa9eb1146696fd1feb0840fdbd8a6b3dc5cec6751dd86d6198b07a826f445c2`. Final builder image `maslow-craft-package-builder:2026-10-11`, image ID `sha256:7dea3c778f143fdf8997ed13156fcbfcfd0760f6c9ad0b5225b741a4183e09f2`; Docker bootstrap/build logs under `craft-build/builder/`. This is a clean disposable container packaging build, not a Rust source compilation.

Checks pass: archive/source checksum validation, package generation, original 28 release-file content hashes preserved, desktop-file-validate, readelf/ldd without missing libraries, CLI `--version` (0.6.0)/`--help`, no-network unpacked MCP initialize and tools/list (server 0.6.0, 143 tools), package repository invariants and Bash syntax. Two-app ISO overlap check passed on final rebuilt PDF+Photo artifacts; coordinator must rerun with final Connect artifact. Unpacked package preserves 23 license notices plus OCR model CC-BY-SA-4.0 notices beside model files. ABI maximum GLIBC_2.35. Exact Arch library ownership captured in `craft-build/builder/ownership.log` SHA-256 `dc46a6af8da28e5273939aa1e12b3820c1570fdceeef348c276693d2ec743c9b`: glibc owns libc/libm/loader, libgcc owns libgcc_s and is a dependency of gcc-libs; GUI providers are libx11, libxcb, libxcursor, libxi, libxrandr, libxrender, libxkbcommon, libxkbcommon-x11, wayland, libglvnd, vulkan-icd-loader and fontconfig.

Updater boundary verified in exact tag: `apps/pdfcraft/src/updates.rs` only requests release metadata; `crates/ui-egui/src/updates.rs` opens the release web page through egui, explicitly never downloads or installs. No sudo/pkexec executable replacement path or package marker is needed. Tar release has no AppImage delta-update metadata. Pacman remains update owner without relying only on root file permissions.

Supplemental font notices preserve license wording while removing one trailing space per affected line. Original→packaged SHA-256: JetBrains Mono `a76abf002c49097d146e86740a3105a5d00450b1592e820a1109a8c5680cd697` → `c1ab7c666206842a02b35b30770dac0d7a10156ed401c9defc3f02a754d89e90`; Dancing Script `6f090277c00af96651ce6dbcc38ff1591047a3bffef486e80b6a32e8276a8201` → `c02c0002d3bbd41a16933c162888c400469c7029f1362ca9d60d5ed20ea7d157`. Initial staged whitespace check found these upstream spaces; correction/checksum changes and rebuild resolved them. Adobe CMap crate SHA-256 matches tag lockfile `24d285dc30731c8485de5fa732fbdf2b3affdf01e4da7c2135022ca6fa664bf6`.

No host install or configuration change. Same-tag source fallback was not needed: archive contents/CLI ABI passed. Remaining gates: combined final three-package overlap, disposable install/upgrade/remove/reinstall, GUI Wayland/XWayland/portal/font/offline startup, fidelity, confined MCP, selected-agent/Voice and exact ISO/fresh VM. Status is implementation-complete only; app candidate/release readiness remains unverified. Next action: coordinator review package diff/evidence and integrate, then disposable installed-product testing.

Final evidence under `/home/maslow/Maslow-ai-os/craft-build/pdf/`: exact-tag `source.tar.gz` SHA-256 `eaf3fd20fbb6b9cc8a2c3a19be211622cb29cca23a1a987a6c62005640b03549` (used for source inspection/notices, not compilation), final `build.log` `1bd00cde77e99458329f9104a19b8e69cd3ca0d5524fdb5616adaec50e307cac`, `mcp-smoke.json` `039506ea242e4951f8315ffe2ed366d4cacae859786d1429d59e4b206eefd892`. Full release content manifest and notice normalization records are retained there.
