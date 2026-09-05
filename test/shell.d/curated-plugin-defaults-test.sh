#!/bin/bash

source "$(dirname "${BASH_SOURCE[0]}")/base-test.sh"

require_command git
require_command node
require_command jq

node <<'JS'
const fs = require('fs')
const path = require('path')
const root = process.env.ROOT
const config = JSON.parse(fs.readFileSync(path.join(root, 'config/omarchy/shell.json'), 'utf8'))
const enabled = config.plugins.map(plugin => plugin.id)

function fail(message) {
  console.error('not ok - ' + message)
  process.exit(1)
}

if (JSON.stringify(enabled) !== JSON.stringify(['omadock', 'tyrsolution.app-launcher'])) {
  fail('fresh shell defaults enable only the two curated plugin overlays')
}

for (const section of Object.values(config.bar.layout)) {
  if (section.some(entry => entry.id === 'tyrsolution.app-launcher')) {
    fail('fresh shell defaults omit the App Launcher bar widget')
  }
}

console.log('ok - fresh shell defaults enable both overlays without a duplicate App Launcher bar widget')
JS

bindings="$ROOT/default/hypr/bindings/applications.lua"
grep -Fqx 'o.bind("SUPER + A", "App Launcher", "omarchy-shell shell toggle tyrsolution.app-launcher '\''{}'\''")' "$bindings" ||
  fail 'Super+A toggles the App Launcher with the exact plugin command'
grep -Fqx '  o.bind("SUPER + SHIFT + A", "ChatGPT", { webapp = "https://chatgpt.com" })' "$bindings" ||
  fail 'Super+Shift+A remains assigned to ChatGPT'
pass 'App Launcher binding preserves the existing ChatGPT shortcut'

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

remote="$tmpdir/omadock.git"
upstream="$tmpdir/upstream"
home="$tmpdir/home"
bin="$tmpdir/bin"
mkdir -p "$bin" "$home/.config/omarchy/plugins"
git init --bare "$remote" >/dev/null
git clone --quiet "$remote" "$upstream"
git -C "$upstream" config user.name 'Upstream'
git -C "$upstream" config user.email 'upstream@example.invalid'
printf '%s\n' '{"schemaVersion":1,"id":"omadock","name":"omadock","version":"1","kinds":["overlay"],"entryPoints":{"overlay":"Dock.qml"}}' \
  >"$upstream/manifest.json"
printf '%s\n' 'MIT License' >"$upstream/LICENSE"
printf '%s\n' 'glyph: "\ue900"' 'tooltip: "Omarchy"' >"$upstream/Dock.qml"
git -C "$upstream" add .
git -C "$upstream" commit --quiet -m 'Upstream dock'
git -C "$upstream" push --quiet origin HEAD:main
git -C "$remote" symbolic-ref HEAD refs/heads/main

plugin="$home/.config/omarchy/plugins/omadock"
git clone --quiet "$remote" "$plugin"
git -C "$plugin" checkout --quiet -b maslow-managed
printf '%s\n' 'glyph: "\ue90b"' 'tooltip: "Maslow OS"' >"$plugin/Dock.qml"
printf '%s\n' '{' '  "id": "omadock",' '  "displayBranding": "maslow-dock-v1"' '}' \
  >"$plugin/.maslow-managed-branding.json"
git -C "$plugin" config user.name 'Maslow OS'
git -C "$plugin" config user.email 'support@maslow.ai'
git -C "$plugin" add Dock.qml .maslow-managed-branding.json
git -C "$plugin" commit --quiet -m 'Apply Maslow dock display branding'

printf '%s\n' 'upstream change' >"$upstream/README.md"
git -C "$upstream" add README.md
git -C "$upstream" commit --quiet -m 'Upstream change'
git -C "$upstream" push --quiet origin HEAD:main

cat >"$bin/omarchy-plugin-validate" <<'SH'
#!/bin/bash
[[ ${VALIDATE_FAIL:-} == "1" ]] && exit 1
exit 0
SH
cat >"$bin/omarchy-shell" <<'SH'
#!/bin/bash
if [[ $1 == "shell" && $2 == "listPlugins" ]]; then
  printf '[]\n'
fi
SH
cat >"$bin/omarchy-cmd-present" <<'SH'
#!/bin/bash
exit 1
SH
chmod +x "$bin/omarchy-plugin-validate" "$bin/omarchy-shell" "$bin/omarchy-cmd-present"

HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-update" omadock --yes >/dev/null
grep -Fqx 'glyph: "\ue90b"' "$plugin/Dock.qml" ||
  fail 'managed upstream update retains the Maslow dock glyph'
grep -Fqx 'tooltip: "Maslow OS"' "$plugin/Dock.qml" ||
  fail 'managed upstream update retains the Maslow dock tooltip'
[[ -f $plugin/README.md ]] || fail 'managed upstream update incorporates the reviewed upstream change'
[[ -z $(git -C "$plugin" status --porcelain) ]] ||
  fail 'managed upstream update leaves the checkout clean'
pass 'managed upstream update replays dock branding without blocking updates'

