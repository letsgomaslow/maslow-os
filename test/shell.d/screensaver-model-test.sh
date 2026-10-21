#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

PLUGIN="$ROOT/shell/plugins/screensaver"

run_node_test <<'JS'
const fs = require('fs')
const model = requireFromRoot('shell/plugins/screensaver/ScreensaverModel.js')
const near = (a, b, eps = 1e-9) => Math.abs(a - b) < eps

assertEqual(model.resolveStyle(null), 'maslow', 'screensaver style defaults to maslow without config')
assertEqual(model.resolveStyle({}), 'maslow', 'screensaver style defaults to maslow without a block')
assertEqual(model.resolveStyle({ screensaver: 'classic' }), 'maslow', 'screensaver style ignores a non-object block')
assertEqual(model.resolveStyle({ screensaver: ['classic'] }), 'maslow', 'screensaver style ignores an array block')
assertEqual(model.resolveStyle({ screensaver: { style: 'classic' } }), 'classic', 'screensaver style reads classic')
assertEqual(model.resolveStyle({ screensaver: { style: ' Classic ' } }), 'classic', 'screensaver style tolerates case and spaces')
assertEqual(model.resolveStyle({ screensaver: { style: 'maslow' } }), 'maslow', 'screensaver style reads maslow')
assertEqual(model.resolveStyle({ screensaver: { style: 'matrix' } }), 'maslow', 'screensaver style rejects unknown styles')
assertEqual(model.resolveStyle({ screensaver: { style: 3 } }), 'maslow', 'screensaver style rejects non-strings')

assertEqual(model.resolveMotion(null), 'auto', 'screensaver motion defaults to auto without config')
assertEqual(model.resolveMotion({}), 'auto', 'screensaver motion defaults to auto without a block')
assertEqual(model.resolveMotion({ screensaver: { style: 'maslow' } }), 'auto', 'screensaver motion defaults to auto when unset')
assertEqual(model.resolveMotion({ screensaver: 'full' }), 'auto', 'screensaver motion ignores a non-object block')
assertEqual(model.resolveMotion({ screensaver: ['full'] }), 'auto', 'screensaver motion ignores an array block')
assertEqual(model.resolveMotion({ screensaver: { motion: 'full' } }), 'full', 'screensaver motion reads full')
assertEqual(model.resolveMotion({ screensaver: { motion: ' Reduced ' } }), 'reduced', 'screensaver motion tolerates case and spaces')
assertEqual(model.resolveMotion({ screensaver: { motion: 'auto' } }), 'auto', 'screensaver motion reads auto')
assertEqual(model.resolveMotion({ screensaver: { motion: 'fast' } }), 'auto', 'screensaver motion rejects unknown values')
assertEqual(model.resolveMotion({ screensaver: { motion: true } }), 'auto', 'screensaver motion rejects non-strings')

assertEqual(model.reducedFor('auto', false), false, 'auto motion animates when the system allows motion')
assertEqual(model.reducedFor('auto', true), true, 'auto motion holds still under system Reduced Motion')
assertEqual(model.reducedFor('full', true), false, 'full motion animates even under system Reduced Motion')
assertEqual(model.reducedFor('full', false), false, 'full motion animates')
assertEqual(model.reducedFor('reduced', false), true, 'reduced motion holds still even when the system allows motion')
assertEqual(model.reducedFor('reduced', true), true, 'reduced motion holds still')

assertEqual(model.fpsFor(false, false), 20, 'screensaver runs 20 fps on AC')
assertEqual(model.fpsFor(false, true), 10, 'screensaver runs 10 fps on battery')
assertEqual(model.fpsFor(true, false), 0, 'Reduced Motion stops the frame ticker on AC')
assertEqual(model.fpsFor(true, true), 0, 'Reduced Motion stops the frame ticker on battery')

