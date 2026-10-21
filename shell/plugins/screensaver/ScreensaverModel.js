// Pure timing and layout for the Maslow screensaver. Every visual is a function
// of elapsed milliseconds so one Timer drives the whole scene and the gallery
// fixture can render any instant without waiting for it.

var STYLES = ["maslow", "classic"]
var DEFAULT_STYLE = "maslow"

var FPS_AC = 20
var FPS_BATTERY = 10

var BREATH_PERIOD_MS = 9000
var BREATH_DEPTH = 0.025
var HALO_PERIOD_MS = 7000

// Light crossing a bridge from its lower circle to its upper one.
var PARTICLE_TRAVEL_MS = 5600
var PARTICLES_PER_BRIDGE = 3

// A ripple leaves one standalone circle, then the other.
var RIPPLE_MS = 4200

// The whole composition wanders slowly so no pixel holds the same light.
var DRIFT_X_MS = 97000
var DRIFT_Y_MS = 131000
var DRIFT_X = 0.03
var DRIFT_Y = 0.025

// Reduced Motion: a still frame that jumps to the next drift position.
var REDUCED_REPOSITION_MS = 300000

// Aurora fields behind everything: brand colours on slow, mismatched orbits so
// the background never visibly repeats. size is relative to the scene's short
// side; ax/ay are the orbit radius as a share of width/height; periods in ms.
var AURORA = [
  { key: "deep", size: 1.9, opacity: 0.85, ax: 0.10, ay: 0.08, px: 83000, py: 67000, phase: 0.0 },
  { key: "violet", size: 1.45, opacity: 0.42, ax: 0.30, ay: 0.22, px: 61000, py: 47000, phase: 1.7 },
  { key: "pink", size: 1.25, opacity: 0.40, ax: 0.34, ay: 0.26, px: 53000, py: 71000, phase: 3.1 },
  { key: "teal", size: 1.25, opacity: 0.38, ax: 0.33, ay: 0.28, px: 59000, py: 43000, phase: 4.6 },
  { key: "amber", size: 0.85, opacity: 0.16, ax: 0.38, ay: 0.30, px: 89000, py: 77000, phase: 2.4 }
]

// Centre line of the lower-left bridge in the mark's 374x249 viewBox, traced
// from branding/logos/maslow-mark-gradient.svg: lower circle, the neck, then
// the upper circle. The second bridge is the same shape BRIDGE_SHIFT to the
// right.
var BRIDGE_PATH = [
  [47, 192], [71, 186.5], [81, 181], [91, 170.5], [101, 143], [111, 129.5],
  [121, 116], [131, 97.5], [141, 75], [151, 67], [161, 62], [181, 58]
]
var BRIDGE_SHIFT = 132

// Standalone circles, as centre and radius in viewBox units. The upper one is
// the mark's restored circle: the lower one's twin moved by (-264.5, -132.25).
var CIRCLES = [
  { x: 48.5, y: 57.75, r: 47.5 },
  { x: 313, y: 190, r: 47.5 }
]

var TAU = 2 * Math.PI

function resolveStyle(shellConfig) {
  var block = shellConfig && shellConfig.screensaver
  if (!block || typeof block !== "object" || Array.isArray(block)) return DEFAULT_STYLE
  var style = typeof block.style === "string" ? block.style.trim().toLowerCase() : ""
  return STYLES.indexOf(style) !== -1 ? style : DEFAULT_STYLE
}

// screensaver.motion: "auto" follows the system Reduced Motion setting,
// "full" always animates the screensaver, "reduced" always holds it still.
var MOTIONS = ["auto", "full", "reduced"]
var DEFAULT_MOTION = "auto"

function resolveMotion(shellConfig) {
  var block = shellConfig && shellConfig.screensaver
  if (!block || typeof block !== "object" || Array.isArray(block)) return DEFAULT_MOTION
  var motion = typeof block.motion === "string" ? block.motion.trim().toLowerCase() : ""
  return MOTIONS.indexOf(motion) !== -1 ? motion : DEFAULT_MOTION
}

function reducedFor(motion, systemReduced) {
  if (motion === "full") return false
  if (motion === "reduced") return true
  return !!systemReduced
}

function fpsFor(reduced, onBattery) {
  if (reduced) return 0
  return onBattery ? FPS_BATTERY : FPS_AC
}

function finiteOr(value, fallback) {
  var n = Number(value)
  return isFinite(n) ? n : fallback
}

