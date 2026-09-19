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
    interactive: false, audioLevel: 0, stateMode: 0, normalizedLevel: 0, phase: 0, ...values
  });
}

for (const [voiceState, expected] of Object.entries({ idle: 0, connecting: 1, listening: 2, conversation: 2, thinking: 3, working: 3, speaking: 4, talking: 4, muted: 5, error: 6 })) {
  assert.equal(property("stateMode", { voiceState }), expected, voiceState);
}
assert.equal(property("stateMode", { voiceState: "listening", disabled: true }), 7);
assert.equal(property("stateMode", { voiceState: "error", disabled: true }), 6, "errors stay visible when readiness is disabled");
for (const stateMode of [0, 1, 2, 3, 4]) {
  assert.equal(property("moving", { stateMode }), true);
  for (const constraint of [{ reducedMotion: true }, { visible: false }]) {
    assert.equal(property("moving", { stateMode, ...constraint }), false);
  }
  assert.equal(property("moving", { stateMode, interactive: true }), true, "focus must not freeze state animation");
}
for (const stateMode of [5, 6, 7]) assert.equal(property("moving", { stateMode }), false);
for (const [audioLevel, expected] of [[-1, 0], [0.5, 0.5], [4, 1], [NaN, 0], [Infinity, 0]]) {
  assert.equal(property("normalizedLevel", { audioLevel }), expected);
}
assert.equal(property("responseLevel", { stateMode: 2, normalizedLevel: 0.8 }), 0.8);
const speakingLevel = property("responseLevel", { stateMode: 4, normalizedLevel: 0 });
assert.ok(speakingLevel > 0, "speaking animates without microphone input");
assert.equal(property("responseLevel", { stateMode: 4, normalizedLevel: 1 }), speakingLevel, "speaking never visualizes microphone amplitude");
assert.notEqual(property("responseLevel", { stateMode: 4, phase: 0.5 }), speakingLevel);
for (const stateMode of [2, 4]) {
  assert.equal(property("responseLevel", { stateMode, normalizedLevel: 0.8, reducedMotion: true }), 0);
}
for (const stateMode of [0, 1, 3, 5, 6, 7]) assert.equal(property("responseLevel", { stateMode, normalizedLevel: 0.8 }), 0);
const shader = readFileSync(fileURLToPath(new URL("../ui/VoiceOrb.frag", import.meta.url)), "utf8");
for (const uniform of ["level", "phase", "stateMode"]) {
  assert.match(orb, new RegExp(`property real ${uniform}: root\\.`));
  assert.match(shader, new RegExp(`float ${uniform};`));
}
assert.match(orb, /GraphicsInfo\.Software/);
assert.match(orb, /createRadialGradient/);
assert.match(orb, /border\.width: root\.interactive \? 2 : 0/);
console.log("PASS: Orb states, finite audio levels, motion constraints and shader interface");
