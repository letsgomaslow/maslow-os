# Maslow OS native Lenovo checkpoint and next-ISO handoff

## Checkpoint scope

This checkpoint records the accumulated source work after the first native Lenovo Yoga installation. It intentionally stops manual troubleshooting and configuration on that laptop. No repository change in this checkpoint was pushed, published, built into a new ISO, written to USB, or deployed to the Lenovo.

The first internal x86 ISO installed and completed setup successfully on the Lenovo. Its initially empty online pacman database state caused normal post-install package lookups to report missing `core`, `extra`, `multilib`, and `omarchy` databases and missing targets. Running the supported `omarchy update` path on that installed laptop repaired its current state, after which VS Code, ChatGPT Desktop, Hermes, and Tailscale installed successfully. That manual repair is evidence about the failure mode, not fresh-install proof of the source fix below.

Google Chrome was installed and selected as default manually on the Lenovo. The runtime source now selects Chrome after the existing optional Chrome installer succeeds, but the fresh ISO still has no proven source path that installs Google Chrome by default. Do not describe Chromium as satisfying this requirement.

Speech and dictation are deferred for this low-spec test laptop. Do not resume Voxtype diagnosis as part of the next ISO iteration.

## Recorded source commits

### Runtime: `letsgomaslow/maslow-os`, branch `main`

- `7c74e232c330da46cff4cb1502a76263091ca93b` — Guard Maslow runtime package ownership.
- `994b8dc296c2a52222b96c4116b605ff1436b334` — Make AI onboarding configuration first.
- `8a03d1ab59751d4f57d72d35ed5591192eee8ab3` — Add guarded performance diagnostics.
- `00217123e04f4774348e85224aec396bef0cccd2` — Document AI image and plugin acceptance gates.
- `28dfd19d42cd00d5eee582d847354cf665c5c6a2` — Use the Maslow glyph in the shell menu.
- `53b4f43a9bd1216daca56a6fd914588e4f50d89e` — Select Chrome after optional installation.

### Packages: `letsgomaslow/maslow-os-pkgs`, branch `maslow`

- `ce628a5e89c76537a82d576b52c4b333a13bb4f3` — Package the Maslow runtime hold hook.
- `1b6198f8c30d82c0f384f00e024964be12d35023` — Package the preinstalled AI core.

### Installer: `letsgomaslow/maslow-os-iso`, branch `maslow`

- `b4b57d0c73060306dcbb1d949b2fceebe9403aa5` — Complete the offline package handoff.
- `44048ea5817d88d230eb4089f920d117f548202f` — Expand installed-image AI acceptance coverage.
- `141decb036cc6bb34d4af95a392088d774f1799b` — Exercise media diagnosis through a real PTY.

The handoff document itself is committed separately after these code commits so its final commit can be reported without trying to embed its own hash.

## Online pacman database fix

Installer commit `b4b57d0c73060306dcbb1d949b2fceebe9403aa5` stages nonempty, readable `core`, `extra`, `multilib`, and `omarchy` database archives from the exact `/tmp/offlinedb` synchronization used to resolve and download the frozen offline mirror. The orchestrator copies those archives into the installed target's `/var/lib/pacman/sync` before the finalizer restores the normal online `pacman.conf`. This avoids an empty offline-to-online handoff without introducing a plain `pacman -Sy`, bypassing the Maslow runtime hold, or mixing database and package snapshots inside the build.

The implementation and fixtures passed focused source-level checks, but it has not been built into a new ISO or proven by a fresh native install. Normal post-install operation should still use the supported full `omarchy update` transaction; a copied database cache is not a substitute for the regular update lifecycle.

## Focused verification at checkpoint

