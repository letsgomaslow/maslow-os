#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

run_node_test <<'JS'
const fs = require('fs')
const contrast = requireFromRoot('shell/Commons/Contrast.js')

const black = { r: 0, g: 0, b: 0 }
const white = { r: 1, g: 1, b: 1 }
assertEqual(Math.round(contrast.ratio(black, white) * 10) / 10, 21, 'black on white is 21:1')
assertEqual(contrast.ratio(white, white), 1, 'a color against itself is 1:1')
assertEqual(contrast.minimumAlpha(white, white, 0.04, 3), 1, 'an unreachable target reports full alpha')

function hex(value) {
  const h = value.replace('#', '')
  return { r: parseInt(h.slice(0, 2), 16) / 255, g: parseInt(h.slice(2, 4), 16) / 255, b: parseInt(h.slice(4, 6), 16) / 255 }
}

// Every stock theme gets idle borders that clear 3:1 against both the panel
// background and the control fill they sit between.
const themes = fs.readdirSync(root + '/themes').filter(name => fs.existsSync(`${root}/themes/${name}/colors.toml`))
let checked = 0
for (const name of themes) {
  const toml = fs.readFileSync(`${root}/themes/${name}/colors.toml`, 'utf8')
  const fg = toml.match(/^\s*foreground\s*=\s*"(#[0-9a-fA-F]{6})"/m)
  const bg = toml.match(/^\s*background\s*=\s*"(#[0-9a-fA-F]{6})"/m)
  if (!fg || !bg) continue
  const foreground = hex(fg[1])
  const background = hex(bg[1])
  const alpha = Math.max(0.4, contrast.minimumAlpha(foreground, background, 0.04, 3))
  const border = contrast.over(foreground, background, alpha)
  const fill = contrast.over(foreground, background, 0.04)
  if (contrast.ratio(border, background) < 3 || contrast.ratio(border, fill) < 3) {
    fail(`${name} idle border clears 3:1`, `alpha ${alpha}`)
  }
  if (alpha >= 0.9) fail(`${name} idle border stays below the 0.9 focus border`, `alpha ${alpha}`)
  checked++
}
assert(checked > 10, `idle borders clear 3:1 and stay below the focus border in all ${checked} stock themes`)

const style = fs.readFileSync(root + '/shell/Commons/Style.qml', 'utf8')
assert(/normalBorderAlpha: Math\.max\(configuredNormalBorderAlpha,\s*Contrast\.minimumAlpha\(/.test(style), 'Style applies the contrast floor to idle borders')
JS