let breathOk = true
let haloOk = true
for (let t = 0; t <= 120000; t += 97) {
  const s = model.breathScale(t, false)
  if (!(s >= 1 && s <= 1 + model.BREATH_DEPTH + 1e-12)) breathOk = false
  const h = model.haloOpacity(t, false)
  if (!(h >= 0.45 - 1e-12 && h <= 0.85 + 1e-12)) haloOk = false
}
assert(breathOk, 'breath stays within [1, 1 + BREATH_DEPTH]')
assert(near(model.breathScale(0, false), 1), 'breath starts at rest')
assert(near(model.breathScale(model.BREATH_PERIOD_MS / 2, false), 1 + model.BREATH_DEPTH), 'breath peaks half way through its period')
assert(near(model.breathScale(model.BREATH_PERIOD_MS / 2, true), 1), 'Reduced Motion does not breathe')
assert(near(model.breathScale(NaN, false), 1), 'breath tolerates invalid times')
assert(haloOk, 'halo opacity stays within [0.45, 0.85]')
assert(near(model.haloOpacity(0, false), 0.45) && near(model.haloOpacity(model.HALO_PERIOD_MS / 2, false), 0.85), 'halo swells from 0.45 to 0.85')
assert(near(model.haloOpacity(1234, true), 0.65) && near(model.haloOpacity(98765, true), 0.65), 'Reduced Motion holds the halo still')

assertEqual(model.AURORA.length, 5, 'five aurora fields light the background')
assertDeepEqual(model.AURORA.map(f => f.key), ['deep', 'violet', 'pink', 'teal', 'amber'], 'aurora fields use the brand colour assets')
const sizes = [[1440, 900], [1280, 800], [1920, 1080], [2880, 1800], [1024, 768], [3440, 1440]]
let auroraInside = true
let auroraSized = true
let auroraMoves = false
let auroraVisible = true
for (const [w, h] of sizes) {
  const shortSide = Math.min(h, w / 1.6)
  for (let i = 0; i < model.AURORA.length; i++) {
    for (let screen = 0; screen < 3; screen++) {
      const start = model.auroraField(i, 0, w, h, screen, false)
      for (let t = 0; t <= 400000; t += 1733) {
        const f = model.auroraField(i, t, w, h, screen, false)
        // Orbits stay well inside the screen so no field leaves a dark side.
        if (f.x < w * 0.1 || f.x > w * 0.9 || f.y < h * 0.1 || f.y > h * 0.9) auroraInside = false
        if (!near(f.size, shortSide * model.AURORA[i].size)) auroraSized = false
        if (!(f.opacity > 0 && f.opacity <= model.AURORA[i].opacity + 1e-12)) auroraVisible = false
        if (Math.abs(f.x - start.x) > 1 || Math.abs(f.y - start.y) > 1) auroraMoves = true
      }
    }
  }
}
assert(auroraInside, 'aurora field centres stay within the middle 80% of every screen')
assert(auroraSized, 'aurora fields scale with the short side')
assert(auroraVisible, 'aurora fields stay visible within their base opacity')
assert(auroraMoves, 'aurora fields drift over time')
assertDeepEqual(model.auroraField(2, 0, 1440, 900, 0, true), model.auroraField(2, 250000, 1440, 900, 0, true), 'Reduced Motion holds the aurora still')
const a0 = model.auroraField(1, 5000, 1440, 900, 0, false)
const a1 = model.auroraField(1, 5000, 1440, 900, 1, false)
assert(Math.abs(a0.x - a1.x) > 1 || Math.abs(a0.y - a1.y) > 1, 'neighbouring screens start their aurora at different points')
assertEqual(model.auroraField(99, 0, 1440, 900, 0, false).key, 'amber', 'out-of-range aurora indices clamp to the last field')
assert(isFinite(model.auroraField(0, NaN, NaN, NaN, NaN, false).x), 'aurora tolerates invalid inputs')

