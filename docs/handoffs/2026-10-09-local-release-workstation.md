# Lenovo local Hub release workstation and first local renewal

Date: 2026-10-09. The Lenovo is now a second release workstation. It renews, prepares, verifies and publishes Hub staging metadata without GitHub Actions, which is blocked by an account billing lock. The Mac's existing capability is unchanged. Mac compatibility of the new tool has **not** been tested.

## Publication path (no change to `main`)

- `main` keeps its protections: required `checks` status, one review, enforced for admins. Nothing was disabled or faked.
- Created `signed-staging` at `c0ea86a` (main's tip, the latest signed distribution commit). It is protected against force-pushes and deletion (admins included) and requires linear history.
- Switched Pages from `main` to `signed-staging`. All eight public files (both signed pairs, `bootstrap/release.pem`, `bootstrap-trust.py`, its `.sha256`, `index.html`) were byte-identical before and after.
- Branch Pages builds run under the billing lock: requested builds succeeded at 15:00 (main), 15:04 (signed-staging) and 15:29 UTC (the renewal). Only the infrastructure check job is refused for billing.

## Tooling

`maslow-releases` draft PR #3 (`codex/local-release-workstation`, stacked on unmerged PR #2) adds `tools/local-release.py` and `docs/local-release.md`. It is a front end over PR #2's `build-candidate`, `publish-candidate`, `renew/renew-channel`, `channel-data` and `verify-delivery`; there is no second signing system.

- **Configuration:** machine paths are in `~/.config/maslow-release/workstation.json` (600). The key is in `~/.config/maslow-release-signing` (700), with `release-key.pem` (encrypted) and `release.pem` at 600.
- **Passphrase:** OpenSSL prompts on the terminal; the tool strips `HUB_SIGNING_PASSPHRASE`.
- **Before signing:**
  - fetch and verify `signed-staging`;
  - require Pages to serve exactly those bytes;
  - make the new commit directly extend the fetched one;
  - recheck the remote tip, then do a normal fast-forward push.
- **Approval:** `publish` requires the exact `review.json` SHA-256. `--no-push` rehearses locally.

The PR also fixes PR #2's build harness. Hub's Voice-delivery checks reject any group- or world-writable ancestor, so they always failed under `/tmp`, even as root; root checks now use a private `TMPDIR`. With that, all 138 Hub tests pass as root in the container. This corrects the earlier "25 root-only failures" explanation: those tests need a root-owned, non-writable temp tree, not just root.

## Evidence

- **Local tests:** `python3 -m unittest discover -s tests -v` gives 60/60 on the Lenovo. That is PR #2's 42 (first full Linux run, including GPG and git cases) plus 18 new tests with disposable keys, a local bare repo and a simulated Pages site. They cover:
  - expired renewal;
  - signature rejection;
  - Pages lag;
  - concurrent publication, at the preflight and at git level;
  - sequence continuation;
  - permissions and encryption;
  - trust-root and wrong-key mismatch;
  - exact-digest approval;
  - rollback preservation;
  - no-push rehearsal;
  - no republishing an existing version;
  - the Hub's real archive-ownership policy.

  These tests are not publication evidence.
- **Keys:** the operator placed the existing encrypted key and public key in `~/Downloads`. They were moved, not copied, into the signing directory (they had been mode 644 there). The public key's SPKI SHA-256 is `daacaa5a…3d1ee4` and it is identical to `bootstrap/release.pem`. The operator ran `maslow-release fingerprint` in a real terminal: the private-key-derived fingerprint matches. Embedded `!` prompts cannot answer OpenSSL's passphrase prompt.
- **Authorized renewal:** run by the operator with `maslow-release renew`; evidence in `~/.local/share/maslow-release/runs/20261009T152904Z-renew/record.json`.
  - Tools commit `432f140`; base `c0ea86a`; new commit `fe01694` (parent `c0ea86a`; only the four `hub/staging` files changed; only `sequence`, `generatedAt` and `expiresAt` differ).
  - Manifest 5→6, catalog 1→2, expiring 2026-11-08T15:29:05Z. Releases 0.1.3, 0.2.0, 0.2.1, 0.3.0 and 0.3.2 are unchanged.
  - Pushed 15:29:22Z. The tool verified anonymous delivery at 15:30:07Z.
  - An independent anonymous re-download matched every signed hash (`manifest.json aa4abf54…`, `.sig 6287ed10…`, `catalog.json a207fb64…`, `.sig 65a87eaa…`) and both signatures verify against the pinned key.
- **Lenovo acceptance** (installed Hub 0.3.2, no re-enrollment, no ISO change):
  - Before: `Check failed (MANIFEST_EXPIRED)`.
  - `maslow-hubctl --json check --manual`: `ok`, "Hub is up to date.", accepted `highestSequence` 6.
  - `catalog-refresh --manual`: `ok`, 6 items, accepted catalog sequence 2.
  - The root replay anchor was not inspected (no passwordless sudo).

## Hub 0.3.3 candidate and installed acceptance (unpublished, awaiting approval)

### Retired first build
Built from Hub `8aeabe9f` (package `248109a7…`, review `98d6c6cc…`). Installed acceptance on the Lenovo found a defect: Voice's controller `enabled` flag means a live conversation, so Hub told a ready Voice user it was "turned off" while the orb said "Ready · click to talk". The fix is Hub `c401d3c` on PR #1. This build must not be published.

### Current candidate
Built with `maslow-release prepare` in `archlinux@sha256:996c3a1d…`, network off. Run: `~/.local/share/maslow-release/runs/20261009T163303Z-prepare`.
- Hub source `c401d3c95780535ffdc5dff680e31b55cf452c41` (PR #1 head, unmerged); recipe `448856485e710caedfc24f544a027aea8652dd33`.
- Package `maslow-hub-0.3.3-1-any.pkg.tar.zst`, 474,637,715 bytes, SHA-256 `b23f3e5757aa7581802521d0691dac23fe87f1e6b719a3653cab9c5f33159985`.
- Review SHA-256 `2c0237d91388b99978009821afeee36ae04cca3e9147021b86d091d7bc725cbe`.
- The Voice donor is signed 0.3.2 (`7cbd9494…`); the Voice manifest `84d17109…` is identical to the Lenovo's installed 0.3.2.
- **Build checks:** all 138 Hub tests pass as root in the container, along with the UI contract; the recipe builds unchanged; Hub's archive-ownership policy passes; identity is correct with no conflicts or replaces. A dry run keeps all five rollback releases; publishing would now produce sequence 7.

### Clean-container install
The first build was installed with `pacman -U` in a clean Arch container:
- 52 files, 0 altered; the only files outside Hub folders are the paths Hub's ownership policy explicitly allows.
- The UI entry point is `0.3.3/Panel.qml`.
- Installed `maslow-hubctl`: version 0.3.3, Connect `unavailable` with no portal URL, `connect` returns `CONNECT_UNAVAILABLE`.
- An unenrolled container reports updates as `untrusted`, as expected.

### Lenovo installed acceptance
The operator ran `sudo pacman -U` for each step; evidence is in `~/.local/share/maslow-release/acceptance-0.3.3/`.
- **First build:** upgraded 0.3.2→0.3.3 (52 files, 0 altered). The Quickshell PID 1578 was unchanged. All 8 Hub state files and the setup state were byte-identical. After a plugin reload the live panel showed Updates "Installed version 0.3.3 · Up to date", Connect "Coming soon", and readiness of Codex/Claude ready, Hermes needs-attention and Hindsight action-required (screenshots captured). This build had the Voice defect described above.
- **Corrected build:** reinstalled (0.3.3-1, 0 altered); the installed `Panel.qml` and `hubctl.py` match the candidate.
  - `voice status`: `idle`, "Voice is ready. Click the orb or press Super+H to start talking."
  - `check --manual`: `ok`, up to date.
  - Shell PID unchanged; setup and other state unchanged.
  - The corrected Voice page was not screenshotted because the operator's Voice task overlay covered the Hub window. A same-version reinstall can also leave Quickshell's cached QML in place; a real update loads a new version path.
- **Rollback:** pacman downgraded to the signed cached 0.3.2 (`7cbd9494…`, verified against its published detached signature).
  - Panel back to `0.3.2/Panel.qml`; `check --manual` returns `ok`, up to date at sequence 6; rollback still available; shell PID unchanged; state preserved.
  - `pacman -Qkk` reports 2 "altered" directories (`usr/share/maslow-hub/catalog` and `observability`). The signed 0.3.2 package records them as 775 (built on macOS); the 0.3.3 container build set the stricter 755, and pacman does not loosen existing directory modes. The filesystem is stricter than 0.3.2's record; nothing else differs.
- The installed runtime's `omarchy-launch-hub` predates the `voice` page (`Unknown Hub page`); runtime `main` already includes it.
- **Not tested:** the over-the-air update path (Hub Update button through the privileged installer) to 0.3.3. It needs publication; publish only after the operator approves review `2c0237d9…`, then apply from Hub on the Lenovo and verify.

## Remaining gates

1. PRs #2 and #3 and Hub PR #1 are unmerged. Merging `main` needs the Actions `checks` job, which billing blocks. Local signing runs from the reviewed local commit of PR #3.
2. `main` still carries the PR #1 `renew-staging.yml`. It targets `main`'s channel files and cannot push there under protection; PR #2 replaces it. It must not run against `signed-staging` once Actions returns.
3. **Next renewal:** before 2026-11-08 (run `maslow-release renew` around 2026-10-30). Nothing renews automatically while Actions is blocked.
4. **Mac setup is untested:** pull PR #3, Python 3.12+, `zstd`, Docker for `prepare`, `local-release.py init` with Mac paths, signing directory at 700.
5. **Hub 0.3.3:** after operator approval, run `maslow-release publish --candidate ~/.local/share/maslow-release/runs/20261009T163303Z-prepare/candidate --approve 2c0237d91388b99978009821afeee36ae04cca3e9147021b86d091d7bc725cbe` in a real terminal, then apply it from Hub's Updates page on the Lenovo.
