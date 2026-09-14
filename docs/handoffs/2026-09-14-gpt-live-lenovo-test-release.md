# GPT-Live Lenovo test update

Date: 2026-09-14. The user authorized shipping GPT-Live for Lenovo testing through the existing Hub update route. LiveKit remains pending. This is a test update, not general feature or hardware acceptance.

## Delivery decision and exact inputs

Reuse the exact Voice 0.1.4-9 archive tested in the [GPT-Live native integration checkpoint](2026-09-13-gpt-live-native-integration.md), delivered inside Hub 0.3.2. Later LiveKit experiments are excluded by choosing that older archive; the existing LiveKit provider is not removed. The GPT-Live provider, daemon, task coordinator, controller, UI, launcher and dependency locks have not changed since its tested runtime revision. The later shared audio additions expose two counters used only by LiveKit. There is no reason to rebuild Voice or the accepted ISO for this scoped delivery.

| Input | Identity |
| --- | --- |
| Hub branch | `codex/gpt-live-test-release`, separate Hub repository |
| Hub archive build source | `82efec304142813b6f4898f04c117aeb8520b45c` |
| Hub validation source | `5c412c77d4bcdebf0a1e2f01bbd740efea182eea`; only the UI contract test changed after the build, with packaged paths byte-equivalent |
| Hub outer recipe | `652583d9d463c60acf999a2c5b5946739316544b` |
| Hub archive | `maslow-hub-0.3.2-1-any.pkg.tar.zst`, 474,605,777 bytes, SHA-256 `7cbd9494df66526834a73bc390179c596f18db2e8125694c5b5ba24c1d9ed1ab` |
| Voice runtime | `675019e524759f0ab66a2f8b0079e5aea2d4d9bb` |
| Voice recipe | `3fe0daf7143cc041804a1f8a34560db10b5401fd` |
| Nested Voice archive | `maslow-voice-0.1.4-9-x86_64.pkg.tar.zst`, 284,542,111 bytes, SHA-256 `4b465a4cff46e4da6a5bf549d9fefcabd0f70fa312dedd76a1219a29136228ab` |
| Unchanged Hermes archive | `hermes-agent-0.21.0-3-x86_64.pkg.tar.zst`, SHA-256 `2102449c67c188e4a1ebb9771173ebd0ad2688116f458664344f686afb217ab4` |
| Unchanged local-speech archive | `maslow-voice-local-0.1.0-2-x86_64.pkg.tar.zst`, SHA-256 `a17d7613b43c040b88cded635a7e3116a22d5813cc35376771c3d259b00d77c8` |

Hub changes are version metadata and the update instructions: after updating Hub, open Voice, choose **Update Voice**, then select **GPT-Live** in Voice Settings. The page identifies the 22 voice choices, recommends a disposable test project and checking filenames, and explicitly marks LiveKit testing pending. Hub does not automatically install the optional Voice component, migrate the OS core, or authenticate the separate task agent.

## Verification

- Hub's release check passed all 124 Python tests and all three UI contract groups. The first run exposed stale assertions for 0.3.1; the tests now check 0.3.2 and its new guidance. That test-only correction did not change the built archive.
- The package audit matched all three nested archive hashes/sizes and 13 packaged Hub helper/UI files to the build source. The actual Hub updater accepted archive identity, ownership, dependencies, helper interface 2 and version-specific `0.3.2/Panel.qml`. No arbitrary install script or file ownership was introduced.
- Real Quickshell under Docker/headless Weston rendered the 1280×800 Updates page. Worker and root inspected the PNG; the new copy fit without overlap or clipping. This is rendering evidence, not provider or installed-package proof.
- Installed OTA, preservation, native GPT-Live settings and the separate fresh Mac synthetic provider check passed at the scopes below. Operator signing is ready; production publication remains pending.
- Luna handled bounded UI/tester checks; Sol reviewed release/source provenance and signing guards; root integrated and verified the actual guest flow. Final independent evidence review found no accuracy blocker. Documentation checks passed 22 relative links, eight revision references and whitespace validation; Hub, package, ISO and distribution worktrees were clean at closeout.

