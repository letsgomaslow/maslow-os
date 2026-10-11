# CRAFT-PHOTO-PACKAGE

Objective: Evaluate pinned photocraft 0.7.0 release archive, ABI, notices and native package

Repository: packages. Phase: 1.

Permitted files: pkgbuilds/photocraft/**. Coordinator owns ledger and shared integration.

Dependencies: CRAFT-P0-GATE.

Acceptance: Reviewed archive hash/source tag, clean build/contents/deps/ownership; same-tag locked fallback or evidenced deferral

Attempt history: not dispatched. No completion or test claims.

Next action: Evaluate pinned photocraft 0.7.0 release archive, ABI, notices and native package

## Dispatch 1, 2026-10-11

Worker /root/craft_packages; actual model gpt-6.1-sol, medium. Worktree `/home/maslow/Projects/Maslow/craft-packages`, branch `codex/craft-packages`, base `448856485e710caedfc24f544a027aea8652dd33`. Build PDF then Photo sequentially. Own only named app recipe directories; coordinator owns `pkgbuilds/maslow-connect/**` and ledger. Artifact/build directories outside source. Do not install on host or change base payload; record hash/tag/ABI/deps/notices and any same-tag fallback blocker.

## Implementation checkpoint, 2026-10-11

Recipe and supplemental notices prepared in `pkgbuilds/photocraft/`; package `photocraft 0.7.0-1` consumes official Linux x86_64 release tarball. Exact tag `v0.7.0` resolves to `79261615956ab21334e49ca1d384390272e647da` (research main revision is not an input). Archive SHA-256 `641f831252fd31b43ee1a12e572d7442e5652c2e5bf623de085741c370f0c91d` matches the official GitHub API asset digest; this is same-publisher integrity evidence, not independent publisher trust. Raw release/tag API JSON and source/asset bytes are retained outside Git at `/home/maslow/Maslow-ai-os/craft-build/photo/`.

Archive members inspected before extraction: no absolute paths, parent traversal, symlinks, hard links or devices. Recipe repeats safety validation with Python before extraction. Stable GUI and CLI are direct ELF `/usr/bin/photocraft` and `/usr/bin/photocraft-cli`; original desktop, icon, MIME and AppStream assets retained. NEEDED libraries are libgcc_s, libc, libm and ld-linux; max GLIBC symbol 2.35. Arch GUI dependencies cover dlopen X11/Wayland, OpenGL/Vulkan and fonts. Actual installed shared-library ownership and unpacked smoke checks remain to be captured in clean build logs.

Code licenses/craft-fonts notices remain in upstream documentation and `/usr/share/licenses/photocraft`. Added exact-tag NOTICE, ATTRIBUTION, branding and asset font/icon notices; epaint_default_fonts 0.36.2 default-font notices come from crate bytes matching Cargo.lock SHA-256 `773fa9c96dd0dbef887e39d0ed6177f141cce4d68e6041df77570aa3702dfa13`. App icons have independent MIT/Apache permission; restricted ArtCraft branding is preserved unmodified within upstream binaries. No base/ISO payload changes or host installs.

Clean disposable Docker builder bootstrap is active, based on `omarchy-pkg-builder:latest-x86_64-edge` image ID `sha256:b31326ed586c849b305eda5cc0f20fd7a152543fc1545568e5c72b43d8e9bfac`; dependency upgrades are inside this builder only. Package builds remain sequential PDF then Photo. Repository `./test/maslow-packaging`, recipe Bash syntax, and `git diff --check` pass. Package build/output hashes/MCP evidence are pending; this checkpoint does not establish task completion or candidate readiness.

## Implementation complete, 2026-10-11

Package commits `7d8dfd1` and `f211378f416f50d63d4352b2049758a7aaa0996e` (final recipe). Clean unprivileged Docker makepkg completed twice; final rebuild followed supplemental font-notice trailing-space normalization only. Package `/home/maslow/Maslow-ai-os/craft-build/photo/photocraft-0.7.0-1-x86_64.pkg.tar.zst`, SHA-256 `22c553446baae55603c202a4090340961044cd779d3084c2a687eb0b9a5a92c5`. Final builder `maslow-craft-package-builder:2026-10-11`, image ID `sha256:7dea3c778f143fdf8997ed13156fcbfcfd0760f6c9ad0b5225b741a4183e09f2`; builder logs/ownership under `craft-build/builder/`. This is a clean disposable container packaging build, not Rust source compilation.

Checks pass: source/archive SHA-256 validation, package generation, original 20 release-file content hashes preserved, desktop-file-validate, readelf/ldd with no missing libraries, CLI version 0.7.0/help, no-network unpacked MCP initialize and tools/list (server 0.7.0, 21 tools), package repository invariants, Bash syntax and whitespace validation. Final two-app ISO overlap check passes (`craft-build/builder/two-app-overlap.log`); coordinator must include final Connect artifact before full ownership acceptance. Unpacked package has 21 license notices. No separate external Photo runtime asset directory: fonts are embedded. Official release builds HEIF support; archive ELF has no dynamic libheif/libstdc++ dependency, so neither is imposed as a runtime dependency.

ELF NEEDED: glibc libc/libm/loader and libgcc_s; max GLIBC symbol 2.35. `craft-build/builder/ownership.log` SHA-256 `dc46a6af8da28e5273939aa1e12b3820c1570fdceeef348c276693d2ec743c9b` verifies glibc ownership and libgcc ownership (gcc-libs depends on libgcc), plus dynamic GUI runtime providers. Exact tag `apps/photocraft/src/linux_libs.rs` declares X11 providers libx11/libxcb/libxcursor/libxi/libxkbcommon/libxkbcommon-x11, Wayland provider wayland, and Vulkan/EGL providers vulkan-icd-loader/libglvnd. RandR goes through x11rb protocol, so libxrandr/libxrender are not Photo dependencies. Fontconfig supplies system font discovery. GUI acceptance remains separate.

Updater boundary: no self-updater found in exact-tag apps/crates source. `linux_libs.rs` contains sudo package-install strings only as printed missing-dependency advice; they are never executed (its process invocation reads `ldconfig -p`). No pkexec/sudo executable-replacement path, marker/env bypass, or AppImage delta-update metadata is present in the tar package. Pacman owns executable updates without depending merely on filesystem permissions.

Supplemental JetBrains Mono license has unchanged wording with a single trailing-space removal; original tag notice SHA-256 `a76abf002c49097d146e86740a3105a5d00450b1592e820a1109a8c5680cd697`, final packaged normalized SHA-256 `c1ab7c666206842a02b35b30770dac0d7a10156ed401c9defc3f02a754d89e90`. Initial staged whitespace validation exposed the upstream space; recipe checksum correction and rebuild resolved it. `craft-build/photo/notice-normalization.json` records the distinction. Final supplementary notice bytes match packaged files; all upstream archive files remain byte-identical.

No host installs/configuration changes; release archive passed content/CLI ABI checks, so same-tag source fallback was unnecessary. Remaining gates: final three-package overlap, disposable install/upgrade/remove/reinstall, GUI Wayland/XWayland/portal/font/offline startup, format fidelity, confinement, selected agents/Voice and exact ISO/fresh VM. Implementation-complete only; app candidate/release readiness is unverified. Next action: coordinator review/integrate, then installed-product gates.

Final evidence under `/home/maslow/Maslow-ai-os/craft-build/photo/`: exact-tag `source.tar.gz` SHA-256 `11bddc2a714139877f59f96c3d52a7510b718616fb4d2b4dec32e8c8eea827d2` (used for source inspection/notices, not compilation), final `build.log` `8c75d5a73612c9499ed6b986212f7809ea455eb6d82a24c5794fb6e01254e9f6`, `mcp-smoke.json` `fcc3f57cb663a6e00e0bff488a5d082e015d1c9c1dc4e34902cbccb4d8e95966`. Full release content manifest and notice normalization records are retained there.
