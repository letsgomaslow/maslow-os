# Maslow Hub implementation and acceptance checkpoint

Status: Internal engineering candidate complete. Hub implementation, migration rehearsal, graphical update/rollback on the preliminary ISO, corrected ISO assembly, exact artifact inspection, final fresh installation, and installed-guest screensaver fit are verified. This is not a publication or Lenovo hardware acceptance record. References below to native UI/captures mean real Quickshell/desktop rendering inside the headless guest, not observed Lenovo hardware; local evidence directory names are retained unchanged.

Follow-up: [verified USB and tester-reported Lenovo installation](2026-09-08-hub-usb-follow-up.md) records full USB readback and the user's subsequent confirmation that installation reached the desktop. It does not close itemized onboarding, security, recovery, or production delivery gates. Start new work from [development status and prioritized backlog](../maslow-development.md).

## Recorded inputs

- Preliminary runtime code: `960bb961353c0257788bc7705f2253bf0295ee10`. This includes the approved branding checkpoint `b69f785ffdd3e67959702f2a535056b0bcba8986`, cherry-picked without conflicts from its recorded parent `ae1041b4095637a2490674637e8b04cc8a4f565f`. Hub integration remains present.
- Package recipes: `c8506a142a37389f39006676e37ab89799f4e125`. Hub uses version-specific QML entry-point paths to prevent an existing QML engine from reusing older code after a plugin rescan.
- ISO builder code: `ae6bf9f9a5ed38057e35479125741e3d9175bab3`, with archiso submodule `424e78130db2af6c1ceb55b442d7914b1109ff2b`. Later ISO commits add acceptance tests only; the fresh Hub test is at `c3dd85c`.
- Hub baseline source: `9e0376567144bdbcf72f45203fbfeb457d381974`, version `0.1.3`, helper interface `1`.
- Baseline Hub archive: `maslow-hub-0.1.3-1-any.pkg.tar.zst`, SHA-256 `3baa23be234a5a9754d755f61d4da1ba9eda81a9ef16a2ebd99dc6e469d7f20b`.
- Preserved preliminary internal ISO: `maslow-os-2026.09.08-x86_64-hub-0.1.3-local-internal.iso`, 6,485,413,888 bytes, SHA-256 `5bb3e347947058138af74810049953b5f2a1f642c8c45ba0e48a9f3692f3d943`. Direct extraction from its SquashFS confirms the recorded runtime/Hub commits and the exact 0.1.3 archive hash. The image/package inspection found no disposable release trust or private signing material.
- The private `letsgomaslow/maslow-hub` repository was created. Source and artifacts have not been pushed or published.

The final corrected runtime is `dca4d9c824f958719c54c1ac09db0ffd82e89b68`; its exact candidate and package provenance are recorded below. All guest checks used headless QEMU/TCG; no UTM was used.

The final ISO baseline is 0.1.3. The separate local acceptance branch `codex/fresh-update-fixture` at `30e1db3` produces version 0.1.4 solely for demonstrating a newer signed release on a fresh-installed baseline. Its archive SHA-256 is `06715e975cb85ab72be0aecc703118b9904ea19c6aceae92db9e83cbfb6f6289`.

## Implemented behavior

Hub provides native Setup, Connections, Featured, and Updates sections. Setup reuses the runtime's existing state/tool helpers and preserves completed/deferred setup. The optional observability step is skippable and installs no service or model. Featured uses a bounded data-only catalog and explicit web-app add/open/remove actions. Connections distinguishes a local bridge/portal handoff from account authorization.

The package owns the Hub UI, helper, catalog, user timer, and narrow root installer. Updates verify signed bounded HTTPS metadata, expiry, sequence, compatibility, archive hash/signature, identity, dependencies, ownership, free space, and locks. Root verification repeats before normal pacman installation; rollback uses the retained root-owned trusted archive. Terminal callers with both standard streams on a TTY use sudo; graphical callers use Polkit. Neither route accepts an arbitrary root command.

Fresh defaults omit OBS Studio, Kdenlive, Moonlight, and eleven seeded web-app launchers. Docker, Compose, Buildx, Git, Lazydocker, Codex, Claude Code, Hermes, and Hub remain explicit packages. Existing-user shortcuts/data are preserved. ONCE and Ollama remain optional installs.

## Verified so far

