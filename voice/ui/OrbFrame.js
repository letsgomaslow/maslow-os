.pragma library
// Eye motion for the Voice orb, adapted from Moodstone's frame engine
// (https://github.com/karacca/moodstone, src/core/frame.ts and math.ts).
//
// MIT License
//
// Copyright (c) 2026 Ömer Karaca
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
//
// Every function is pure in (mood, seconds). Geometry is in a 64-unit box
// centred on 32 whose body radius is 28. Maslow's face keeps its taller pupil
// eyes and mouth, so rest geometry and the largest vertical travels differ
// from Moodstone's; the timing, easing and choreography are unchanged.

var CENTER = 32
var BODY_RADIUS = 28
var EYE = { w: 7, h: 13.5, r: 3.5, cxL: 24, cxR: 40, cy: 29.5 }
var MOUTH_Y = 43
var TAU = Math.PI * 2

var MOODS = {
  idle: { cycle: 5.5, reps: 2 },
  observing: { cycle: 6.5, reps: 2 },
  thinking: { cycle: 5.5, reps: 1 },
  working: { cycle: 3.75, reps: 1 },
  done: { cycle: 3.2, reps: 1 },
  failed: { cycle: 5.5, reps: 1 },
  inactive: { cycle: 3.4, reps: 1 },
  resting: { cycle: 1, reps: 1 }
}

function clamp(v, a, b) { return v < a ? a : v > b ? b : v }
function lerp(a, b, u) { return a + (b - a) * u }
function wrap01(x) { return ((x % 1) + 1) % 1 }
function easeInOut(x) { return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2 }
function easeBack(x) { var c = 2.2; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2) }
function smoothstep(x) { var u = clamp(x, 0, 1); return u * u * (3 - 2 * u) }
function ramp(p, a, b) { return p <= a ? 0 : p >= b ? 1 : easeInOut((p - a) / (b - a)) }
function pulse(p, w) { return ramp(p, w[0], w[1]) - ramp(p, w[2], w[3]) }

function loopLength(mood) { var m = MOODS[mood] || MOODS.idle; return m.cycle * m.reps }

function restPose(side, dx, dy) {
  return { cx: (side === 1 ? EYE.cxR : EYE.cxL) + dx, cy: EYE.cy + dy, w: EYE.w, h: EYE.h, r: EYE.r, rot: 0, alpha: 1 }
}
function dotPose(cx, cy, d) { return { cx: cx, cy: cy, w: d, h: d, r: d / 2, rot: 0, alpha: 1 } }
function lerpPose(a, b, u) {
  return { cx: lerp(a.cx, b.cx, u), cy: lerp(a.cy, b.cy, u), w: lerp(a.w, b.w, u), h: lerp(a.h, b.h, u), r: lerp(a.r, b.r, u), rot: lerp(a.rot, b.rot, u), alpha: lerp(a.alpha, b.alpha, u) }
}
function calm(poses) { return { poses: poses, tilt: 0, offset: [0, 0], openness: 1, swirl: 0, sleep: 0 } }

// Keys are [phase, leftDx, leftDy, rightDx, rightDy, overshoot].
function gazeAt(track, p) {
  for (var k = 0; k < track.length - 1; k++) {
    var a = track[k], b = track[k + 1]
    if (p >= a[0] && p <= b[0]) {
      var u = clamp((p - a[0]) / (b[0] - a[0] || 1), 0, 1)
      var e = b[5] === 1 ? easeBack(u) : easeInOut(u)
      return [lerp(a[1], b[1], e), lerp(a[2], b[2], e), lerp(a[3], b[3], e), lerp(a[4], b[4], e)]
    }
  }
  var z = track[track.length - 1]
  return [z[1], z[2], z[3], z[4]]
}

// Blinks shut faster than they reopen.
var BLINK_CLOSE = 0.09
var BLINK_OPEN = 0.14
function blinkCurve(d, closeN, openN) {
  if (d < -closeN || d > openN) return 1
  if (d < 0) return 0.5 * (1 + Math.cos(Math.PI * (d + closeN) / closeN))
  return 0.5 * (1 - Math.cos(Math.PI * d / openN))
}
function opennessAt(p, cycle, blinks, durationScale) {
  var o = 1
  var cN = BLINK_CLOSE * durationScale / cycle
  var oN = BLINK_OPEN * durationScale / cycle
  for (var i = 0; i < blinks.length; i++) {
    var d = p - blinks[i]
    if (d > 0.5) d -= 1
    if (d < -0.5) d += 1
    o = Math.min(o, blinkCurve(d, cN, oN))
  }
  return clamp(o, 0, 1)
}

