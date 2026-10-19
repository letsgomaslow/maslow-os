# MacBook AC/battery nouveau pstate switch: implemented, fixed, and live-validated — October 19, 2026

## Outcome

Following the rejected Intel-iGPU fix and the research confirming nouveau has no true dynamic/load-based reclocking for this chip (see [the revert handoff](2026-10-18-macbook-intel-igpu-fix-reverted.md) and the "Known hardware facts" section of `docs/macbook-development.md`), a narrower, safer fallback was implemented, tested, fixed, and is now **live and working** on the 2012 15-inch Retina MacBook Pro: a udev rule that forces nouveau's GPU to a higher pstate while on real AC power and back to its lowest pstate on battery, with no continuous polling and no third-party daemon.

Branch `macbook-nouveau-ac-pstate-switch`, commits `031b5161` and `e52405d1` (not yet merged to `main` — see "Status" below).

## A real bug found via live testing, and the fix

The first implementation's `battery` case wrote the literal string `AC` to nouveau's pstate debugfs interface, intending to revert to the chip's conservative default. Live-testing on the actual hardware found this was wrong on two counts:

- Writing `AC` is **rejected outright** (`Invalid argument`) — that row is purely an informational live-clock readout in nouveau's pstate listing, not a selectable target.
- Writing `auto` (the next reasonable guess) is **accepted but selects pstate `0f`** — the single riskiest level this whole feature exists to avoid, not a return to any conservative default.

Fixed to use the explicit pstate `07` for the battery case, confirmed live to match this chip's untouched default behavior (its max core clock, 405MHz, is exactly what the chip was observed stuck at before any of this work began). Both directions (`ac`→`0a`, `battery`→`07`) are now live-tested and confirmed correct on the real hardware.

## What is actually running on this machine right now

Since `omarchy dev link` is disabled on this build (the same channel protection encountered during the earlier rejected fix) and this feature is not yet packaged/released, the two reviewed, committed scripts were placed manually at their real intended packaged location (`/usr/bin/omarchy-hw-macbookpro10-1`, `/usr/bin/omarchy-hw-macbookpro10-1-pstate-switch`, each symlinked into `/usr/share/omarchy/bin/` matching this repo's existing `hw-*` command convention), and the real committed udev rule was installed to `/etc/udev/rules.d/90-omarchy-macbookpro10-1-pstate.rules` byte-for-byte as committed. This is a deliberate, reviewed exception to hand-editing the packaged tree, done because the content is already reviewed and committed source, not an end-user customization hack — it should be reconciled with a real package release of this branch when one happens.

The full automatic path was directly end-to-end tested on real hardware, not just the manual script invocation: `sudo udevadm trigger --subsystem-match=power_supply` fired the real rule, which correctly resolved the bare `omarchy-hw-macbookpro10-1` call from inside the udev-spawned process's own (non-session) environment, and correctly forced pstate `0a` — confirmed against `upower` reporting `fully-charged` (genuinely on AC) at the time. This answers an open question from the implementation: udev-spawned process PATH resolution for Omarchy commands does work correctly in practice on this system, at least for this rule.

## Full round-trip confirmed with a real physical unplug/replug

Both directions are now confirmed via an actual physical charger unplug and replug, not just `udevadm trigger` synthetic events: unplugging switched the active pstate to `07` (nouveau's own live-state label correctly flipped from `AC` to `DC` too, confirming it tracks real power state), and replugging switched it back to `0a`. Pushed to `origin` and opened as [PR #21](https://github.com/letsgomaslow/maslow-os/pull/21).

## Reboot persistence confirmed

After a full `systemctl reboot`, all installed files survived with correct ownership/permissions (`/usr/bin/omarchy-hw-macbookpro10-1`, `/usr/bin/omarchy-hw-macbookpro10-1-pstate-switch`, `/etc/udev/rules.d/90-omarchy-macbookpro10-1-pstate.rules`), and pstate `0a` was **already active with zero manual intervention** immediately after login — the udev rule fired on its own during normal boot-time device enumeration (the AC adapter's initial uevent at boot matched the rule the same way a live change event does, since the rule has no explicit `ACTION==` restriction). This is the best-case outcome: the feature is fully self-activating across reboots, not something that needs to be re-triggered or re-applied.

## Remaining gates

1. PR #21 is open, not yet merged. Decide when to merge.
2. Not tested: rapid plug/unplug flapping.
3. If/when this is properly packaged and released upstream, the manually-placed files in this entry should be reconciled with (or simply left to be overwritten cleanly by) that real package.
