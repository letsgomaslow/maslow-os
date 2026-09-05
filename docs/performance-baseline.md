# Performance baseline

`omarchy debug performance` captures a small, read-only performance snapshot from an installed Maslow OS or Omarchy system. It is engineering evidence for comparisons, not a published minimum system requirement.

Run it only after the same workload and power state have been applied to both systems. The default waits five minutes for the desktop to settle, samples CPU for ten seconds, reads used memory from Linux `/proc`, and captures enabled user units, running user and system services, and process names and resource metrics across all users. This includes shared names such as `quickshell` and `orca`, not just names containing `maslow`.

```bash
omarchy debug performance --json >maslow-idle.json
```

Use the same command, settle time, sample time, virtual hardware, display state, and open applications for the upstream Omarchy comparison. Repeat each capture at least three times and compare the median rather than choosing a single favorable run. The command does not stop services, close applications, change power settings, install packages, or inspect command arguments and credentials.

The JSON remains schema version 1 with additive fields: `enabledUserUnits`, `runningUserServices`, and `runningSystemServices` each contain `available` and `names`; `processSnapshot` contains `available` and `processes`. Process records contain `pid`, numeric `uid`, executable `command` name, `rssKiB`, and `cpuPercent`. Existing `maslowNamedUserServices` and `maslowNamedProcesses` retain their original filtered meanings for compatibility. Use the broader fields for attribution; no matching Maslow name does not mean no downstream work. An unavailable collector is distinguished from an empty successful result.

Per-process CPU from `ps` is a lifetime average, not the measured CPU sample window. RSS can include shared pages and must not be summed to claim total physical memory use. Enabled units are not necessarily running, and running services may have been activated on demand. Process visibility may be restricted by the host. Names, PIDs, numeric user IDs, and host identity are operational metadata: review snapshots before sharing them. Full command lines, process environments, and service configuration are not collected.

Cold boot, login-to-desktop, and application-launch timings require an external observer and a controlled fresh session; launching applications would change the system being measured, so this command does not automate those timings. Record them separately with the exact start and end event stated alongside the result.

ISO size and installer phase timing belong to `letsgomaslow/maslow-os-iso`, which owns media assembly and the VM acceptance harness. Package archive attribution belongs to `letsgomaslow/maslow-os-pkgs`. Do not add either measurement to this runtime repository or infer either value from this snapshot.

## Recorded upstream comparison baseline

Evidence-retention correction: the upstream measurements below were observed and reviewed during the task, but their original temporary raw JSON, screenshots, baseline disk and package-input artifacts are now unavailable. The values survive in task/tool logs; they are historical observations, not a currently auditable comparison bundle. Candidate raw evidence survives. Restore or reproduce and retain the upstream baseline before final performance acceptance or the matched terminal follow-up. The cause of the missing artifacts is not established.

Three sequential static-desktop samples were accepted from the private `20260905-001-upstream-fresh` fixture. The upstream runtime source was `7eca64e2683d2a4d4620f36164f001693ae6a5b7` (`4.0.0.alpha`), the exact common ancestor used for this Maslow comparison, not upstream's newer branch tip or stable 3.8.5. Unchanged package recipes came from `b66905a4370e3802424c83cfb187aeafdf78f25c`, producing `omarchy-dev` and `omarchy-settings-dev` version `4.0.0.r2006.g7eca64e-1`. Installer source was `2673c613d9a71e23920e43fbb951238145e0f1e8`.

This was a fresh target disk, not a Maslow installation with its source replaced. Installation was recovered after a test SSH public-key staging path became hidden by the target mount. Recovery ran the normal remaining SSH, Tailscale, DNS, boot-validation and factory-snapshot phases; subsequent installed-disk-only boot was verified. It is a recovered test installation, not evidence of an uninterrupted installer pass. Third-party packages came from the candidate's cached closure, not a reconstruction of historical upstream repositories. Upstream's default AI installation wrappers were retained; these are not the candidate's preinstalled core AI packages.

