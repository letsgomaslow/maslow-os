import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

// OrbFrame.js is a QML library; drop its pragma and evaluate it as a script.
const source = readFileSync(fileURLToPath(new URL("../ui/OrbFrame.js", import.meta.url)), "utf8").replace(/^\.pragma library\n/, "");
const frame = vm.runInNewContext(`${source}\n({ frameAt, stillFrame, blend, loopLength, swirlPoints, interruptOpenness, MOODS, CENTER, BODY_RADIUS, MOUTH_Y, FAILED_HOLD, DONE_END })`);
const moods = ["idle", "observing", "thinking", "working", "done", "failed", "inactive", "resting"];
const close = (a, b, message) => assert.ok(Math.abs(a - b) < 1e-6, `${message}: ${a} != ${b}`);

function assertContained(f, label) {
  for (const value of [f.tilt, ...f.offset]) assert.ok(Number.isFinite(value), label);
  for (const eye of f.eyes) {
    for (const value of Object.values(eye)) assert.ok(Number.isFinite(value), label);
    assert.ok(eye.w >= 0 && eye.h >= 0 && eye.r >= 0 && eye.alpha >= 0 && eye.alpha <= 1, label);
    // Every eye corner stays inside the body, whose silhouette never drops below radius 26.
    const reach = Math.hypot(Math.abs(eye.cx - frame.CENTER) + eye.w / 2, Math.abs(eye.cy - frame.CENTER) + eye.h / 2);
    assert.ok(reach + Math.hypot(...f.offset) < 26, `${label} eye reaches ${reach.toFixed(2)}`);
  }
  for (const swirl of f.swirls) for (const [x, y] of frame.swirlPoints(swirl)) assert.ok(Math.hypot(x - frame.CENTER, y - frame.CENTER) < 26, label);
  for (const mark of f.sleep) assert.ok(Math.hypot(mark.x - frame.CENTER, mark.y - frame.CENTER) + mark.size < 26, label);
}

for (const mood of moods) {
  const length = frame.loopLength(mood);
  for (let t = 0; t <= length * 1.5; t += 0.01) assertContained(frame.frameAt(mood, t), `${mood} at ${t.toFixed(2)}`);
  assertContained(frame.stillFrame(mood), `${mood} still`);
  assert.equal(frame.frameAt(mood, 0).mood, mood);
}

// Looping moods are seamless; one-shot moods hold their end.
for (const mood of ["idle", "observing", "thinking", "working", "inactive"]) {
  const length = frame.loopLength(mood);
  for (const t of [0, 0.7, 2.3]) {
    const a = frame.frameAt(mood, t), b = frame.frameAt(mood, t + length);
    a.eyes.forEach((eye, index) => close(eye.cy, b.eyes[index].cy, `${mood} loop`));
  }
}
const doneEnd = frame.DONE_END * frame.MOODS.done.cycle;
const failedEnd = frame.FAILED_HOLD * frame.MOODS.failed.cycle;
assert.deepEqual(frame.frameAt("done", doneEnd + 5), frame.frameAt("done", doneEnd));
assert.deepEqual(frame.frameAt("failed", failedEnd + 5), frame.frameAt("failed", failedEnd));

// Done finishes at rest so returning to idle is continuous.
const doneLast = frame.frameAt("done", doneEnd), idleFirst = frame.frameAt("idle", 0);
doneLast.eyes.forEach((eye, index) => { close(eye.cx, idleFirst.eyes[index].cx, "done ends at rest"); close(eye.cy, idleFirst.eyes[index].cy, "done ends at rest"); });
close(doneLast.tilt, 0, "done ends level");

// A held error shows fallen, flattened eyes without lingering swirls.
const fallen = frame.frameAt("failed", failedEnd);
assert.equal(fallen.swirls.length, 0);
assert.ok(fallen.eyes[0].cy > idleFirst.eyes[0].cy + 5 && fallen.eyes[0].h < idleFirst.eyes[0].h * 0.7);
assert.ok(frame.frameAt("failed", 0.6 * frame.MOODS.failed.cycle).swirls.length === 2, "the fall goes dizzy");

// Expressions that define each mood.
const thinking = frame.stillFrame("thinking");
close(thinking.eyes[0].cx, thinking.eyes[1].cx, "thinking merges the eyes");
assert.ok(frame.stillFrame("done").eyes[0].h < 4, "done squints");
assert.equal(frame.stillFrame("inactive").sleep.length, 3, "asleep shows z marks");
assert.equal(frame.stillFrame("resting").sleep.length, 0, "paused is not asleep");
assert.ok(frame.stillFrame("resting").eyes[0].h < idleFirst.eyes[0].h * 0.5, "paused eyes are half shut");

// Idle blinks twice per cycle and its gaze moves.
const idleOpen = Array.from({ length: 551 }, (_, index) => frame.frameAt("idle", index / 100).eyes[0].h);
assert.ok(Math.min(...idleOpen) < 2, "idle blinks");
assert.ok(new Set(Array.from({ length: 50 }, (_, index) => frame.frameAt("idle", index / 10).eyes[0].cx.toFixed(2))).size > 10, "idle glances");

// Blends start at the previous frame and finish at the target.
const from = frame.frameAt("thinking", 3), to = frame.frameAt("idle", 0);
assert.deepEqual(frame.blend(from, to, 0).eyes, from.eyes);
assert.deepEqual(frame.blend(from, to, 1), to);
assert.deepEqual(frame.blend(null, to, 0), to);

// Interruption is one quick blink.
assert.equal(frame.interruptOpenness(0), 1);
assert.ok(frame.interruptOpenness(0.12) < 0.01);
assert.equal(frame.interruptOpenness(0.4), 1);

console.log("PASS: Orb moods stay inside the body, loop seamlessly, hold one-shot ends and blend between moods");