// Rasterise the bridge paths of the shipped mark (M/C/z only) into polygons and
// check every sampled bridge point falls inside the matching bridge.
const svg = fs.readFileSync(path.join(root, 'shell/plugins/screensaver/assets/maslow-mark-gradient.svg'), 'utf8')
const paths = [...svg.matchAll(/\sd="([^"]+)"/g)].map(m => m[1])
assert(paths.length >= 2, 'mark exposes its two bridge paths')
function polygon(d) {
  const tokens = d.match(/[MCz]|-?\d*\.?\d+(?:e-?\d+)?/gi)
  const points = []
  let cursor = null
  let i = 0
  while (i < tokens.length) {
    const command = tokens[i++]
    if (command === 'M') {
      cursor = [Number(tokens[i++]), Number(tokens[i++])]
      points.push(cursor)
    } else if (command === 'C') {
      const c = [cursor]
      for (let k = 0; k < 3; k++) c.push([Number(tokens[i++]), Number(tokens[i++])])
      for (let s = 1; s <= 24; s++) {
        const t = s / 24, u = 1 - t
        points.push([
          u * u * u * c[0][0] + 3 * u * u * t * c[1][0] + 3 * u * t * t * c[2][0] + t * t * t * c[3][0],
          u * u * u * c[0][1] + 3 * u * u * t * c[1][1] + 3 * u * t * t * c[2][1] + t * t * t * c[3][1]
        ])
      }
      cursor = c[3]
    } else if (command.toLowerCase() === 'z') {
      // closed implicitly
    } else {
      fail('mark path uses an unexpected command ' + command)
    }
  }
  return points
}
function inside(poly, x, y) {
  let hit = false
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j]
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) hit = !hit
  }
  return hit
}
// Inside with a margin, so a particle's core never sits on the edge.
function insideWithMargin(poly, x, y, margin) {
  if (!inside(poly, x, y)) return false
  for (let a = 0; a < 8; a++) {
    if (!inside(poly, x + margin * Math.cos(a * Math.PI / 4), y + margin * Math.sin(a * Math.PI / 4))) return false
  }
  return true
}
const bridges = [polygon(paths[0]), polygon(paths[1])]
assert(inside(bridges[0], 120, 110) && !inside(bridges[0], model.CIRCLES[0].x, model.CIRCLES[0].y) && !inside(bridges[0], model.CIRCLES[1].x, model.CIRCLES[1].y), 'the rasterised bridge covers its neck and neither standalone circle')

const lower = model.bridgePoint(0, 0)
const upper = model.bridgePoint(1, 0)
assertDeepEqual(lower, { x: model.BRIDGE_PATH[0][0], y: model.BRIDGE_PATH[0][1] }, 'bridge travel starts at the lower circle')
assertDeepEqual(upper, { x: model.BRIDGE_PATH[model.BRIDGE_PATH.length - 1][0], y: model.BRIDGE_PATH[model.BRIDGE_PATH.length - 1][1] }, 'bridge travel ends at the upper circle')
assert(lower.y > 140 && lower.x < 96, 'the lower end sits in the lower-left circle')
assert(upper.y < 107 && upper.x > 147 && upper.x < 228, 'the upper end sits in the upper circle of the first bridge')
assertDeepEqual(model.bridgePoint(-3, 0), lower, 'bridge travel clamps below 0')
assertDeepEqual(model.bridgePoint(7, 0), upper, 'bridge travel clamps above 1')
assertDeepEqual(model.bridgePoint(NaN, 0), lower, 'bridge travel tolerates invalid input')
let onBridge = true
let shifted = true
let monotonic = true
let previousY = Infinity
const misses = []
for (let n = 0; n <= 400; n++) {
  const u = n / 400
  const p0 = model.bridgePoint(u, 0)
  const p1 = model.bridgePoint(u, 1)
  if (!insideWithMargin(bridges[0], p0.x, p0.y, 3)) { onBridge = false; misses.push('0@' + u.toFixed(3)) }
  if (!insideWithMargin(bridges[1], p1.x, p1.y, 3)) { onBridge = false; misses.push('1@' + u.toFixed(3)) }
  if (!near(p1.x, p0.x + model.BRIDGE_SHIFT) || !near(p1.y, p0.y)) shifted = false
  if (p0.y > previousY + 1e-9) monotonic = false
  previousY = p0.y
}
assert(onBridge, 'every sampled bridge point lies inside its bridge with a 3-unit margin', misses.slice(0, 10).join(', '))
assert(shifted, 'the second bridge is the first shifted right by BRIDGE_SHIFT')
assert(monotonic, 'bridge travel climbs from the lower circle to the upper one')
const mid = model.bridgePoint(0.5, 0)
const halfway = (lower.x + upper.x) / 2
assert(Math.abs(mid.x - halfway) < 40, 'arc-length travel puts the midpoint near the neck')