- 31 Python helper/security tests and the QML/helper contract checks pass. Runtime brand checks, focused Hub routing/slim-default checks, ISO local-package checks, and package overlap checks pass.
- The complete runtime/settings/Hub package set was inspected for conflicting ownership. The 0.1.3 replacement was checked again against all nine selected local packages before ISO assembly resumed.
- In a disposable overlay of the preserved R2 installed base, graphical signed updates 0.1.0 → 0.1.1 and 0.1.0 → 0.1.2 succeeded. The latter loaded the new version-specific QML while retaining shell PID 780. A subsequent graphical authorization installed 0.1.3.
- Normal `maslow-hub-recover rollback` from installed 0.1.3 succeeded with the graphical shell stopped, using sudo and the narrow installer to restore trusted 0.1.2. This is terminal recovery evidence, not graphical rollback evidence. A separate direct privileged-helper rehearsal restored 0.1.1 → 0.1.0.
- Completed onboarding, a settings marker, a Chrome profile marker, and an existing user launcher retained their hashes. A Hub-created launcher survived updates/rollback, then was explicitly removed; the original preservation manifest consequently reports that one expected missing file. All original user markers still match.
- Signed tampering, expiry, replay, wrong-channel metadata, and an offline release server were rejected. The user timer was active after reboot and exposed its next scheduled check. Signed catalog loading was verified.
- Native headless screenshots verify Setup layout, saved selection, optional-step preservation, Connections, Featured, Updates, and keyboard scrolling/focus. Light-theme renderer captures cover all four sections. One transient status parse warning was observed; repeated instrumented helper calls returned valid JSON. Version 0.1.3 clears such a warning after a successful refresh, verified with a deliberately malformed then valid renderer fixture.
- Web-app opening reached Chrome's first-run terms screen. Those terms were not accepted, so loaded web-page content is not claimed as verified.

## Preliminary fresh-install acceptance

The recorded internal ISO completed a clean unattended headless installation. All 31 first-login assertions/evidence checks passed, including essential package presence, the three removed native packages, all eleven removed seeded web apps, automatic Hub launch, read-only incomplete onboarding, active daily timer, and no disposable trust. Native package reads confirm Hub `0.1.3-1` and runtime/settings `4.0.0.r2075.g960bb96-1`.

A second disposable overlay of that installed guest received only a test public release key, test TLS certificate, and isolated HTTPS channel. Hub's graphical Check discovered test-only `0.1.4`; Apply used native Polkit authorization and normal pacman. Graphical Roll back then restored trusted `0.1.3` through native Polkit. Quickshell remained PID 782, the version-specific manifests changed between `0.1.3/Panel.qml` and `0.1.4/Panel.qml`, and all six preservation hashes matched after both transactions. Those hashes cover synthetic setup choices/optional-step skip, a real Hyprland settings file, a synthetic browser-profile marker, an existing fixture launcher, and a Hub-created fixture launcher. No account authentication is implied by the synthetic setup choice.

Evidence: `fresh-install-test.log`, `fresh-installed-baseline.log`, and `fresh-update/{after-apply.log,after-rollback.log,apply-journal.log,rollback-journal.log,hub-next-discovered.png,hub-014-reloaded.png,hub-013-rollback-reloaded.png}`. The previous terminal recovery `0.1.3` to `0.1.2` remains a separate migration result.

The fresh test server was stopped and its private release/TLS keys deleted. Public metadata and archive signatures still verify with the saved public key. The guest's original channel configuration was restored and disposable public trust removed, returning updates to disabled; all six preservation hashes still match. See `fresh-update/{cleanup.log,public-signature-verification.log,after-test-trust-cleanup.log}`.

Native About and login branding render correctly. Completed randomized screensaver frames expose horizontal clipping of the approved 100-column artwork at 1280x800 with the original 18-point font (`fresh-update/screensaver-sequence/014.png`). The originating task authorized a minimal responsive sizing correction, preserving artwork and 18 points on sufficiently wide screens, followed by narrow/wide installed-guest checks and a corrected ISO. The current ISO/hash is retained as preliminary engineering evidence. An upstream installer tip also mentions optional Kdenlive despite its removal from preinstalled packages; this is recorded wording debt, not an installed-package test failure.

## Responsive screensaver correction

Runtime commit `dca4d9c824f958719c54c1ac09db0ffd82e89b68` adds monitor-aware font sizing without changing approved artwork. The default remains 18 points where it fits. The focused sizing test passes, including UTF-8 artwork measured from a C-locale launcher.

The exact candidate launcher was run from a temporary file in the disposable preliminary installed guest. At 1280x800 it selects 15 points and the actual terminal has 106 columns for the 100-column banner; `fresh-update/sizing-narrow/025.png` shows the full banner. At 1920x1080 it retains 18 points and the actual terminal has 137 columns; `fresh-update/sizing-wide-ready/015.png` shows the full banner. These are native guest captures, not browser previews. The earlier `sizing-wide/` sequence was interrupted by automatic incomplete-onboarding UI and is not acceptance evidence. See `fresh-update/screensaver-sizing-proof.json` and the corresponding process logs.