// Idle: a small glance up-right, then down-left, two blinks per cycle.
var IDLE_TRACK = [[0, 0, 0, 0, 0, 0], [0.3, 1.5, -1, 1.2, -1, 0], [0.62, -1.2, 0.6, -1.5, 0.6, 0], [1, 0, 0, 0, 0, 0]]
function idle(p, cycle) {
  var g = gazeAt(IDLE_TRACK, p)
  var s = calm([restPose(0, g[0], g[1]), restPose(1, g[2], g[3])])
  s.openness = opennessAt(p, cycle, [0.3, 0.8], 1)
  return s
}

// Observing: looks up-right, then up-left; the head turns with the gaze.
// Vertical travel is reduced from 15 to 9 so the taller eyes stay inside.
var OBSERVE_TRACK = [[0, 0, 0, 0, 0, 0], [0.09, 0, 0, 0, 0, 0], [0.17, 11, -9, 6, -9, 1], [0.33, 11, -9, 6, -9, 0], [0.44, -6, -7, -11, -7, 1], [0.64, -6, -7, -11, -7, 0], [0.72, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 0]]
function observing(p, cycle) {
  var g = gazeAt(OBSERVE_TRACK, p)
  var look = (g[0] + g[2]) / 2
  var narrow = 1 - clamp(Math.abs(look) / 9.5, 0, 1) * 0.3
  var left = restPose(0, g[0], g[1]), right = restPose(1, g[2], g[3])
  // The eye on the side the head turns toward is further away.
  if (look > 0) right.w *= narrow
  else if (look < 0) left.w *= narrow
  var s = calm([left, right])
  s.tilt = -look * 0.65
  s.openness = opennessAt(p, cycle, [0.135, 0.455, 0.735], 1)
  return s
}

// Thinking: the eyes merge into one dot that bobs three times.
var THINK_MERGE = [0.2, 0.32, 0.82, 0.96]
function thinking(p, cycle) {
  var merge = pulse(p, THINK_MERGE)
  var bob = clamp((p - THINK_MERGE[1]) / (THINK_MERGE[2] - THINK_MERGE[1]), 0, 1)
  var wave = Math.sin(TAU * 3 * bob)
  var dot = dotPose(CENTER, CENTER - 2 + 9 * wave, 7.8)
  var s = calm([lerpPose(restPose(0, 0, 0), dot, merge), lerpPose(restPose(1, 0, 0), dot, merge)])
  s.offset = [0, bob > 0 && bob < 1 ? 1.2 * wave : 0]
  s.openness = opennessAt(p, cycle, [0.1], 1)
  return s
}

// Working: the eyes read three lines like text.
var WORK_LINE_Y = [-7, -1, 5]
var WORK_SWEEP = 7
var WORK_READ = 0.82
function working(p, cycle) {
  var along = (p * 3) % 1
  var line = Math.floor(p * 3) % 3
  var dx, dy = WORK_LINE_Y[line]
  if (along < WORK_READ) {
    dx = -WORK_SWEEP + 2 * WORK_SWEEP * (along / WORK_READ)
  } else {
    var back = easeInOut((along - WORK_READ) / (1 - WORK_READ))
    dx = WORK_SWEEP - 2 * WORK_SWEEP * back
    dy = lerp(dy, WORK_LINE_Y[(line + 1) % 3], back)
  }
  var s = calm([restPose(0, dx, dy), restPose(1, dx, dy)])
  s.tilt = -0.35 * dx
  s.openness = opennessAt(p, cycle, [0.303, 0.637, 0.97], 0.7)
  return s
}