- Runtime changed-area tests completed under the cached Linux x86 test image: runtime hold, channel switching, default applications, Hermes CLI ownership, AI onboarding state and panel behavior, performance diagnostics, preinstalled-agent handling, AI tool adapters, and the Maslow brand guard all reached their passing assertions.
- Packages `test/ai-core-packaging` and `test/maslow-packaging` passed. `test/hermes-installed-isolation` was not claimed because this checkpoint did not build and install a Hermes package into `/usr/bin/hermes`.
- ISO `test/unit/local-packages-test.sh`, `test/unit/online-pacman-databases-test.sh`, and `test/unit/integration-qemu-config-test.sh` passed under the cached Linux x86 test image.
- ISO `python3.13 -m unittest test.unit.test_pacman_handoff` passed all three tests, and `phases_impl.py` plus its handoff test compiled successfully.
- ISO media-diagnosis logic passed every functional case through the missing-log case. The final dashboard 40-row PTY assertion could not initialize its terminal-size fixture inside the container and therefore remains unverified in this checkpoint; this is recorded as an environment limitation, not converted into a pass.
- `git diff --check` passed in all three repositories before the commits.
- No full repository aggregate suite, package build, ISO build, VM run, visual deployment check, USB write, or native fresh-install test was run for this bounded checkpoint.

## Next ISO priorities

1. Make Google Chrome, not Chromium, installed and selected by default on a fresh ISO. First verify the existing approved package route, redistribution or license boundary, dependency closure, desktop file, and default-browser behavior. Commit `53b4f43a9bd1216daca56a6fd914588e4f50d89e` only selects Chrome after the optional installer succeeds; it does not satisfy fresh-image installation.
2. Preserve and validate the staged online pacman database handoff. Build from the exact coordinated runtime, package, and ISO commits, then prove a fresh target starts with usable online databases and can complete the supported full update and install ordinary packages without a manual database recovery.
3. Install and configure both Omadock (`omadock`) and Tyrsolution App Launcher (`tyrsolution.app-launcher`) as fresh-image defaults from reviewed, pinned upstream revisions. The native Lenovo plugin state was configured manually and does not prove source bundling. Preserve upstream IDs, authors, licenses, themes, update ownership, and removal behavior.
4. Bind the App Launcher to `Super+A`, which was confirmed unused in the complete native keybinding output. Preserve `Super+Space` for the Maslow menu, `Super+Alt+Space` for Apps, and `Super+Shift+A` for ChatGPT.
5. Keep the top-left first-party menu glyph change from upstream-compatible U+E900 to approved Maslow U+E90B. It exists in source with a passing brand assertion but has not been deployed. Omadock separately hardcodes U+E900 and an Omarchy tooltip; make the smallest maintainable downstream display-brand adjustment while retaining the plugin's upstream identity and compatibility.
6. Allow only a small AI onboarding UI and UX pass that configures the preinstalled infrastructure. Prioritize Codex, Claude Code, and Hermes. Keep software installation, provider sign-in, and high-permission consent as separate states. Treat Bitwarden as a provider-owned vault, never a Maslow secret store. Avoid a broad redesign.
7. Preserve the finalized Maslow appearance and every Omarchy command, package, update, and plugin contract. Keep the runtime/settings package hold temporary and explicit until a supported signed Maslow update channel and rollback path exist.
8. Build, checksum, write, and verify the next exact ISO only after focused source/package/installer tests pass. Then perform a genuinely fresh native Lenovo install and verify first boot, online update/package installation, Chrome default, plugin defaults and keybindings, dock/menu branding, onboarding behavior, and update/reboot preservation. Do not call the result stable or released without Maslow-owned signing, repository publication, update, and rollback infrastructure.

## Remaining risks and boundaries

- The current commits are local only and have not been pushed or reviewed through pull requests.
- The online pacman database fix is source-tested but not fresh-image or native-hardware verified.
- Google Chrome default installation remains an explicit product requirement with unresolved packaging and redistribution evidence.
- Omadock and App Launcher default bundling, source pinning, source-level configuration, performance, theme switching, and removal remain unproven.
- The Maslow menu glyph source change and the separate dock branding change have not been visually verified on the native candidate.
- Existing historical VM or candidate-image observations do not replace a new ISO built from these exact commits.
- No signing, repository publication, update, or rollback infrastructure is established well enough to support a public stable claim.

## Pasteable fresh-session prompt