The corrected ISO rebuilt only `omarchy-dev` as `4.0.0.r2077.gdca4d9c-1`. Settings remain the verified `4.0.0.r2075.g960bb96-1` artifact because no settings assets changed. The other eight local archives and completed dependency mirror are frozen. The isolated rebuild checks that the only changed package payload is `usr/bin/omarchy-launch-screensaver`, retains normal package integrity and overlap checks, and uses no network.

The corrected candidate is `maslow-os-2026.09.08-x86_64-hub-0.1.3-sizing-local-internal.iso`, 6,485,413,888 bytes, SHA-256 `c3ee08889eaa50bf2843ae6d0bdc45f8549569f956159421b1e67b98a31b363a`. Its new runtime archive SHA-256 is `33a2cb614603c5fceae53a38a2705aa3da769a0210af75bba753e7befce8e6e0`. Direct SquashFS extraction confirms the exact launcher bytes, runtime source/version/hash, unchanged settings and Hub archive hashes, all 1,192 package archives, removed native-package absence, and no disposable update trust. The first attempted rebuild stopped before package changes because the source snapshot referenced host-only Git objects; the snapshot was made self-contained and the offline retry completed normally. See `sizing-iso.json`, `sizing-iso-inspection/`, `sizing-runtime-payload.diff`, and `slim-iso-sizing-build.log`. Fresh installation of this exact corrected image passed all 31 first-login assertions/evidence checks. Installed package reads confirm Hub `0.1.3-1`, runtime `4.0.0.r2077.gdca4d9c-1`, and the intentionally retained settings `4.0.0.r2075.g960bb96-1`.

The final installed package-owned launcher has SHA-256 `13fc4c6c48b6f028592fbff3b5e44aa7c524b2f1a85e38d2097e0ef1a2763175`, matching the reviewed source and the archive extracted from the ISO. At 1280x800, Foot selects 15 points and its actual terminal is 29 rows by 106 columns. Native frame `sizing-native/installed-screensaver-final/018.png` shows the full 100-column banner with clear margins. The user artwork retains SHA-256 `b86d5ee296def5670afb66dfaef52fb082713f0b2c880b842a22449387a0a20d`. The settled Hub tool list is visible in `sizing-native/hub-loaded/001.png`; the automatic first-login screenshot was captured before its asynchronous tool list had loaded. See `fresh-sizing-install-test.log`, `sizing-native-boot.log`, and `sizing-native/{installed-baseline.log,screensaver-process.log}`.

The exact unchanged Hub archive's native graphical update/rollback and preservation proof remains scoped to the preliminary ISO. Those unchanged suites were not rerun on the corrected ISO. No new signing key, TLS key, or test release server was created for final fresh-install/sizing validation. Both the preliminary Hub ISO and original R2 ISO hashes were rechecked unchanged in `preserved-iso-hashes.log`. The final disposable guest was shut down cleanly after capture; no QEMU guest remains running in the task QA container.

## ISO build recovery

All local packages completed with the approved branding. Before image assembly, the initially built Hub 0.1.2 archive was replaced with the reviewed 0.1.3 archive, its checksum and full-set ownership checks passed, and the exact Hub commit/hash were appended to the ISO build-info file.

The subsequent mirror-download phase failed on timeouts fetching five large upstream archives. Local package outputs and the prepared live profile were preserved. Host-native curl resumed the exact archive URLs into the isolated build cache; the resumed builder retains its normal pacman checksum/signature verification, dependency resolution, mirror pruning, and mkarchiso checks. The isolated cache had initially been copied with an extra `airootfs/var/cache/omarchy` directory level. The coordinator corrected that harness layout, reused 689 matching complete archives, and downloaded the remaining 29 resolved archives. The nested old-cache copy was moved outside the active build mount so it cannot inflate or contaminate the ISO. No signature check or test was weakened. The accepted original R2 ISO, original repositories, and shared original build cache remain untouched.

Evidence is in the sibling `hub-evidence` directory: `migration/`, `packages/`, `source-recovery/`, `source-next/`, `slim-iso-build-brand.log`, `resume-iso-with-recovery.sh`, `resume-download-assembly.sh`, and `slim-iso-assemble.log`, `slim-iso-assemble2.log`, `final-iso.json`, and `final-iso-inspection/`. The headless renderer output is under the task's `hub-ui-qa2` visualization directory.

## Remaining acceptance and release gates

- Production release-key provisioning and an approved anonymously reachable immutable artifact endpoint remain open. Private GitHub release assets are not anonymously downloadable; no PAT or credential may be embedded.
- Source/artifact publication, Chrome redistribution, and final native Lenovo/device acceptance remain separate gates. No real provider account authorization was established by Hub testing.

Migration-only private signing/TLS keys were deleted after that rehearsal. Fresh-install acceptance used a separate disposable key pair, confined to the test container and excluded from source, packages, and ISO inputs. Its private keys were also deleted after the completed rehearsal.