// Done: a happy squint, a jump and a wiggle. It plays once; joy ends by 0.82.
var DONE_SQUINT = [0.08, 0.16, 0.36, 0.5]
var DONE_END = 0.82
function done(p) {
  var joy = p < 0.06 ? p / 0.06 : 1 - ramp(p, 0.65, DONE_END)
  var squint = pulse(p, DONE_SQUINT)
  var wave = Math.sin(TAU * 7 * p)
  var poses = []
  for (var i = 0; i < 2; i++) {
    var rest = restPose(i, 0, 0)
    // Flat slits tilted toward the middle: the eyes' "^ ^".
    var slit = { cx: rest.cx, cy: rest.cy - 0.5, w: 7.4, h: 2.8, r: 1.4, rot: i === 1 ? 0.34 : -0.34, alpha: 1 }
    var e = lerpPose(rest, slit, squint)
    e.cx += joy * 5 * wave
    e.cy -= joy * 8
    poses.push(e)
  }
  var s = calm(poses)
  s.tilt = joy * 10 * wave
  return s
}

// Failed: the eyes drop and bounce, the body shakes, the eyes go dizzy. A
// persistent error plays this once and holds the fallen pose at FAILED_HOLD.
var FALL_TOP = EYE.cy
var FALL_FLOOR = EYE.cy + 7
var FALL_START = 0.14
var FALL_SETTLED = 0.38
var FAIL_SWIRL = [0.37, 0.53, 0.72, 0.82]
var FAILED_HOLD = 0.82
function bounceHeight(u) {
  var r = 0.55
  var durs = [1, 2 * r, 2 * r * r, 2 * r * r * r, 2 * r * r * r * r]
  var total = 0
  for (var i = 0; i < durs.length; i++) total += durs[i]
  var t = u * total, acc = 0
  for (var k = 0; k < durs.length; k++) {
    var seg = (t - acc) / durs[k]
    if (t <= acc + durs[k]) return k === 0 ? 1 - seg * seg : Math.pow(r, 2 * k) * (1 - Math.pow(2 * seg - 1, 2))
    acc += durs[k]
  }
  return 0
}
function failed(p, cycle) {
  var drop = FALL_FLOOR - FALL_TOP
  var y = p < FALL_START ? FALL_TOP : p < FALL_SETTLED ? FALL_FLOOR - bounceHeight((p - FALL_START) / (FALL_SETTLED - FALL_START)) * drop : FALL_FLOOR
  var height = clamp((FALL_FLOOR - y) / drop, 0, 1)
  // The eyes stretch as they fall and squash flat near the floor.
  var contact = clamp(1 - height / 0.1, 0, 1)
  var sy = lerp(1 + 0.3 * (1 - height), 0.5, contact)
  var sx = 1 / Math.sqrt(sy)
  var w = EYE.w * sx, h = EYE.h * sy
  var r = Math.min(EYE.r, w / 2, h / 2)
  var s = calm([{ cx: EYE.cxL, cy: y, w: w, h: h, r: r, rot: 0, alpha: 1 }, { cx: EYE.cxR, cy: y, w: w, h: h, r: r, rot: 0, alpha: 1 }])
  if (p >= 0.215 && p <= 0.345) {
    var u = (p - 0.215) / 0.13
    var fade = Math.pow(1 - u, 2)
    s.offset = [1.1 * fade * Math.sin(TAU * 8 * u + 1), 2.2 * fade * Math.sin(TAU * 9 * u)]
  }
  s.openness = opennessAt(p, cycle, [0.07], 1)
  s.swirl = pulse(p, FAIL_SWIRL)
  return s
}

// Inactive: asleep, drooped and nearly shut, with "z"s drifting up.
function inactive(p) {
  var s = calm([restPose(0, 0, 3), restPose(1, 0, 3)])
  s.openness = 0.05 + 0.02 * Math.sin(p * TAU)
  s.sleep = 1
  return s
}

// Resting (paused or muted): drooped and half shut, without sleep marks.
function resting() {
  var s = calm([restPose(0, 0, 3), restPose(1, 0, 3)])
  s.openness = 0.24
  return s
}

function moodState(mood, p, cycle) {
  switch (mood) {
  case "observing": return observing(p, cycle)
  case "thinking": return thinking(p, cycle)
  case "working": return working(p, cycle)
  case "done": return done(p)
  case "failed": return failed(p, cycle)
  case "inactive": return inactive(p)
  case "resting": return resting()
  default: return idle(p, cycle)
  }
}

function hiddenEye() { return { cx: CENTER, cy: CENTER, w: 0, h: 0, r: 0, rot: 0, alpha: 0 } }

