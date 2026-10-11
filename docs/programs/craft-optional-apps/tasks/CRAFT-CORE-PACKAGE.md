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

## Draft build and rejection checkpoint

Native `maslow-connect 0.1.0-1` built cleanly from source `21fdf8ae46de11cfc8b0a634d4489cf6abd0e937`, recipes `5a3f49a`; artifact `/home/maslow/Maslow-ai-os/craft-build/connect/recipe/maslow-connect-0.1.0-1-x86_64.pkg.tar.zst`, SHA-256 `35db43440f3e9bbfe4a289f1bdef73a7bd9f0cffa9be608d88ac1044d4f7f04a`. Builder `cfd891bf262d24bac53aa489af912484a08545e38001624a94640de4e43b840f`. Registered install, both launcher ownership, mtree checks for 10,202 paths, offline catalog/status and three-package overlap pass in a disposable container without development source mounted. Build/install logs remain in `craft-build/connect/`. This package is a rejected confinement draft, not accepted capability or release evidence; no host install occurred.

Build diagnoses: npx tried registry resolution even with a global tool in an offline test; recipe now fetches and checks the exact pnpm tarball (`3e2a9063…`) and invokes it directly. Legacy deploy generated one escaping workspace self-reference; the known self-link is relocated to deployed root while all other unsafe links remain errors. Private nested dependency `.bin` shims retained build NODE_PATH strings; all generated shims are removed, leaving fixed native entry points and normal module resolution. Deployment version/integrity fields are compared with the frozen source lock and local compiled contracts are byte-checked. First lock-record parser was too greedy across lines; a bounded header pattern was tested on existing actual deployment before the corrected full build. Final makepkg emits no source-directory-reference warning. These are diagnosed changes, not skipped checks.

Separate core isolation failures invalidate the standard Craft workflow at source21: host-UID nproc pre-limit prevents namespace start; direct RW output/state permits outside inode mutation via aliases; a project FIFO can carry host IPC even on a RO directory bind. Source worker attempt2 is repairing these with private project representation/output/state and bounded trusted publication. Next package must use a new reviewed source and pkgrel2; retain this exact rejected draft for provenance. Do not install/promote it as a confined offering.