function time(elapsedMs) {
  return Math.max(0, finiteOr(elapsedMs, 0))
}

// Range [1, 1 + BREATH_DEPTH]. The scene rasterises the mark at the largest
// size and scales down from it, so the edge never softens by upscaling.
function breathScale(elapsedMs, reduced) {
  if (reduced) return 1
  return 1 + BREATH_DEPTH / 2 * (1 - Math.cos(TAU * time(elapsedMs) / BREATH_PERIOD_MS))
}

// The halo behind the mark swells and settles, 0.45..0.85.
function haloOpacity(elapsedMs, reduced) {
  if (reduced) return 0.65
  return 0.65 - 0.2 * Math.cos(TAU * time(elapsedMs) / HALO_PERIOD_MS)
}

// Centre, size and opacity of aurora field i. Each screen starts the orbits at
// a different point so neighbouring monitors do not mirror each other.
function auroraField(index, elapsedMs, w, h, screenIndex, reduced) {
  var field = AURORA[Math.min(AURORA.length - 1, Math.max(0, Math.floor(finiteOr(index, 0))))]
  var width = Math.max(0, finiteOr(w, 0))
  var height = Math.max(0, finiteOr(h, 0))
  var shortSide = Math.min(height, width / 1.6)
  var t = reduced ? 0 : time(elapsedMs)
  var phase = field.phase + Math.max(0, Math.floor(finiteOr(screenIndex, 0))) * 1.3
  var x = width / 2 + field.ax * width * Math.sin(TAU * t / field.px + phase)
  var y = height / 2 + field.ay * height * Math.sin(TAU * t / field.py + phase * 1.37)
  var pulse = reduced ? 1 : 0.8 + 0.2 * Math.sin(TAU * t / (field.px * 0.41) + phase)
  return { key: field.key, x: x, y: y, size: shortSide * field.size, opacity: field.opacity * pulse }
}

var bridgeLengths = (function() {
  var lengths = [0]
  for (var i = 1; i < BRIDGE_PATH.length; i++) {
    var dx = BRIDGE_PATH[i][0] - BRIDGE_PATH[i - 1][0]
    var dy = BRIDGE_PATH[i][1] - BRIDGE_PATH[i - 1][1]
    lengths.push(lengths[i - 1] + Math.sqrt(dx * dx + dy * dy))
  }
  return lengths
})()

// Point a share u (0..1) of the way along a bridge, by arc length.
function bridgePoint(u, bridge) {
  var total = bridgeLengths[bridgeLengths.length - 1]
  var target = Math.min(1, Math.max(0, finiteOr(u, 0))) * total
  var shift = bridge === 1 ? BRIDGE_SHIFT : 0
  for (var i = 1; i < BRIDGE_PATH.length; i++) {
    if (target <= bridgeLengths[i] || i === BRIDGE_PATH.length - 1) {
      var span = bridgeLengths[i] - bridgeLengths[i - 1]
      var f = span > 0 ? (target - bridgeLengths[i - 1]) / span : 0
      f = Math.min(1, Math.max(0, f))
      return {
        x: BRIDGE_PATH[i - 1][0] + (BRIDGE_PATH[i][0] - BRIDGE_PATH[i - 1][0]) * f + shift,
        y: BRIDGE_PATH[i - 1][1] + (BRIDGE_PATH[i][1] - BRIDGE_PATH[i - 1][1]) * f
      }
    }
  }
  return { x: BRIDGE_PATH[0][0] + shift, y: BRIDGE_PATH[0][1] }
}

// Particle k on a bridge: it eases out of the lower circle, crosses the neck
// and settles into the upper circle, brightest mid-crossing. The two bridges
// run half a stagger apart so light is always moving somewhere.
function particle(k, bridge, elapsedMs, reduced) {
  if (reduced) return { x: 0, y: 0, opacity: 0, scale: 0 }
  var count = PARTICLES_PER_BRIDGE
  var offset = (Math.floor(finiteOr(k, 0)) + (bridge === 1 ? 0.5 : 0)) / count
  var cycle = time(elapsedMs) / PARTICLE_TRAVEL_MS + offset
  var f = cycle - Math.floor(cycle)
  var u = 0.5 - 0.5 * Math.cos(Math.PI * f)
  var point = bridgePoint(u, bridge)
  var glow = Math.sin(Math.PI * f)
  return { x: point.x, y: point.y, opacity: Math.pow(glow, 0.8), scale: 0.7 + 0.5 * glow }
}