for (const c of model.CIRCLES) {
  const poly = paths.map(polygon).find(p => inside(p, c.x, c.y) && inside(p, c.x - c.r * 0.8, c.y) && inside(p, c.x + c.r * 0.8, c.y))
  assert(!!poly, `ripple circle at ${c.x},${c.y} matches a circle of the mark`)
}

const P = model.PARTICLE_TRAVEL_MS
assertEqual(model.PARTICLES_PER_BRIDGE, 3, 'three particles cross each bridge')
assert(near(model.particle(0, 0, 0, false).opacity, 0), 'a particle is dark as it leaves the lower circle')
assert(near(model.particle(0, 0, P - 1e-6, false).opacity, 0, 1e-3), 'a particle is dark as it settles into the upper circle')
assert(near(model.particle(0, 0, P / 2, false).opacity, 1), 'a particle is brightest mid-crossing')
assert(model.particle(0, 0, P / 2, false).scale > model.particle(0, 0, P / 10, false).scale, 'a particle is largest mid-crossing')
const halfSpark = model.particle(0, 0, P / 2, false)
assert(near(halfSpark.x, model.bridgePoint(0.5, 0).x) && near(halfSpark.y, model.bridgePoint(0.5, 0).y), 'a particle is half way across at half its travel time')
let particleOnBridge = true
let staggered = true
for (let t = 0; t <= 3 * P; t += 61) {
  const lit = []
  for (let bridge = 0; bridge < 2; bridge++) {
    for (let k = 0; k < model.PARTICLES_PER_BRIDGE; k++) {
      const spark = model.particle(k, bridge, t, false)
      if (!(spark.opacity >= 0 && spark.opacity <= 1)) particleOnBridge = false
      if (!insideWithMargin(bridges[bridge], spark.x, spark.y, 3)) particleOnBridge = false
      if (spark.opacity > 0.3) lit.push(bridge)
    }
  }
  if (!lit.includes(0) || !lit.includes(1)) staggered = false
}
assert(particleOnBridge, 'particles stay on their bridge with opacity in [0, 1]')
assert(staggered, 'light is always crossing both bridges')
const p00 = model.particle(0, 0, 1000, false)
const p10 = model.particle(1, 0, 1000, false)
assert(Math.abs(p00.y - p10.y) > 5, 'particles on one bridge are spread along it')
assertDeepEqual(model.particle(1, 1, 2000, true), { x: 0, y: 0, opacity: 0, scale: 0 }, 'Reduced Motion hides the particles')

const R = model.RIPPLE_MS
assert(near(model.ripple(0, 0, false).radius, model.CIRCLES[0].r), 'a ripple starts at its circle edge')
assert(model.ripple(0, 0, false).opacity > 0.5, 'a ripple starts visible')
assertEqual(model.ripple(1, 0, false).opacity, 0, 'the other circle waits its turn')
assertEqual(model.ripple(0, R + 10, false).opacity, 0, 'the first circle rests while the second ripples')
assert(model.ripple(1, R + 10, false).opacity > 0.5, 'the second circle ripples after the first')
let oneAtATime = true
let grows = true
let fades = true
let previous = null
for (let t = 0; t < 4 * R; t += 37) {
  const r0 = model.ripple(0, t, false)
  const r1 = model.ripple(1, t, false)
  if (r0.opacity > 0.001 && r1.opacity > 0.001) oneAtATime = false
  if (previous && r0.opacity > 0 && previous.opacity > 0 && t % (2 * R) > 37) {
    if (r0.radius < previous.radius - 1e-9) grows = false
    if (r0.opacity > previous.opacity + 1e-9) fades = false
  }
  if (r0.radius > model.CIRCLES[0].r * model.RIPPLE_REACH + 1e-9) grows = false
  previous = r0
}
assert(oneAtATime, 'the two circles take turns rippling')
assert(grows, 'a ripple grows outward and never beyond RIPPLE_REACH')
assert(fades, 'a ripple fades as it grows')
assert(model.ripple(0, R * 0.99, false).radius > model.CIRCLES[0].r * (model.RIPPLE_REACH - 0.1), 'a ripple reaches nearly RIPPLE_REACH times its circle')
assertEqual(model.ripple(0, 1000, true).opacity, 0, 'Reduced Motion hides the first ripple')
assertEqual(model.ripple(1, R + 1000, true).opacity, 0, 'Reduced Motion hides the second ripple')
assertEqual(model.ripple(1, 0, false).x, model.CIRCLES[1].x, 'the second ripple centres on the second circle')

