# CRAFT-CORE-BOUNDARY-REPAIR

Objective: independently review actual namespace-start and writable hardlink failures at Connect `21fdf8a`, propose smallest coherent repair and precise tests.

Dependencies: CRAFT-P0-GATE. Ownership: this report only; no implementation edits, ledger edits or installed changes.

Evidence: [coordinator reproduction](../evidence/2026-10-11-boundary-failures.json). Source `/home/maslow/Projects/Maslow/craft-connect`, root output `/home/maslow/Maslow-ai-os/craft-build/hardlink-probe/`.

Acceptance: distinguish native-app boundary from unrestricted requesting agent/host; assess preflight alias rejection plus syscall denial versus staged trusted export, including races and private state; prescribe regression tests. Source/profile acceptance is held; existing package builds do not waive failed isolation.

Worker: gpt-6-astra high, attempt 1 if available. Next action: read source/report/evidence; return findings and repair recommendation without modifying source.
