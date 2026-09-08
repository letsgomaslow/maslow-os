# Maslow Hub implementation and acceptance checkpoint

Status: implementation and migration rehearsal verified; final ISO assembly and fresh-installed update rehearsal are in progress. This is not a publication or native Lenovo acceptance record.

## Recorded inputs

- Runtime code: `960bb961353c0257788bc7705f2253bf0295ee10`. This includes the approved branding checkpoint `b69f785ffdd3e67959702f2a535056b0bcba8986`, cherry-picked without conflicts from its recorded parent `ae1041b4095637a2490674637e8b04cc8a4f565f`. Hub integration remains present.
- Package recipes: `c8506a142a37389f39006676e37ab89799f4e125`. Hub uses version-specific QML entry-point paths to prevent an existing QML engine from reusing older code after a plugin rescan.
- ISO builder code: `ae6bf9f9a5ed38057e35479125741e3d9175bab3`, with archiso submodule `424e78130db2af6c1ceb55b442d7914b1109ff2b`. Later ISO commits add acceptance tests only; the fresh Hub test is at `c3dd85c`.
- Hub baseline source: `9e0376567144bdbcf72f45203fbfeb457d381974`, version `0.1.3`, helper interface `1`.
- Baseline Hub archive: `maslow-hub-0.1.3-1-any.pkg.tar.zst`, SHA-256 `3baa23be234a5a9754d755f61d4da1ba9eda81a9ef16a2ebd99dc6e469d7f20b`.
- The private `letsgomaslow/maslow-hub` repository was created. Source and artifacts have not been pushed or published.

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

## ISO build recovery

All local packages completed with the approved branding. Before image assembly, the initially built Hub 0.1.2 archive was replaced with the reviewed 0.1.3 archive, its checksum and full-set ownership checks passed, and the exact Hub commit/hash were appended to the ISO build-info file.

The subsequent mirror-download phase failed on timeouts fetching five large upstream archives. Local package outputs and the prepared live profile were preserved. Host-native curl resumed the exact archive URLs into the isolated build cache; the resumed builder retains its normal pacman checksum/signature verification, dependency resolution, mirror pruning, and mkarchiso checks. No signature check or test was weakened. The accepted original R2 ISO, original repositories, and shared original build cache remain untouched.

Evidence is in the sibling `hub-evidence` directory: `migration/`, `packages/`, `source-recovery/`, `source-next/`, `slim-iso-build-brand.log`, `resume-iso-with-recovery.sh`, `resume-download-assembly.sh`, and `slim-iso-assemble.log`. The headless renderer output is under the task's `hub-ui-qa2` visualization directory.

## Remaining acceptance and release gates

- Finish the ISO, record its exact size/hash/embedded package inventory, and run the fresh Hub first-login/slim-default scenario.
- In a disposable guest installed from that exact ISO, provision only a test public key/channel and prove 0.1.3 → 0.1.4 discovery/apply plus graphical rollback. Migration-only evidence does not replace this gate.
- Verify the approved branding in the final installed guest. No UTM is involved.
- Production release-key provisioning and an approved anonymously reachable immutable artifact endpoint remain open. Private GitHub release assets are not anonymously downloadable; no PAT or credential may be embedded.
- Source/artifact publication, Chrome redistribution, and final native Lenovo/device acceptance remain separate gates. No real provider account authorization was established by Hub testing.

Migration-only private signing/TLS keys were deleted after that rehearsal. Fresh-install acceptance uses a separate disposable key pair, confined to the test container and excluded from source, packages, and ISO inputs; delete it after the fresh rehearsal.