let driftBounded = true
let driftMoves = false
let driftSmooth = true
for (const [w, h] of sizes) {
  for (let screen = 0; screen < 3; screen++) {
    let last = null
    for (let t = 0; t <= 400000; t += 50) {
      const d = model.drift(t, w, h, false, 0, screen)
      if (Math.abs(d.x) > Math.round(model.DRIFT_X * w) || Math.abs(d.y) > Math.round(model.DRIFT_Y * h)) driftBounded = false
      if (d.x !== 0 || d.y !== 0) driftMoves = true
      // At 20 fps a frame is 50 ms: the drift never visibly jumps.
      if (last && (Math.abs(d.x - last.x) > 1 || Math.abs(d.y - last.y) > 1)) driftSmooth = false
      last = d
    }
    for (let cycle = 0; cycle < 40; cycle++) {
      const d = model.drift(0, w, h, true, cycle, screen)
      if (Math.abs(d.x) > Math.round(model.DRIFT_X * w) || Math.abs(d.y) > Math.round(model.DRIFT_Y * h)) driftBounded = false
    }
  }
}
assert(driftBounded, 'drift stays within DRIFT_X and DRIFT_Y of the centre')
assert(driftMoves, 'the composition drifts')
assert(driftSmooth, 'the drift moves at most a pixel per frame')
assertDeepEqual(model.drift(0, 1440, 900, true, 3, 0), model.drift(250000, 1440, 900, true, 3, 0), 'Reduced Motion drift depends only on its cycle')
assert(JSON.stringify(model.drift(0, 1440, 900, true, 0, 0)) !== JSON.stringify(model.drift(0, 1440, 900, true, 1, 0)), 'Reduced Motion jumps to a new place each cycle')
assert(JSON.stringify(model.drift(5000, 1440, 900, false, 0, 0)) !== JSON.stringify(model.drift(5000, 1440, 900, false, 0, 1)), 'screens drift on different paths')
assertEqual(model.REDUCED_REPOSITION_MS, 300000, 'Reduced Motion moves the composition every five minutes')
assertDeepEqual(model.drift(NaN, NaN, NaN, false, NaN, NaN), { x: 0, y: 0 }, 'drift tolerates invalid inputs')

const screens = [
  { name: 'HDMI-A-1', x: 2880, y: 0, width: 1920, height: 1080 },
  { name: '', x: 0, y: 0, width: 1920, height: 1080 },
  { name: 'eDP-1', x: 0, y: 0, width: 2880, height: 1800 },
  { name: 'DP-2', x: 2880, y: -1080, width: 1920, height: 1080 },
  { name: 'ghost', x: 100, y: 0, width: 0, height: 0 },
  null
]
assertDeepEqual(model.orderScreens(screens).map(s => s.name), ['eDP-1', 'DP-2', 'HDMI-A-1'], 'screens order by x then y and drop placeholders')
assertDeepEqual(model.orderScreens(null), [], 'no screens orders to an empty list')

for (const name of ['glow.png', 'particle.png', 'ring.png', 'maslow-mark-gradient.svg', ...model.AURORA.map(f => `aurora-${f.key}.png`)]) {
  assert(fs.existsSync(path.join(root, 'shell/plugins/screensaver/assets', name)), `screensaver ships ${name}`)
}
JS