// Ripple from standalone circle `which`: its radius grows from the circle's
// edge to RIPPLE_REACH times it while fading. The circles take turns.
var RIPPLE_REACH = 3.2

function ripple(which, elapsedMs, reduced) {
  var circle = CIRCLES[which === 1 ? 1 : 0]
  if (reduced) return { x: circle.x, y: circle.y, radius: circle.r, opacity: 0 }
  var cycle = time(elapsedMs) / (RIPPLE_MS * 2) + (which === 1 ? 0.5 : 0)
  var f = (cycle - Math.floor(cycle)) * 2
  if (f >= 1) return { x: circle.x, y: circle.y, radius: circle.r, opacity: 0 }
  var ease = 1 - Math.pow(1 - f, 2.2)
  return {
    x: circle.x,
    y: circle.y,
    radius: circle.r * (1 + (RIPPLE_REACH - 1) * ease),
    opacity: 0.55 * Math.pow(1 - f, 1.4)
  }
}

// Offset of the whole composition from the centre. Reduced Motion holds one
// position per cycle and jumps to the next.
function drift(elapsedMs, w, h, reduced, reducedCycle, screenIndex) {
  var width = Math.max(0, finiteOr(w, 0))
  var height = Math.max(0, finiteOr(h, 0))
  var t = reduced ? Math.max(0, Math.floor(finiteOr(reducedCycle, 0))) * 37000 : time(elapsedMs)
  var phase = Math.max(0, Math.floor(finiteOr(screenIndex, 0))) * 0.9
  return {
    x: Math.round(DRIFT_X * width * Math.sin(TAU * t / DRIFT_X_MS + phase)),
    y: Math.round(DRIFT_Y * height * Math.sin(TAU * t / DRIFT_Y_MS + phase + 1))
  }
}

function isRealScreen(screen) {
  return !!(screen && screen.name && Number(screen.width) > 0 && Number(screen.height) > 0)
}

// Real outputs only, left to right then top to bottom, so screen indices match
// what the user sees.
function orderScreens(screens) {
  var list = []
  var source = screens || []
  for (var i = 0; i < source.length; i++) {
    if (isRealScreen(source[i])) list.push(source[i])
  }
  list.sort(function(a, b) {
    var ax = finiteOr(a.x, 0), bx = finiteOr(b.x, 0)
    if (ax !== bx) return ax - bx
    var ay = finiteOr(a.y, 0), by = finiteOr(b.y, 0)
    if (ay !== by) return ay - by
    return String(a.name) < String(b.name) ? -1 : String(a.name) > String(b.name) ? 1 : 0
  })
  return list
}

if (typeof module !== "undefined") {
  module.exports = {
    STYLES: STYLES,
    DEFAULT_STYLE: DEFAULT_STYLE,
    MOTIONS: MOTIONS,
    DEFAULT_MOTION: DEFAULT_MOTION,
    FPS_AC: FPS_AC,
    FPS_BATTERY: FPS_BATTERY,
    BREATH_PERIOD_MS: BREATH_PERIOD_MS,
    BREATH_DEPTH: BREATH_DEPTH,
    HALO_PERIOD_MS: HALO_PERIOD_MS,
    PARTICLE_TRAVEL_MS: PARTICLE_TRAVEL_MS,
    PARTICLES_PER_BRIDGE: PARTICLES_PER_BRIDGE,
    RIPPLE_MS: RIPPLE_MS,
    RIPPLE_REACH: RIPPLE_REACH,
    DRIFT_X: DRIFT_X,
    DRIFT_Y: DRIFT_Y,
    REDUCED_REPOSITION_MS: REDUCED_REPOSITION_MS,
    AURORA: AURORA,
    BRIDGE_PATH: BRIDGE_PATH,
    BRIDGE_SHIFT: BRIDGE_SHIFT,
    CIRCLES: CIRCLES,
    resolveStyle: resolveStyle,
    resolveMotion: resolveMotion,
    reducedFor: reducedFor,
    fpsFor: fpsFor,
    breathScale: breathScale,
    haloOpacity: haloOpacity,
    auroraField: auroraField,
    bridgePoint: bridgePoint,
    particle: particle,
    ripple: ripple,
    drift: drift,
    isRealScreen: isRealScreen,
    orderScreens: orderScreens
  }
}