Local evidence root: `/Users/r.david/.codex/visualizations/2026/09/13/01a09a02-5898-7873-8684-032cf60f9165/voice-ota-032/`. Key records are `build-inputs.json`, `build.log`, `package-audit.json`, `release-check-final.log`, and `ui/updates-032.png`. The PNG SHA-256 is `1103283d2dd746c5c4567ed646c96c7e2f3df7e10dd35483eca4ccbe4782ebca`.

## Installed OTA rehearsal

Passed. Used the ISO repository's existing headless QEMU/TCG harness at `d96a3ee563df5a1eb76a711c7b408c0d1d0137cb`, with CIDATA/SSH/QMP and a new disposable overlay of the prior installed OTA guest. The base is the accepted September 8 ISO, SHA-256 `c3ee08889eaa50bf2843ae6d0bdc45f8549569f956159421b1e67b98a31b363a`; no installer rerun or ISO rebuild is claimed. The guest uses four emulated CPUs, 2 GiB RAM and the recorded 256 MiB TCG cache wrapper.

Baseline was Hub 0.3.1-1, Voice 0.1.3-1 and Hermes 0.21.0-3. The isolated test channel used disposable signing/TLS fixtures and manifest sequence 103; that is not the public sequence or release key. QMP interaction exercised Hub's normal Check/Update now flow, GUI administrator authorization, then the separate Update Voice terminal and sudo prompt. Transactions completed as Hub 0.3.2-1 and Voice 0.1.4-9; Hermes stayed 0.21.0-3.

All preservation fields matched after Hub installation: Voice settings, task database, saved launcher, core launcher, private Voice launcher, held core package versions and Quickshell PID 997. After Voice installation only the intended private Voice launcher hash changed, and it matched the exact tested source. All 37 installed runtime/UI/launcher/lock files matched runtime `675019e5`; the plugin entrypoint was `0.1.4-9/Panel.qml`, with no refresh marker after opening Voice. Package presence alone was not the acceptance criterion.

The actual native panel opened, showed the shaded disabled orb, exposed GPT-Live cloud with its key field and voice picker, and persisted a keyboard change from Marin to Alloy (`mode=gpt_live`, `live_voice=alloy`). Those deliberate QA preference edits happened after the preservation comparison. The full catalog contained 22 voices; this is not an audition of all 22. No provider account was provisioned or physical/native audio session started in this OTA rehearsal. The installer advised opening Voice again; the normal packaged launcher succeeded without restarting the desktop.

The temporary guest Stay Awake control was restored to Allow Idle. The canonical harness stopped the disposable VM and its owned container/test server; the build container is also stopped. Unrelated containers, original overlays, public trust, held core packages and Mac tester credentials were left in place. Safe summary: `installed-rehearsal-result.json`; full hash comparison: `installed-voice-audit.json`. Inspected QMP frames include `guest/hub-032-visible.png`, `guest/voice-installed.png`, `guest/native-gpt-live-settings.png` and `guest/native-gpt-live-selected.png`.

Rehearsal tooling notes: idle lock initially obscured Hub, so the normal guest Stay Awake/Wake controls were used and later restored. A screen wait looked for the wrong label (`Apply Update` versus actual `Update now`), and one stdin-based audit received no script; both were corrected and the real UI/JSON evidence checked. Host/container archive inspection lacked zstd, so no dependency was added; the earlier package audit and actual installed source hashes supplied proof. These harness mistakes are not product failures or passes. The Mac Python 3.9 builder helper also required a streaming hash instead of `hashlib.file_digest`.

## Fresh GPT-Live check and tester learning

The fresh synthetic Mac connection check passed after a development-tester fix. It recognized input speech and an assistant reply, received 4,500 ms of reply audio, and returned to `disabled`, `busy=false`, microphone off, with no error. No physical microphone/speaker or new task handoff was exercised. The existing accepted-handoff count of one and two completed tasks were unchanged historical counters. Safe evidence is `gpt-live-api-smoke.json`, SHA-256 `225fc08c2122efe80578501e1d71cf44d6a8c23b35d202edd9018c9e0603dfdd`. This freshness check is separate from the prior exact-package installed conversation/task evidence; no new native credentialed audio session ran during OTA rehearsal.