The test used x86 QEMU TCG with CPU model `max`, four vCPUs, 4 GiB configured memory and a 1280×800 display on an Apple Silicon development host. Test-only autologin, stay-awake inhibition and dismissed notifications established a static desktop. No product branding or accessibility defaults were changed to obtain these samples. Each sample used an external 300-second settle, then the same collector with `--settle=0 --sample=30`; the zero in collector JSON therefore does not mean there was no settling. Samples ran sequentially, not in parallel.

The test-owned guard required fresh output directories, explicit failure returns, no application clients, the expected desktop layers, no test application/screensaver processes and continued inhibition. It checked before and after sampling and retained screenshots. Layer geometry alone cannot establish absence of notification content, so acceptance additionally required visual review of endpoints. Guard SHA256: `b8a1dd96694154c1d30ef9f3a2a74e84dd38a386c02c33e90eaf18f736655d5f`.

| Sample | Aggregate CPU | Used memory (KiB) |
| --- | ---: | ---: |
| 003 | 1.27% | 1,482,068 |
| 004 | 1.12% | 1,500,936 |
| 005 | 1.17% | 1,509,300 |
| Median | 1.17% | 1,500,936 |

All three reported total memory of 3,993,056 KiB. Original `performance.json`, `protocol.json`, screenshots and endpoint inventories were recorded under `upstream-baseline-runs/20260905-001-upstream-fresh/upstream-guarded-idle-{003,004,005}` in the now-unavailable temporary QA directory. These were not repository fixtures. Raw CPU endpoints included collection overhead around the collector and need not exactly match its internal sample interval.

## Matched Maslow candidate samples

The candidate was installed from frozen-source ISO SHA256 `4034e6df66e1e4405faac5ded56a5fea8f064548e6dc913b3fd70535773af9bc`. Its runtime HEAD was `9ce7adab7d6ba9e5255a5a2ef5ea1d900bd2ac27`, but the image also includes uncommitted implementation changes captured by the build snapshot. HEAD alone is not its complete source identity, and the current working tree must not be substituted for that frozen input.

The same guarded protocol and guard hash above were used for three sequential candidate samples. Each actual `protocol.json` records the external 300-second settle and 30-second sample; each collector JSON records `settleSeconds: 0` and `sampleSeconds: 30`. Endpoint screenshots for both three-sample series were visually approved as clear static desktops. Candidate evidence is retained under ISO `test-runs/maslow-os-2026.09.04-x86_64-integration/runs/20260905-011941-candidate-performance/candidate-guarded-idle-{001,002,003}`.

| Sample | Aggregate CPU | Used memory (KiB) |
| --- | ---: | ---: |
| 001 | 0.85% | 1,378,880 |
| 002 | 1.60% | 1,376,456 |
| 003 | 1.08% | 1,409,176 |
| Median | 1.08% | 1,378,880 |

Candidate total memory was 3,993,052 KiB in all three samples, versus upstream's 3,993,056 KiB. The historically observed median differences were −0.09 percentage points CPU and −122,056 KiB used memory relative to upstream. The reviewed samples showed **no observed idle-resource regression in this controlled TCG experiment**, not statistical equivalence or proof that Maslow is faster. Missing upstream raw artifacts prevent treating this as a completed, currently reproducible acceptance gate.

Across all three candidate snapshots, running user and system service sets matched the upstream reference after normalizing instance identifiers. The candidate additionally enabled `speech-dispatcher.socket`, but no speech-dispatcher, Orca, espeakup, Codex, Claude, Hermes or Bitwarden process appeared in these snapshots. No candidate-only user-process executable name appeared. This supports the intended installed-but-inactive behavior for the sampled idle state; an enabled socket can activate later. No process RSS totals or lifetime CPU fields were used to attribute the interval result.

Earlier candidate results near 98% CPU were not valid static-idle measurements: one displayed an animated screensaver and another retained the onboarding panel. Preserve those as workload diagnostics, not parity evidence. Active-window rendering, typing responsiveness, the full Bitwarden/onboarding journey, and update/branding preservation remain separate acceptance questions. These results establish neither native-laptop performance nor minimum hardware requirements, package-channel safety or release completion. Native x86 hardware remains a separate verification step.