managed_head=$(git -C "$plugin" rev-parse HEAD)
repeat_output=$(HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-update" omadock --yes)
grep -Fqx 'omadock is up to date.' <<<"$repeat_output" ||
  fail 'managed dock detects an upstream parent already at FETCH_HEAD'
if grep -Fq 'Replaying Maslow dock display branding' <<<"$repeat_output"; then
  fail 'managed dock does not rebase when only its branding commit differs from upstream'
fi
[[ $(git -C "$plugin" rev-parse HEAD) == "$managed_head" ]] ||
  fail 'managed dock keeps its branding commit when already up to date'
pass 'managed dock repeat update avoids an unnecessary rebase'

printf '%s\n' 'upstream validation change' >"$upstream/VALIDATION.md"
git -C "$upstream" add VALIDATION.md
git -C "$upstream" commit --quiet -m 'Upstream validation change'
git -C "$upstream" push --quiet origin HEAD:main
if VALIDATE_FAIL=1 HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-update" omadock --yes >/dev/null 2>&1; then
  fail 'managed dock update returns failure when post-rebase validation fails'
fi
[[ $(git -C "$plugin" rev-parse HEAD) == "$managed_head" ]] ||
  fail 'managed dock validation failure resets to the pre-rebase branding commit'
[[ -z $(git -C "$plugin" status --porcelain) ]] ||
  fail 'managed dock validation rollback leaves no rebase or worktree changes'
pass 'managed dock validation rollback restores the pre-rebase checkout'

printf '%s\n' 'glyph: "upstream replacement"' 'tooltip: "Upstream"' >"$upstream/Dock.qml"
git -C "$upstream" add Dock.qml
git -C "$upstream" commit --quiet -m 'Change upstream dock branding lines'
git -C "$upstream" push --quiet origin HEAD:main
if HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-update" omadock --yes >/dev/null 2>&1; then
  fail 'a conflicting upstream dock change must not leave a partial managed update'
fi
[[ $(git -C "$plugin" rev-parse HEAD) == "$managed_head" ]] ||
  fail 'managed dock rebase conflict restores the pre-update branding commit'
[[ -z $(git -C "$plugin" status --porcelain) && ! -d $plugin/.git/rebase-merge && ! -d $plugin/.git/rebase-apply ]] ||
  fail 'managed dock rebase conflict leaves no in-progress operation or worktree changes'
grep -Fqx 'glyph: "\ue90b"' "$plugin/Dock.qml" || fail 'managed dock rebase conflict retains the Maslow glyph'
grep -Fqx 'tooltip: "Maslow OS"' "$plugin/Dock.qml" || fail 'managed dock rebase conflict retains the Maslow tooltip'
pass 'managed dock rebase conflict safely restores the branded checkout'

printf '%s\n' 'local user commit' >"$plugin/LOCAL.md"
git -C "$plugin" add LOCAL.md
git -C "$plugin" commit --quiet -m 'User dock change'
user_head=$(git -C "$plugin" rev-parse HEAD)
if HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-update" omadock --yes >/dev/null 2>&1; then
  fail 'user commits after managed branding do not get rebased automatically'
fi
[[ $(git -C "$plugin" rev-parse HEAD) == "$user_head" ]] ||
  fail 'user divergence leaves the dock checkout untouched'
git -C "$plugin" reset --hard --quiet "$managed_head"
pass 'managed dock keeps normal user-divergence safety'

HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-remove" omadock --yes >/dev/null
[[ ! -e $plugin ]] || fail 'managed dock remains removable through the standard plugin command'
pass 'managed dock removal keeps the standard plugin behavior'

launcher_remote="$tmpdir/app-launcher.git"
launcher_upstream="$tmpdir/app-launcher-upstream"
launcher="$home/.config/omarchy/plugins/tyrsolution.app-launcher"
git init --bare "$launcher_remote" >/dev/null
git clone --quiet "$launcher_remote" "$launcher_upstream"
git -C "$launcher_upstream" config user.name 'Tyrsolution'
git -C "$launcher_upstream" config user.email 'tyrsolution@example.invalid'
printf '%s\n' '{"schemaVersion":1,"id":"tyrsolution.app-launcher","name":"App Launcher","version":"1","kinds":["overlay"],"entryPoints":{"overlay":"AppGrid.qml"}}' \
  >"$launcher_upstream/manifest.json"
printf '%s\n' 'MIT License' >"$launcher_upstream/LICENSE"
printf '%s\n' 'Item {}' >"$launcher_upstream/AppGrid.qml"
git -C "$launcher_upstream" add .
git -C "$launcher_upstream" commit --quiet -m 'Upstream app launcher'
git -C "$launcher_upstream" push --quiet origin HEAD:main
git -C "$launcher_remote" symbolic-ref HEAD refs/heads/main
git clone --quiet "$launcher_remote" "$launcher"
printf '%s\n' 'upstream launcher change' >"$launcher_upstream/README.md"
git -C "$launcher_upstream" add README.md
git -C "$launcher_upstream" commit --quiet -m 'Upstream launcher change'
git -C "$launcher_upstream" push --quiet origin HEAD:main

HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-update" tyrsolution.app-launcher --yes >/dev/null
[[ -f $launcher/README.md ]] || fail 'App Launcher remains updateable through the standard plugin command'
[[ -z $(git -C "$launcher" status --porcelain) ]] ||
  fail 'App Launcher update leaves the upstream checkout clean'
HOME="$home" PATH="$bin:$PATH" "$ROOT/bin/omarchy-plugin-remove" tyrsolution.app-launcher --yes >/dev/null
[[ ! -e $launcher ]] || fail 'App Launcher remains removable through the standard plugin command'
pass 'App Launcher keeps standard update and removal behavior'