The initial probe failed before an API request: a long-lived tester reloaded the provider while retaining an older voice catalog without `LIVE_VOICES`, raising `ImportError` at the provider import. Setup occurred outside error handling, while discarded background exceptions left `connecting`, `busy=false` and no public error. This was a tester cache/lifecycle defect, not evidence of provider unavailability or a packaged runtime defect.

Runtime commit `f6165d54a0659dc36647bba290729a2703d179a3` changes only `voice/dev/gpt_live_mac.py` and `voice/dev/gpt_live_session.py`. It reloads the shared catalog before importing/reloading the provider, reports safe exception type/location without raw exception text, and recovers completed failed jobs. The existing tester reloaded in place without clearing RAM credentials. Compile/whitespace checks, credential-free stale-catalog first-import coverage and an injected setup-failure/redaction check passed. The last import-order correction was checked without another paid probe. These development files do not change the frozen Voice archive.

The initial evidence file was overwritten by the worker's successful result. `gpt-live-api-smoke-initial-failure-reconstruction.json` explicitly reconstructs only known recorded fields and the original hash `1a534f2b8b5fde9f0f7ebbb2692f6e5b9d63517806eeadbc270ba351026dda24`; it is not the original bytes. Preserve separate attempt files in future, and reload shared dependencies before dependent modules in a long-lived tester.

## Public update preparation

The existing anonymous recovery tool verified public staging sequence 4, catalog sequence 1, distribution revision `bfd869fbb4da6776abe24fff58de01fe3afe20b7`, and exact historical package/signature bytes for 0.1.3, 0.2.0, 0.2.1 and 0.3.0. Hub 0.3.1 remains a frozen unpublished candidate; do not accidentally promote its old bundle.

Prepared public sequence 5 adds only Hub 0.3.2. The catalog and older recovery artifacts retain their exact bytes/signatures, and metadata expiry remains `2026-09-24T23:56:41Z`. Unsigned manifest SHA-256: `34eafd10b62d4ac1f184d97b25d4fc80e89ff19fc980bbd1a44e0cbb48587611`.

Preparation lives at `/Users/r.david/.codex/worktrees/43ab/hub-evidence/ota-voice-032/`. `sign-voice.sh` retains the verified operator workflow: require a real Mac Terminal, exact source/archive pins and release approval marker; use the protected operator key through OpenSSL; create a new signed bundle; verify signatures and run publication dry-run checks. It cannot publish. Its noninteractive refusal was checked without accessing the private key. The production trust fingerprint remains `daacaa5aac138710a3950097b29a05abd3f69c9a8efad512321c45f3103d1ee4`.

Current gate: operator signing is ready; the checked sequence-5 bundle is still unsigned and unpublished. The installed rehearsal and separate fresh Mac connection check are complete, and `.operator-signing-approved` enables the reviewed guard. Run `bash "/Users/r.david/.codex/worktrees/43ab/hub-evidence/ota-voice-032/sign-voice.sh"` directly in Mac Terminal. The existing signing passphrase is entered through OpenSSL twice and stays in that Terminal. Following a verified operator signature, the user's shipping request authorizes the existing immutable-artifact publication and staging promotion; do not request a second publication approval. Recheck public sequence before promoting to avoid overwriting concurrent work, then verify anonymous public bytes before telling the user to update Lenovo.

## Lenovo acceptance scope

The prior exact Voice archive passed native conversation during a separately typed Hermes correction and an additional 60-second soak. The user described Mac audio as smooth and responsive. Those are separate evidence levels. The native spoken filename was wrong, and the typed recovery retained capture drops under TCG; neither smooth physical audio nor reliable spoken technical names is established.

After publication, test Hub update, explicit Voice update, GPT-Live setup/voice selection, conversation start with microphone on, interruption, clean stop, and a task in a disposable project with its filename and contents checked. Keep conversation quality, spoken-detail accuracy and actual task results separate. GPT-Live conversation authentication is not Hermes readiness; direct named Codex/Claude routing and complete local-only inference remain open. LiveKit remains pending. No new claims about those paths, complete orb interaction, rollback of optional Voice packages, or Lenovo hardware acceptance follow from this test update.
