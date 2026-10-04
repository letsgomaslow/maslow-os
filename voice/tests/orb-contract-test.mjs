import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const orb = readFileSync(fileURLToPath(new URL("../ui/VoiceOrb.qml", import.meta.url)), "utf8");
function property(name, values = {}) {
  const expression = orb.match(new RegExp(`readonly property \\w+ ${name}: (.*)`))?.[1];
  assert.ok(expression, `missing ${name}`);
  return vm.runInNewContext(expression, {
    voiceState: "idle", disabled: false, visible: true, reducedMotion: false,
    interactive: false, audioLevel: 0, playbackLevel: 0, stateMode: 0,
    normalizedLevel: 0, normalizedPlayback: 0, phase: 0, reaction: "", ...values
  });
}
for (const [voiceState, expected] of Object.entries({ idle: 0, connecting: 1, listening: 2, conversation: 2, thinking: 3, working: 3, speaking: 4, talking: 4, paused: 5, muted: 5, error: 6 })) {
  assert.equal(property("stateMode", { voiceState }), expected, voiceState);
}
assert.equal(property("stateMode", { voiceState: "listening", disabled: true }), 7);
assert.equal(property("stateMode", { voiceState: "error", disabled: true }), 6);
for (let stateMode = 0; stateMode <= 7; stateMode++) {
  // An error animates only until its fall finishes, then holds still.
  assert.equal(property("moving", { stateMode, moodTime: 0, failedHold: 4.5 }), stateMode < 5 || stateMode === 6);
  assert.equal(property("moving", { stateMode, moodTime: 4.5, failedHold: 4.5 }), stateMode < 5);
  assert.equal(property("moving", { stateMode, reducedMotion: true, moodTime: 0, failedHold: 4.5 }), false);
  assert.equal(property("moving", { stateMode, visible: false, moodTime: 0, failedHold: 4.5 }), false);
}
for (const [values, expected] of [
  [{ stateMode: 0 }, "idle"], [{ stateMode: 1 }, "observing"], [{ stateMode: 2 }, "listening"],
  [{ stateMode: 3, voiceState: "thinking" }, "thinking"], [{ stateMode: 3, voiceState: "working" }, "working"],
  [{ stateMode: 4 }, "speaking"], [{ stateMode: 5 }, "resting"], [{ stateMode: 6 }, "failed"], [{ stateMode: 7 }, "inactive"],
  [{ stateMode: 5, reaction: "completed" }, "done"], [{ stateMode: 2, reaction: "interrupted" }, "listening"],
  [{ stateMode: 2, reaction: "wake" }, "waking"], [{ stateMode: 6, reaction: "wake" }, "failed"], [{ stateMode: 2, reaction: "completed" }, "done"]
]) assert.equal(property("mood", values), expected, JSON.stringify(values));
for (const [level, expected] of [[-1, 0], [0.5, 0.5], [4, 1], [NaN, 0], [Infinity, 0]]) {
  assert.equal(property("normalizedLevel", { audioLevel: level }), expected);
  assert.equal(property("normalizedPlayback", { playbackLevel: level }), expected);
}
assert.equal(property("responseLevel", { stateMode: 2, normalizedLevel: 0.8 }), 0.8);
assert.equal(property("responseLevel", { stateMode: 4, normalizedLevel: 1 }), 0, "Quiet speakers do not animate as speech");
assert.equal(property("responseLevel", { stateMode: 4, normalizedPlayback: 0.4 }), 0.4);
assert.equal(property("responseLevel", { stateMode: 4, normalizedPlayback: 1, reaction: "interrupted" }), 0, "Interruption immediately stops output movement");
for (const stateMode of [2, 4]) assert.equal(property("responseLevel", { stateMode, normalizedLevel: 1, normalizedPlayback: 1, reducedMotion: true }), 0);
const shader = readFileSync(fileURLToPath(new URL("../ui/VoiceOrb.frag", import.meta.url)), "utf8");
assert.match(shader, /float phase;/);
for (const name of ["topColor", "accentColor", "bottomColor"]) {
  assert.match(shader, new RegExp(`vec4 ${name};`));
  assert.match(orb, new RegExp(`property color ${name}: root\\.${name}`));
}
assert.match(orb, /onTopColorChanged\(\).*requestPaint/);
const contrast = orb.match(/function contrastInk\(color\) \{([\s\S]*?)\n  \}/)?.[1];
assert.ok(contrast);
const ink = vm.runInNewContext(`(function(color) { ${contrast} })`);
for (const [color, expected] of [
  [{r: 1, g: 1, b: 1}, "#000000"],
  [{r: 0, g: 0, b: 0}, "#FFFFFF"],
  [{r: 1, g: 0.82, b: 0.18}, "#000000"],
  [{r: 0.12, g: 0.18, b: 0.4}, "#FFFFFF"],
  [{r: 0.43, g: 0.77, b: 0.68}, "#000000"]
]) assert.equal(ink(color), expected, "Face ink adapts to bright and dark theme accents");
assert.match(orb, /property real phase: root.reducedMotion \? 0 : root.phase/);
assert.match(orb, /GraphicsInfo\.Software/);
assert.match(orb, /clip: true/);
assert.match(orb, /onInterruptionSequenceChanged/);
assert.match(orb, /onCompletionSequenceChanged/);
assert.match(orb, /root.reactionTime >=/);
assert.match(orb, /import "OrbFrame.js" as OrbFrame/);
// Motion follows real frame time at the display's rate, not a 25 fps timer.
assert.equal((orb.match(/FrameAnimation \{/g) || []).length, 3);
assert.doesNotMatch(orb, /interval: 40/);
assert.match(orb, /root\.phase \+= Math\.min\(frameTime, 0\.1\)/);
assert.match(orb, /Behavior on xScale \{ enabled: !root\.reducedMotion; SmoothedAnimation/);
// A conversation starting from ready or setup wakes once; reduced motion never does.
// The state at creation is recorded, so the first conversation after loading wakes.
assert.match(orb, /Component\.onCompleted: \{[^}]*previousStateMode = stateMode/);
const wake = orb.match(/onStateModeChanged: \{([\s\S]*?)\n  \}/)?.[1];
assert.ok(wake);
for (const [previousStateMode, stateMode, reducedMotion, expected] of [[0, 2, false, true], [7, 1, false, true], [0, 1, true, false], [-1, 2, false, false], [4, 2, false, false], [5, 2, false, false]]) {
  let woke = false;
  const scope = { previousStateMode, stateMode, reducedMotion, react: kind => { woke = kind === "wake"; } };
  vm.runInNewContext(wake, scope);
  assert.equal(woke, expected, `wake from ${previousStateMode} to ${stateMode}`);
  assert.equal(scope.previousStateMode, stateMode);
}

const paint = orb.match(/onPaint: \{([\s\S]*?)\n      \}\n    \}\n    Loader/)?.[1];
assert.ok(paint);
for (const size of [56, 88]) for (let stateMode = 0; stateMode <= 7; stateMode++) for (const phase of [0, 1.5, 10000]) {
  let stack = 0;
  let points = 0;
  const ctx = new Proxy({}, { get: (_target, operation) => (...args) => {
    for (const value of args) if (typeof value === "number") assert.ok(Number.isFinite(value));
    if (operation === "save") stack++;
    if (operation === "restore") assert.ok(--stack >= 0);
    if (operation === "lineTo" || operation === "moveTo") {
      points++;
      assert.ok(Math.hypot(...args) < 0.86, "Fluid silhouette stays inside its allocation");
    }
    if (operation === "createRadialGradient" || operation === "createLinearGradient") return { addColorStop(position, color) { assert.ok(position >= 0 && position <= 1); assert.match(color, /^(#|rgba\()/); } };
  }});
  vm.runInNewContext(paint, {getContext: () => ctx, width: size, height: size, root: {phase, stateMode, reducedMotion: false, topColor: "#C0E8DC", accentColor: "#6DC4AD", bottomColor: "#478071"}});
  assert.equal(stack, 0);
  assert.equal(points, 97);
}
console.log("PASS: Fluid character states, input/playback separation, interruption, reduced motion and contained fallback geometry");