```text
Continue the next bounded Maslow OS x86 ISO iteration from this durable checkpoint:

- Runtime repo: /Users/r.david/Documents/Maslow-Propriotory-Repos/Maslow OS - Linux, branch main, code HEAD 53b4f43a9bd1216daca56a6fd914588e4f50d89e plus the later handoff-only commit containing docs/handoffs/2026-09-05-native-lenovo-next-iso.md.
- Packages repo: /Users/r.david/Documents/Maslow-Propriotory-Repos/Maslow OS - Packages, branch maslow, HEAD 1b6198f8c30d82c0f384f00e024964be12d35023.
- ISO repo: /Users/r.david/Documents/Maslow-Propriotory-Repos/Maslow OS - ISO, branch maslow, HEAD 141decb036cc6bb34d4af95a392088d774f1799b.

Read every repo's AGENTS.md and the matching task guides before editing. Read the handoff document in full. Start with read-only status/log verification and preserve any new user changes. Use focused cost-efficient subagents only for genuinely independent investigation, and keep the main agent responsible for integration and verification.

This is a minimal next-ISO implementation and validation pass, not a redesign or public release. Do not manually troubleshoot or configure the Lenovo, do not resume Voxtype work, and do not erase disks or write a USB until the user explicitly authorizes the exact device for that later action.

First priority: make Google Chrome, not Chromium, installed and selected by default on a fresh ISO. Verify the existing approved package source, redistribution/license boundary, dependency closure, desktop entry, and default-browser path before implementing; do not assume the current optional installer change is enough and do not invent or redistribute an unreviewed proprietary package recipe.

Then preserve and validate ISO commit b4b57d0c73060306dcbb1d949b2fceebe9403aa5, which stages the exact synchronized core/extra/multilib/omarchy database archives used for the offline mirror and seeds the target before the normal online pacman.conf is restored. The previous Lenovo was repaired by running supported omarchy update, but that is not proof of this source fix. Never suggest plain pacman -Sy, bypass the runtime hold, disable signing, or mix package/database snapshots.

Install and configure Omadock (ID omadock) and Tyrsolution App Launcher (ID tyrsolution.app-launcher) as fresh-image defaults using reviewed pinned upstream revisions. Preserve upstream IDs, authors, licenses, themes, update ownership, and removal. Configure Super+A for App Launcher; preserve Super+Space Maslow menu, Super+Alt+Space Apps, and Super+Shift+A ChatGPT. The plugins were installed and enabled manually on the old Lenovo, so default source bundling remains unproven.

Preserve runtime commit 28dfd19d42cd00d5eee582d847354cf665c5c6a2: the first-party top-left menu uses approved Maslow glyph U+E90B while U+E900 remains available for upstream compatibility. Omadock separately hardcodes U+E900 and an Omarchy tooltip; apply the smallest maintainable visible-brand adjustment without renaming or forking its upstream identity. Run automated brand checks and real visual verification before acceptance.

A small AI onboarding UI/UX pass is allowed only to configure preinstalled infrastructure. Prioritize Codex, Claude Code, and Hermes; keep install, sign-in, and permission consent separate; Bitwarden is not a Maslow secret store. Speech/dictation is deferred. Preserve finalized appearance and Omarchy command/package/update/plugin contracts.

Validate in dependency order: runtime, packages, then ISO. Run focused tests first. Build from exact recorded local commits, record source revisions, build logs, artifact size and SHA-256, then verify the written medium and perform a truly fresh native x86 install only when separately authorized. Fresh-native acceptance must cover initial online package databases, supported full update, an ordinary package install, Chrome installed/default, both plugins and keybindings, dock/menu branding, onboarding, and update/reboot preservation. Historical VM evidence and the manually repaired Lenovo do not qualify. Do not push, publish, sign, or claim stable/release readiness without explicit approval and working Maslow-owned signing, repository publication, update, and rollback infrastructure.

Make minimal atomic changes in the owning repositories, preserve unrelated work, and report exact commits, tests, limitations, and remaining native gates.
```
