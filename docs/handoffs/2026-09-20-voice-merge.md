# Voice MVP source integration and lessons closeout

Date: 2026-09-20. The user authorized committing the complete Voice work, documenting the larger goal and lessons, and creating/merging pull requests. Runtime targets `letsgomaslow/maslow-os:main`; recipes target the package repository's verified product/default branch `letsgomaslow/maslow-os-pkgs:maslow`. This authorization does not publish packages or rebuild an ISO.

## Product and documentation

[Voice product direction, journey and lessons](../maslow-voice-product.md) separates the executive-assistant ambition, this one-job MVP, observed outcomes, unresolved acceptance and future scope. The original September 19 discussion is now committed as historical context. Historical handoffs retain their exact candidate identities and failures, with pointers to current status. The Voice development guide now links the product regression checklist.

The governing lesson is that automatic backend behavior is insufficient if the user still encounters a form. Verify first entry, delegation, live intervention and result delivery in the actual UI. Keep ordinary bookkeeping automatic while retaining meaningful clarification and exact permission decisions. Never confuse typed conversation with physical speech, file existence with browser behavior, process creation with readiness, or source integration with public delivery.

## Pre-merge review correction

A bounded independent Astra review found a task-target race: a delayed Gemini control resolved the task selected at tool dispatch, rather than the task associated with the captured request. Selecting task B after requesting a correction or Continue for A could redirect that instruction to B. An isolated reproduction used no credentials, inference or UI.

Runtime `b42bc84c` captures the daemon-resolved task identity or targeting error at the existing final-transcript boundary shared by typed/spoken requests. Only a daemon submission receipt can associate a newly created task with that same turn. Later UI selection cannot redirect it. Provider generation is checked after acquiring the action lock, so an old queued callback cannot reuse a new session's turn identity. Binding is at final transcript capture, not physical speech onset.

Five added regressions cover typed/spoken selection changes across all six controls, repeated transcripts, missing and ambiguous task selection, same-turn submission retries, and old-provider callbacks queued across session replacement. Focused pinned checks passed 90 tests without skips. No additional concrete blocker was found in the bounded desktop/workspace, approval, recovery and continuation review; this is not exhaustive security or hardware acceptance.

Recipe `aa7f340` advances Voice from pkgrel 12 to 13 for this additional runtime correction; no dependency or package ownership changes. Installed Lenovo Voice remains `0.1.5-12` from `c7de65fb`; source integration alone does not install the new task-binding fix. Preserve the installed candidate's exact prior evidence and rollback artifacts.

## Verification and delivery boundaries

The existing main-branch GitHub Actions run `35473577580` failed before any test steps. Its source check annotation states: “The job was not started because your account is locked due to a billing issue.” That is hosted CI unavailable, not a passing or failing source-test result. No workflow, protection, billing configuration or check result was altered to conceal it. Local verification and PR checks are recorded separately below.

All package build outputs, private logs, screenshots and credentials remain outside Git. Unrelated package `staging-output-*` directories are preserved, not committed. The local runtime tree includes the previously uncommitted product-discussion document with the user's new authorization. No installed runtime or provider configuration is changed by this integration work.

Physical microphone/speaker acceptance, spoken correction, voice-driven launch/refocus, actual browser artifact behavior and real missing-auth recovery remain open. Existing permission prompts remain enabled. Next product action after source integration: test the complete physical journey, using a separately installed candidate that includes the task-binding correction.
