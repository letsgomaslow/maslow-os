# Repeatable internet updates without rebuilding the ISO

Updated 2026-09-09. Proposed next execution plan; no endpoint, signing key, package, or deployment was published by this documentation change. See [the development index](maslow-development.md) for accepted artifact inputs and evidence limits.

## Scope and prerequisites

The Lenovo has reached the desktop and the user reports successful everyday use. Real internet update delivery and native rollback are still unproven. The installed internal image has no production update trust configured. A useful feature alone does not unblock OTA: first establish the approved endpoint and trusted signing key.

Use signed Hub packages and channel metadata served over public HTTPS. GitHub Releases remains the original artifact option; Vercel-hosted channel metadata with immutable package objects in Vercel Blob is an alternative to evaluate against the existing downloader. Neither needs a continuously running Maslow application server. Private repository assets are not automatically anonymously downloadable. Approve hosting/access policy and key custody before publication; do not embed a broad GitHub token in clients.

Bootstrap the existing Lenovo once with the reviewed channel configuration and public trust key. It may be downloaded over HTTPS, but authenticate the expected key fingerprint through an independently trusted route before installation. Do not bootstrap trust solely from the same unverified download. No private signing key belongs on the laptop, ISO, repository, or build image. No LAN share, temporary local web server, or manual package transfer counts as internet OTA acceptance.

Hub currently updates only its own package, including onboarding UI and supported helper behavior. Signed catalog refreshes update data, not executable functionality. Connect and observability backend packages require separately reviewed installation/update support. Runtime/desktop and other OS packages remain under the existing package/update workflow and Maslow runtime protection; do not bypass the hold or claim a stable OS package channel. New boot/install behavior and fresh-install defaults still require updated installer media, even when an existing machine can receive a separately engineered migration.

## Candidate test payloads

These are options, not implementation claims or authorization to install services. Lift is relative and excludes the common signing/hosting prerequisite.

| Payload | Lift | What it proves |
| --- | --- | --- |
| Observability onboarding guide: explain traces, failures, latency and cost using clearly labeled synthetic examples; keep backend setup Coming soon and allow offline skip | S | Real packaged UI/onboarding change without a database, provider account, or background service |
| Improve web-app validation feedback or management empty state | S | Packaged behavior change; verify existing launchers survive update/rollback |
| Bitwarden setup and locking guidance | S | Useful onboarding change without accessing a vault or claiming agent isolation |
| Refresh curated Featured descriptions/status labels | XS | Signed data delivery only; not sufficient evidence of package replacement |
| Local Hub update-history view | S–M after event-storage inventory | Real update diagnostics, not agent/model tracing; redact sensitive details and bound retention |
| One real opt-in observability adapter | M | Actual trace ingestion and failure visibility; requires selected backend, consent, privacy review, configuration and removal tests |

Recommended first payload: the Observability guide. Keep “Coming soon” on installation/setup until a working adapter is accepted. A synthetic trace must never look like collected activity. A future working backend remains optional and outside the ISO baseline.

## Repeatable release loop

1. Record installed Hub/runtime/helper versions and nonsecret state on Lenovo. Establish an authenticated, cached baseline A and compatible state backup so rollback is possible. Do not promote the existing 0.1.4 fixture clone as a production release.
2. Build reviewed B with the small visible feature. Run focused helper/security and UI contract tests, then Docker + headless Weston + real Quickshell and inspect PNGs. Reuse the installed QEMU/TCG guest for package integration; no UTM and no new ISO for Hub-only changes.
3. Produce the package, checksum, detached signature, compatibility information, release notes, and signed staging manifest using approved key custody. Publish immutable artifacts before switching channel metadata. Validate HTTPS accessibility and exact bytes from outside the publishing environment.
4. On Lenovo, explicitly check for updates and apply B with normal privilege authorization. Capture actual installed version and rendered new screen, preserved setup progress/web apps, and successful reload. Check that unrelated OS files/packages were not changed.
5. Roll back to verified cached A with its compatible state; confirm the old UI and preserved user data. Exercise terminal recovery independently of Hub. Return to B through a supported apply path and record the result; rollback must not lower replay protection or republish old channel sequence numbers.
6. Publish reviewed C as a second small package change with a newer valid manifest sequence. Repeat internet check/apply and preservation checks on the same laptop. This proves an ongoing workflow, not just a one-off upgrade.
7. Promote to alpha only after explicit approval and recorded evidence. Keep staging and alpha separate. Retain previous verified packages and release records. Refresh signed metadata before its expiry even if no new package ships; the current validity limit is 31 days. Mutable channel caching must not hide a new release, while immutable package URLs must never be overwritten.

At least once in staging, exercise invalid signatures, expiry/replay, incompatible versions, interrupted downloads, offline launch/skip, concurrent updates, insufficient disk space, and rollback with Hub unavailable. Use disposable guests for destructive failure simulations; do not intentionally exhaust the user's daily-driver disk. Existing automated fixture results do not replace external delivery or Lenovo acceptance.

Record each iteration's source revisions, package hashes, channel sequence, versions, inspected screenshots, state preservation results, failures and recovery. Exclude keys, provider secrets, and raw personal data. The next executable work is A2/A3 in the development index: approve endpoint/key custody and prepare the secure one-time bootstrap plus release pipeline. Feature implementation can proceed independently, but cannot be labeled an OTA success until this loop runs over the internet.

## Connect is a separate workstream

The current Connect bridge is local but its gateway and policy database are not a completed local/serverless deployment. Follow `docs/serverless-local-roadmap.md` in `letsgomaslow/maslow-connect`: decide the local/cloud boundary, durable serverless storage, credential/policy enforcement, and one-provider acceptance. Do not hold the Hub update experiment on this adaptation or silently move shared project credentials onto the laptop.

Hosting references: [Vercel Blob](https://vercel.com/docs/vercel-blob), [Vercel function limits](https://vercel.com/docs/functions/limitations). Platform capability does not establish project deployment readiness or zero operating cost.
