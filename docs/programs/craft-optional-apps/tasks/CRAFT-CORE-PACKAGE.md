# CRAFT-CORE-PACKAGE

Objective: Package native optional Connect independently of development paths

Repository: packages. Phase: 1.

Permitted files: pkgbuilds/maslow-connect/**. Coordinator owns ledger and shared integration.

Dependencies: CRAFT-P0-GATE.

Acceptance: Clean native package build, notices/deps/contents and packaged launch; no base payload change

Attempt history: not dispatched. No completion or test claims.

## Attempt 1, coordinator, 2026-10-11

Worktree `/home/maslow/Projects/Maslow/craft-packages`, branch `codex/craft-packages`, base `448856485e710caedfc24f544a027aea8652dd33`. Actual coordinator model not exposed. Own only `pkgbuilds/maslow-connect/**` and `test/craft-connect-package`; PDF/Photo worker owns separate app directories. No installed configuration changes.

Draft recipe/launchers committed as `494f045`, source-integrity regression script as `57337fb`. Native package contains local bridge CLI/MCP and self-contained deployed production Node dependencies, stable `/usr/bin` entry points, exact source/archive/lockfile/tool provenance, main proprietary license and bundled component notices. Portal/gateway deployment is not part of this package. Bubblewrap >=0.13.0 is optional at package installation but required for Craft isolation; no base-image dependency is inferred. Runtime dependencies include Node >=22, libsecret, xdg-utils and util-linux.

Source pin remains baseline Connect `0c6f7b98a062870e36503f55512d04e0b8576a69` until the Craft implementation passes review. Clean snapshots use `git archive` and refuse dirty or wrong-revision checkouts; no credentials or mutable remote source is fetched. Package build uses frozen dependencies and pinned pnpm 10.33.3. Deployed links must stay within the package tree.

Verification so far: `bash -n` passes for recipe/launchers; owning `./test/maslow-packaging` passes; `./test/craft-connect-package /home/maslow/Projects/Maslow/maslow-connect` passes real clean-snapshot/dirty/untracked/wrong-revision cases using a disposable clone; `git diff --check` passes. No native Connect package built yet. These checks do not pass installed ownership, clean build, packaged launch or candidate gates.

Next action: wait for the sequential app build slot to be released, advance source pin to reviewed Craft commit, build in the disposable x86_64 builder with clean self-contained source snapshot, inspect artifacts and package overlap, then record exact hashes and packaged runtime tests. Preserve active Connect implementation worktree.
