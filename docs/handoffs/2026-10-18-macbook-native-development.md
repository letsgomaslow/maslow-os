# Native MacBook development handoff — October 18, 2026

## Current state and evidence boundary

The user reports that installation succeeded on their 2012 15-inch Retina MacBook Pro and that several things are not working properly. They want to continue development on that laptop. This is a tester-reported installation success, not a directly observed native acceptance run. Exact symptoms, current versions, disk/encryption choices, post-install updates and hardware/provider behavior have not been supplied. Do not invent issue details or mark native checks passed from this general report.

The verified experimental USB task is complete. The user subsequently authorized publishing this handoff to GitHub main and requested shared Claude/Codex instructions for the installed 2012 MacBook Pro. The user explicitly clarified that there is no Mac mini setup. Main receives documentation and agent entry points only; experimental code is backed up on explicit candidate branches rather than promoted across failed startup gates. No new ISO, package rebuild, native connection, system update or binary release is part of this handoff. Existing primary-checkout work remains preserved. [The MacBook development guide](../macbook-development.md) gives source restoration, baseline commands, ownership and a next-agent prompt.

## Exact candidate to resume

| Component | Frozen/tested source or package |
| --- | --- |
| Runtime production payload | `1056a7552c6bff751f2c27f79835cc8953862ee6`; `omarchy-dev` 4.0.0.r3146.g1056a75-1 |
| Runtime source freeze for ISO | `fdce071ee92cb07d5c00a75e2e84dff5f10a6df2`; subsequent runtime commits document results |
| Packages | `63f80c73d45279a7a56d6e83623efc7f82f8cb4f` |
| ISO | `567cef19b70cc62365a823e696a412f29b7bf586` |
| Hub | `6eed636526c3dd39831ce0c3a32f5a98e5e4b6c2`; 2.0.3-2 |
| Voice / Hermes | 0.1.5-47 / 0.22.2-4 |
| Qt / Quickshell | Qt Base 6.12.0-3; Qt Declarative 6.12.0-1.2 with two reviewed official backports; Quickshell 0.3.2.r7.g2b4501a-1 |
| Separate Qt WebEngine | 6.11.2; the stack is not uniformly Qt 6.12 |
| Installed VM kernel / live kernel | `7.2.8-8-omarchy-bore` / `7.2.3-arch1-Watanare-T2-1-t2` |
| Broadcom package | `broadcom-wl-dkms` 6.30.223.271-49 |
| Pinned archiso | `424e78130db2af6c1ceb55b442d7914b1109ff2b` |

The actual MacBook inventory may differ; record it before updates. Candidate upstream evaluation was bounded to the reviewed snapshots, not a claim of global latest Omarchy/Qt. The source manifest on runtime main records exact candidate commits and their later documentation commit; do not substitute the main product code for the candidate.

ISO: `maslow-os-2026.10.18-x86_64.iso`, 7,720,302,592 bytes, SHA256 `48f63db841041c2eff0b755ff8cab61498ff0d9b793e615cca31db498871486e`. The SanDisk 3.2Gen1 61,504,880,640-byte drive was written, fully raw-readback verified and ejected. The PNY USB 2.0 8,021,606,400-byte drive kept its older Lenovo installer; it was not updated to this ISO. No current physical USB state is asserted after the user took the media to the other laptop.

## What passed, failed and remains unknown

