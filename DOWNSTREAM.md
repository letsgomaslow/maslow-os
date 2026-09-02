# Maslow OS downstream maintenance

Maslow OS is a downstream distribution based on Omarchy. This file is the maintained inventory of intentional downstream changes.

## Branch model

- `upstream/quattro` is the source of upstream truth.
- `origin/quattro` is kept identical to `upstream/quattro` with fast-forward-only updates.
- `origin/maslow` is the public product branch and the repository default.
- Sync upstream by fast-forwarding `quattro`, then merge `quattro` into `maslow` through a pull request. Never rebase or force-push `maslow`.

## Compatibility boundary

The following Omarchy interfaces remain unchanged:

- `/usr/bin/omarchy*` commands and routing
- `$OMARCHY_PATH` and `/usr/share/omarchy`
- `~/.config/omarchy` and `~/.local/state/omarchy`
- package and service identifiers
- shell plugin and theme extension contracts

Only curated user-visible product identity is changed. Documentation should describe Maslow OS as “based on Omarchy.”

## Patch inventory

1. Maslow product metadata, README, attribution, and preview version.
2. First-party `maslow-dark` and `maslow-light` themes plus deterministic brand artwork.
3. Maslow bootloader, Plymouth, SDDM, session, first-run, menu, About, and generated editor-theme labels.
4. Persistent Reduced Motion toggle and instant theme-background application.
5. Brand, accessibility, compatibility, and generated-asset validation.
6. Downstream package metadata and x86_64 installer wiring in sibling repositories.
7. Factory-reset ESP resolution for UUID, label, partition UUID, and partition label sources.

## Release policy

The ARM64 UTM image is development-only and must not be redistributed without provenance and license verification. Public binaries require Maslow-controlled signing keys, checksums, package infrastructure, clean-install validation, update validation, and a tested rollback path.