manifest="$PLUGIN/manifest.json"
[[ $(jq -r '.id' "$manifest") == "maslow.screensaver" ]] || fail "screensaver manifest uses the maslow.screensaver id"
[[ $(jq -r '.kinds | join(",")' "$manifest") == "service" ]] || fail "screensaver manifest is a service"
[[ $(jq -r '.keepLoaded' "$manifest") == "true" ]] || fail "screensaver manifest keeps the service loaded"
[[ $(jq -r '.entryPoints.service' "$manifest") == "Service.qml" ]] || fail "screensaver manifest points at Service.qml"
jq -e '[.name, .description, .author] | all(test("Omarchy") | not)' "$manifest" >/dev/null || fail "screensaver manifest shows no Omarchy branding"
pass "screensaver manifest declares the Maslow service contract"

# Every frame is drawn by the one Timer in Service.qml. Animation types,
# runtime effects and layers would each add their own clock or offscreen pass,
# which is the cost this design exists to avoid on old GPUs.
forbidden='\b(NumberAnimation|ColorAnimation|PropertyAnimation|SequentialAnimation|ParallelAnimation|SmoothedAnimation|SpringAnimation|RotationAnimation|FrameAnimation|Behavior|AnimatedImage|AnimatedSprite|ShaderEffect|ShaderEffectSource|MultiEffect|Canvas|MediaPlayer|Video)\b|layer\.enabled'
if hits=$(grep -nE "$forbidden" "$PLUGIN"/*.qml "$PLUGIN"/*.js); then
  fail "screensaver uses no animation, effect, layer or video types" "$hits"
fi
pass "screensaver uses no animation, effect, layer or video types"

timers=$(grep -c '^\s*Timer {' "$PLUGIN/Service.qml")
grep -q 'running: root.active && !root.handingOff && root.fps > 0' "$PLUGIN/Service.qml" || fail "the frame ticker runs only while showing with a frame rate"
if grep -q 'Timer {' "$PLUGIN/ScreensaverScene.qml" "$PLUGIN/ScreensaverWindow.qml"; then
  fail "only the service owns timers"
fi
(( timers == 4 )) || fail "the service owns exactly its frame, Reduced Motion reposition, arm and handoff timers (found $timers)"
pass "one frame ticker drives the screensaver"

untyped=$(awk '/^\s*Text \{/ { inside = 1; typed = 0; start = FNR } inside && /textFormat: Text.PlainText/ { typed = 1 } inside && /^\s*\}/ { if (!typed) print FILENAME ":" start; inside = 0 }' "$PLUGIN"/*.qml)
[[ -z $untyped ]] || fail "every screensaver Text is plain text" "$untyped"
pass "every screensaver Text is plain text"

grep -q 'target: "screensaver"' "$PLUGIN/Service.qml" || fail "screensaver registers its IPC target"
for function in show preview hide status style; do
  grep -qE "function $function\(\): string" "$PLUGIN/Service.qml" || fail "screensaver IPC exposes $function()"
done
pass "screensaver IPC exposes show, preview, hide, status and style"

grep -q 'WlrLayershell.namespace: "maslow-screensaver"' "$PLUGIN/ScreensaverWindow.qml" || fail "screensaver overlay uses the maslow-screensaver namespace"
grep -q 'cursorShape: Qt.BlankCursor' "$PLUGIN/ScreensaverWindow.qml" || fail "screensaver hides the pointer over its overlay"
grep -q 'typeof idle.setNativeScreensaverVisible === "function"' "$PLUGIN/Service.qml" || fail "screensaver reports to idle only when idle supports it"
pass "screensaver overlay and idle reporting follow the contract"

if grep -nE 'Quickshell\.shellDir|env\("HOME"\) *\+ *"/\.local/share/omarchy' "$PLUGIN"/*.qml; then
  fail "screensaver assets come from the injected omarchyPath"
fi
cmp -s "$ROOT/branding/logos/maslow-mark-gradient.svg" "$PLUGIN/assets/maslow-mark-gradient.svg" || fail "screensaver ships the canonical Gradient Bridge mark"
pass "screensaver ships the canonical mark and reads assets from omarchyPath"
