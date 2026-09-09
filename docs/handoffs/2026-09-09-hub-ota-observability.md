# Hub internet delivery and local Observability implementation

## Resume status

Implementation checkpoint, not release acceptance. Preserve the accepted Hub 0.1.3 ISO and package. No ISO rebuild or Lenovo modification was performed for this work. The user reports successful everyday use on a Lenovo with 16 GB RAM and nominal 500 GB storage; this is one test machine, not the product's hardware contract.

The approved payload is now local Langfuse for Hermes plus Observability guidance, web-app polish, Bitwarden guidance, Featured refresh, and bounded update history. This supersedes the earlier guide-only payload recommendation. Connect remains a separate local/serverless adaptation, not the OTA payload or an update transport.

## Delivery foundation

- Private Hub source checkout: sibling `maslow-hub`, branch `main`. Update history is `5062e2d`; delivery tools/CI are `d8e3230`; authenticated bootstrap utility staging is `330de78`; native UI is `8db1588`; guarded adapter development candidate is `b28d5150979dc2df16dc0d5fce161e883cc878d3`. Package assets recipe is `e4fab06`. These are not the accepted ISO's source revisions.
- Public distribution: [letsgomaslow/maslow-releases](https://github.com/letsgomaslow/maslow-releases), separate from private source. Scaffold commits `447747c` and `7e38da2`; GitHub Pages serves [the public root](https://letsgomaslow.github.io/maslow-releases/). Anonymous HTTPS returned the scaffold. GitHub's immutable-release protection was enabled and read back as enabled.
- No production key, signed package, signed channel, or signed catalog has been published. A reachable static site is not a functioning update channel. Protected operator signing and encrypted recovery backup remain required before promotion.
- Hub's `docs/github-delivery.md` owns commands and bootstrap procedure. Preparation verifies signatures, fingerprint, hashes, repository URLs, and channel metadata and refuses overwrite. Publication is explicit and distinct from Pages promotion. Do not promote the old 0.1.4 fixture.
- The exact rollback baseline is `maslow-hub-0.1.3-1-any.pkg.tar.zst`, SHA-256 `3baa23be234a5a9754d755f61d4da1ba9eda81a9ef16a2ebd99dc6e469d7f20b`. Preserve and sign that archive; do not rebuild an approximation of it.
- Private Git history stays private, but Python/QML shipped in installable packages is visible to recipients. No obfuscation or binary secrecy is promised.

## Evidence collected in this session

- Final focused suite: 69 Python tests plus the UI contract check passed. Coverage includes security/bootstrap negatives, bounded history, fail-closed rollback callback, adapter conflicts/credentials/locks, rejected resource checks, failed startup cleanup, local HTTP redirect refusal, and simulated low-disk stopping. This is not complete real-backend acceptance.
- Existing package-repository focused checks passed after adding conditional packaging of the adapter's fixed assets.
- Native Quickshell rendered in the existing Docker/headless Weston/software-rendering environment. Setup/Bitwarden, Featured/web apps, Updates empty history, and Observability were inspected. Review caught and corrected a dark-theme checkbox with unreadable text and an invalid accessibility attachment on a dialog. Light-theme content was also inspected. Setup and Observability were inspected at 720px width after hiding/reopening the test window; changing its requested width while visible did not resize the Weston surface. Keyboard acceptance remains separate.
- Screenshots are outside Git, under the existing visualization output `hub-ui-qa2/ota-020`. Do not commit user-machine paths or images as release artifacts. The development harness uses synthetic state, not real provider authentication.
- The development Docker VM has approximately 8 GB RAM, not the Lenovo's 16 GB. Six digest-pinned amd64 backend images were downloaded; no successful stack or real Hermes trace is implied by an image pull. Reported per-image Docker sizes sum to 1,227,670,040 bytes; this is not measured expanded storage or an established download requirement.
- The new explicit `tests/compose-smoke.py --run` created an isolated random-named stack with synthetic credentials and a 5.25 GiB sum of service memory caps. Startup failed after 3.2 seconds: ClickHouse exited 139 while its entrypoint ran `extract-from-config`; ClickHouse and Redis logs reported QEMU target-signal-11 segmentation faults under Docker's amd64-on-ARM emulation. MinIO and Postgres started. Cleanup returned zero and the original seven containers remained. This is failed emulated startup evidence, not a supported backend configuration or evidence that the Lenovo fails. Do not repeat the same emulation attempt without a concrete change; use installed x86 proof next.
- Built development package `maslow-hub-0.2.0-1-any.pkg.tar.zst`, SHA-256 `9fe0e08b3afcee3ac9f98f3dbf7040c69f7fbdb8c3d8c532dd6cd92d9237fec6`, from clean Hub `b28d515` and recipe `e4fab06`. Archive ownership validation passed; no unrelated system dependency was added. It is unsigned and not approved for public promotion.
- A new 4 GiB QEMU/TCG overlay of `sizing-native` booted the accepted baseline, then installed that package through the disposable guest's package manager. This is direct package smoke testing, not internet OTA proof. Preflight reported x86_64, 4,089,491,456 bytes total RAM, about 2.4 GiB available, and inaccessible Docker; `ready:false`. An interactive install returned `PREFLIGHT_FAILED` and a subsequent assertion confirmed no `stack.env` was created. Installed Hermes is 0.21.0 with bundled Langfuse plugin 1.0.0, not enabled, declared capabilities none. No Hermes reinstallation or Docker permission grant occurred.
- Quickshell remained PID 784 after the package smoke and scheduled extension reload, but QMP captures were inactive/black, including after a harmless wake key. Therefore this run does not establish installed graphical acceptance. The normal `sudo -n` attempt correctly required authorization; only the disposable CIDATA guest's documented synthetic password was used. The guest was powered off afterward; its overlay is retained at `hub-evidence/ota-020/installed` for continuation.

## Open acceptance gates

1. Finish remaining observability presentation: trustworthy download estimates, measured runtime/storage usage and safe bounded backend logs. Review the candidate on native x86 before promotion. The adapter now includes generated owner credentials, verified stop, local-only Docker, ownership conflicts, shared updater/lifecycle locks, and a periodic low-disk stop timer; installed startup/guard/rollback acceptance remains open.
2. Run the real isolated backend and real Hermes trace path. Test failure/restart/disable/data preservation, and measure constrained and higher-capacity installed guests. Publish only measured support, not guessed minimum hardware.
3. Complete and accept release B using a newly recorded build if source changes, then implement C (0.2.1) as a separate guided-troubleshooting/recovery payload. B's unsigned development package exists; neither B nor C is accepted or published, and C is not implemented yet.
4. Operator provisions protected release signing with encrypted recovery backup. Enroll existing 0.1.3 once using the independently authenticated public fingerprint. Never transmit the private key or passphrase in chat.
5. Explicit staging promotion, anonymous asset verification, then installed proof of `0.1.3 → B → rollback → B → C` with state and trace-volume preservation. Use existing QEMU/TCG overlays, not UTM or a new ISO.
6. Lenovo verifies internet update delivery, real traces, login startup, responsiveness, preservation, and recovery. Its success establishes one demonstrated configuration.

## Efficiency and lessons

- At most two disjoint workers: Terra for native UI, Sol for the adapter; coordinator handles release security, integration, evidence, and documentation. Broad upstream investigation delayed adapter code; narrowing to a tested slice was necessary. Do not repeat that investigation when resuming.
- Reuse running native-rendering and Arch package-build containers and downloaded pinned images. Preserve the unrelated Connect database container. Do not reconfigure global Docker resources without authorization.
- Weston here lacks the virtual-keyboard protocol used by `wtype`; do not repeat that failed route. Fixture navigation aids screenshots but does not prove real keyboard accessibility.
- Low-risk UI/test completion must not mask incomplete backend, public trust, package, or hardware acceptance. A failed service stop must block rollback rather than reporting success.

Next executable step: obtain an authorized native x86 test configuration with usable local Docker and adequate measured resources, run the isolated Compose proof, then finish B's remaining presentation/acceptance gaps. Operator signing preparation can proceed independently; do not promote the present unverified payload or rebuild the ISO.