| Scope | Evidence/result | Limit |
| --- | --- | --- |
| Source: installer | Branding, all 15 shell groups and 211 Python tests passed in installed Arch; 24 focused Broadcom controls passed | Earlier Docker/root/tmp-fixture failures remain recorded; no skips/assertion/deadline changes used for the passing run |
| Build/artifact | Fresh assembly exit 0, independent 2,707-check audit, all 1,305 archives and 6,786 exported source entries matched | Internal experimental media; no stable-channel/signing acceptance |
| Fresh VM install | All 15 phases, 928/928 packages, writable Btrfs root, independent disk-only boot, first normal app before update passed | ARM-hosted x86 TCG/software rendering; not physical performance or Mac EFI/GPU proof |
| Offline Broadcom | Normal offline helper/DKMS compilation passed against exact running Bore kernel; matching live T2 module also built/admitted | No physical radio, module load or association/reconnection was tested in the VM |
| Settled Hub/Voice | Six Hub pages and three passive Voice panels inspected by worker and coordinator; secure lock/Voice deferral/one PAM unlock passed | Passive views only; provider account, microphone/audio and task delivery not exercised |
| Claude/public health | Three default readiness calls passed at about 4.0–4.2 seconds; no failed units/pending migrations; four holds preserved; no new crash report | Authentication unknown; no provider session; absence of crash does not establish original crash causality |
| Fresh-media cold startup | FAILED: readiness only at attempt 28, then compositor unknown; 240-second active continuity phase correctly refused | Later settled views and fast ping do not waive failure |
| Earlier Qt/startup investigation | FAILED continuity: 7/64 probes at 2 vCPUs and 4/67 at larger allocation; final 13-group run 7 pass/6 fail/0 skip; both final background fixtures time out | Historical separate VM/evidence; not a new MacBook result; original QML crash cause unproven |
| VM closure | Normal poweroff, saved-QEMU absence before stop, runner exit 0, container removed, clean closed disk/vars and unchanged ISO hashes passed | Closed private VM artifacts stay on the build Mac |
| USB | Exact approved SanDisk write/readback/eject passed; temporary Python Full Disk Access restored off | Both earlier pre-write macOS access failures retained; USB byte proof is separate from native operation |
| Native installation | USER-REPORTED SUCCESS on the 2012 Retina MacBook | No independent native inventory, screenshots or itemized results yet; unspecified remaining issues |
| Native Wi-Fi/GPU/input/audio/power | UNKNOWN / NEEDS ITEMIZED TEST | No inferred acceptance of Wi-Fi reconnect, graphics switching, trackpad, brightness, battery, suspend or audio |
| Updates, migrations, rollback/recovery | Prior ISO has supported update, actual snapshot/full restore and reapply proof; fresh new-media VM has no pending migrations | These lifecycle tests were not rerun on the October 18 ISO or MacBook; encrypted/factory recovery remains open |
| Provider/security/release | NOT TESTED / NOT APPROVED for acceptance | Real sign-in, voice conversation, microphone/speakers, agent delivery, stable signed channel and release publication remain separate |

## Changes already made and next investigation

Earlier work integrated translation parity, sudo recipe corrections, Hermes/Voice package alignment, installer integration, Hub private shared-state creation, the Claude supervisor deadline correction, trusted background asynchronous compilation and two official Qt backports. Their exact tests and remaining limits are in the handoffs below. Do not repeat those fixes from memory or assume they explain an unspecified native symptom.

First next action: collect actual MacBook inventory and a short issue list using [the development guide](../macbook-development.md). Prioritize Wi-Fi connection and reconnection, then capture the startup/desktop symptom at unchanged budgets. Match an observed issue to its source owner; retain packaged behavior until a reversible source-test procedure is established. Fix one confirmed problem and verify it natively before broad upstream updates or another ISO build. Keep Voice provider/permission boundaries, normal lock/PAM and four runtime holds intact.

## Evidence references and portable scope

- [Experimental ISO and verified USB](2026-10-18-macbook-experimental-usb.md): exact build, driver, VM, USB receipts and actual failures.
- [Qt/QML and startup](2026-10-18-qt-startup-fixes.md): production correction, reviewed official backports, focused source/VM failures, normal restoration and resource comparison.
- [Claude and startup](2026-10-17-runtime-readiness.md): deadline fix and original crash evidence.
- [Prior ISO lifecycle](2026-10-17-new-iso-lifecycle.md): earlier exact-media supported update/restore/reapply.
- [Blocker integration](2026-10-17-iso-blocker-integration.md) and [upstream candidate](2026-10-17-quattro-candidate.md): coordinated source/package/installer changes and bounded upstream review.

Build-Mac evidence root: `/Users/r.david/Documents/Maslow-Propriotory-Repos/Maslow OS Build Artifacts/omarchy-quattro-20261017/macbook-experimental-usb-20261018`. Its `completion-audit-final.json`, `vm/smoke-result.json`, source-suite, driver and USB summaries establish the completed media task. Earlier Qt evidence is in sibling `qt-startup-fixes-20261018`; prior ISO lifecycle evidence is in sibling `new-iso-20261017`. These absolute paths are provenance pointers, not locations available on the MacBook.

GitHub main contains this handoff, the shared agent entry points and `docs/macbook-candidate-sources.json`. Exact candidate branches in all four private source repositories preserve reproducibility. The build-Mac evidence root gains a `development-handoff-20261018/` closeout with source/main push receipts and documentation validation. There is no portable source archive or claimed offline build cache: delivery was changed to GitHub at the user's request before any bundle was built. Full screenshots, VM disks, raw build/private logs, package payloads and the ISO stay on the build Mac. Missing local evidence on the new host is not a native test failure; retrieve only needed public/redacted evidence for a concrete issue. Main's documentation update does not mean candidate code is merged, release gates are passed or any binary is published.