function swirlPoints(s) {
  var n = 36, out = []
  for (var i = 0; i <= n; i++) {
    var f = i / n * s.grow
    var th = s.dir * 2.3 * TAU * f + s.rot
    out.push([s.cx + s.radius * f * Math.cos(th), s.cy + s.radius * f * Math.sin(th)])
  }
  return out
}

// Three "z"s a third of a cycle apart, drifting up and right as they grow.
// They stay inside the body so they never draw on the desktop background.
function sleepMarks(p) {
  var marks = []
  for (var k = 0; k < 3; k++) {
    var ph = wrap01(p + k / 3)
    var a = ph < 0.16 ? ph / 0.16 : ph > 0.72 ? (1 - ph) / 0.28 : 1
    marks.push({ x: 40 + ph * 4, y: 26 - ph * 10, size: 3 + ph * 2, alpha: clamp(a, 0, 1) * 0.92 })
  }
  return marks
}

// A frame for `mood` at `seconds` into it, with blink squash, swirls and
// sleep marks applied. "done" and "failed" do not loop: they hold their end.
function frameAt(mood, seconds) {
  var info = MOODS[mood] || MOODS.idle
  var length = info.cycle * info.reps
  var t = mood === "done" ? clamp(seconds, 0, DONE_END * info.cycle) : mood === "failed" ? clamp(seconds, 0, FAILED_HOLD * info.cycle) : ((seconds % length) + length) % length
  var p = mood === "done" || mood === "failed" ? t / info.cycle : wrap01(t / info.cycle)
  var s = moodState(mood, p, info.cycle)
  // Shut eyes get a touch wider and almost flat.
  var sx = 1 + 0.05 * (1 - s.openness)
  var sy = 0.08 + 0.92 * s.openness
  var eyes = []
  for (var i = 0; i < 2; i++) {
    var pose = i < s.poses.length ? s.poses[i] : hiddenEye()
    var w = pose.w * sx, h = pose.h * sy
    eyes.push({ cx: pose.cx, cy: pose.cy, w: w, h: h, r: Math.max(0, Math.min(pose.r * Math.min(sx, sy), w / 2, h / 2)), rot: pose.rot, alpha: pose.alpha })
  }
  // Dizzy swirls take over as the eyes shrink and fade.
  var swirls = []
  if (s.swirl > 0.001) {
    var grow = smoothstep((s.swirl - 0.12) / 0.88)
    var rot = 1.75 * TAU * Math.pow(1 - s.swirl, 3)
    var eyeScale = clamp(1 - s.swirl * 1.3, 0, 1)
    for (var j = 0; j < 2; j++) {
      var e = eyes[j]
      swirls.push({ cx: e.cx, cy: e.cy, radius: 4.2, dir: j === 0 ? -1 : 1, grow: grow, rot: rot, alpha: clamp(s.swirl * 2.5, 0, 1) })
      e.w *= eyeScale
      e.h *= eyeScale
      e.r *= eyeScale
      e.alpha = clamp(1 - s.swirl * 1.6, 0, 1)
    }
  }
  return { mood: mood, eyes: eyes, tilt: s.tilt, offset: s.offset, swirls: swirls, sleep: s.sleep ? sleepMarks(p) : [] }
}

// The moment that shows each mood best, for reduced motion.
var KEY_POSE = { idle: 0, observing: 0.25, thinking: 0.57, working: 0.137, done: 0.286, failed: 0.37, inactive: 0.12, resting: 0 }
function stillFrame(mood) {
  var info = MOODS[mood] || MOODS.idle
  return frameAt(mood, (KEY_POSE[mood] || 0) * info.cycle)
}

// Interruption acknowledgement: one quick blink, shut at 0.12 s.
function interruptOpenness(seconds) {
  return clamp(blinkCurve(seconds - 0.12, 0.09, 0.14), 0, 1)
}

// Eases eyes from the previous mood's last frame into the new one.
function blend(from, to, u) {
  if (!from || u >= 1) return to
  var k = easeInOut(clamp(u, 0, 1))
  var eyes = []
  for (var i = 0; i < 2; i++) eyes.push(lerpPose(from.eyes[i], to.eyes[i], k))
  return { mood: to.mood, eyes: eyes, tilt: lerp(from.tilt, to.tilt, k), offset: [lerp(from.offset[0], to.offset[0], k), lerp(from.offset[1], to.offset[1], k)], swirls: to.swirls, sleep: to.sleep }
}
