# MacBook Intel-iGPU display fix: tested on real hardware and reverted — October 18, 2026

## Outcome

The nouveau-disable fix proposed in [the native inventory handoff](2026-10-18-macbook-native-inventory.md) was implemented on branch `macbook-intel-igpu-display-fix` (worktree `.claude/worktrees/agent-a66c9928385d15f25`, commit `b1742736`) and live-tested on the actual 2012 15-inch Retina MacBook Pro. **It does not work on this hardware and must not be merged as-is.** The machine has been fully reverted and confirmed back to its prior working state.

## What the test found

The fix (modprobe blacklist + `nouveau.modeset=0` kernel param, mirroring the existing T2 Mac fix pattern) was applied manually and the machine rebooted. Result: the internal panel went dim and stuck (brightness widget and keyboard backlight controls both unresponsive), and inspection showed why — this is a real hardware limitation, not a misconfiguration:

- With nouveau prevented from doing KMS, `card0` (the NVIDIA PCI device, `0000:01:00.0`) fell back to a bare `simple-framebuffer` device with no real driver and an `Unknown-1` connector — no GPU acceleration at all, a regression from the original problem, not a fix.
- Intel's `i915` (`card1`, `0000:00:02.0`) enumerated **zero eDP connectors** — only an unrelated, disconnected `VGA-1`. Intel has no electrical path to the internal panel on this model at all.
- Conclusion: unlike later dual-GPU MacBooks where `apple_gmux` can mux the internal display between GPUs, **this MacBookPro10,1 hardwires its internal Retina panel to the discrete GPU only**. Nouveau is the only driver that can light up this screen; there is no software-switchable path to Intel for the internal display.

## Revert and current confirmed-good state

Manually removed `/etc/modprobe.d/macbookpro10-1-nouveau.conf` and `/etc/limine-entry-tool.d/macbookpro10-1-nouveau.conf`, reran `limine-mkinitcpio`, confirmed `nouveau.modeset=0` was gone from the regenerated `/boot/limine.conf` before rebooting. Post-revert and reboot, directly confirmed: `card0` vendor `0x10de` (nouveau) with `eDP-1` connected and properly named again, brightness widget and keyboard backlight controls both working, screen back to normal. The machine is back to exactly the state recorded in the native inventory handoff — sluggish by default (nouveau's conservative pstate), with the known reversible live pstate override still available as a stopgap, nothing else regressed.

## Status of the branch

`bin/omarchy-hw-macbookpro10-1` (the hardware detector) is sound and reusable — the detection logic itself was never in question. The actual fix action in `install/hardware/apple/fix-gmux-nouveau-display.sh` and `migrations/1792349584.sh` is confirmed wrong for this model and **must not ship**. Do not merge this branch. It is left in place as a record of the attempt and the hardware evidence above, not as a pending change.

## Remaining gates and real next steps

1. The internal display has no viable alternative to nouveau on this hardware. Any future performance work must work within that constraint, not around it.
2. Nouveau's *dynamic* reclocking (scaling clock with actual load, rather than a statically forced high pstate) was not investigated — check whether nouveau's automatic power-management path can be enabled/tuned on this Kepler chip rather than only offering "stuck low" or "pinned high" as the two known states.
3. If no dynamic solution is found, a user-facing toggle exposing the known-safe static pstate override (with its fan-noise/heat/battery cost clearly disclosed) is a more honest path than a silent default change.
4. All other gates listed in the native inventory handoff (longer suspend cycle, Voice/provider/audio acceptance) remain open and unaffected by this entry.
