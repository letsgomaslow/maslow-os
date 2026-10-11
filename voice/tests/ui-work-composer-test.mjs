import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const source = readFileSync(new URL("../ui/Panel.qml", import.meta.url), "utf8");
function extract(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `missing ${name}`);
  let depth = 0;
  const opening = source.indexOf("{", start);
  for (let end = opening; end < source.length; end++) {
    if (source[end] === "{") depth++;
    if (source[end] === "}" && --depth === 0) return source.slice(start, end + 1);
  }
  throw new Error(`unterminated ${name}`);
}
const requests = [];
const context = {
  assistantSubmitting: false, assistantDraft: "Draft a summary", selectedProject: "/fixture",
  assistantDocuments: " a.md\n\nb.txt \n", assistantNote: " summary.md ", assistantSaveNote: false,
  assistantRequestFingerprint: "", assistantRequestId: "", settings: { execution_connection: "free-cloud" },
  freeCloudSelected: true, feedback: "", voiceStartPending: false, livekitSetupSaving: false,
  geminiLiveSetupSaving: false, send: (action, payload) => requests.push({ action, ...payload }),
};
runInNewContext([extract("submitAssistant"), extract("handleTransportError")].join("\n"), context);
context.submitAssistant();
context.submitAssistant();
assert.equal(requests.length, 1, "pending double submission is suppressed");
assert.equal(requests[0].action, "task_submit");
assert.deepEqual(Array.from(requests[0].capabilities.documents), ["a.md", "b.txt"]);
assert.equal(requests[0].capabilities.note, null, "a filled note field grants nothing without checkbox consent");
const originalId = context.assistantRequestId;
context.handleTransportError("Connection lost.");
assert.equal(context.assistantSubmitting, false);
assert.equal(context.assistantDraft, "Draft a summary");
assert.equal(context.assistantDocuments, " a.md\n\nb.txt \n");
assert.equal(context.assistantRequestId, originalId);
assert.match(context.feedback, /Retry this request/);
context.submitAssistant();
assert.equal(requests[1].request_id, originalId, "retry preserves idempotency identity");
context.handleTransportError("Connection lost.");
context.assistantSaveNote = true;
context.submitAssistant();
assert.equal(requests[2].capabilities.note, "summary.md");
assert.notEqual(requests[2].request_id, originalId, "changed grants get a new identity");
context.handleTransportError("Connection lost.");
context.freeCloudSelected = false;
context.settings.execution_connection = "existing";
context.submitAssistant();
assert.deepEqual(Object.keys(requests[3].capabilities), []);
assert.equal(requests.every(request => request.action === "task_submit"), true, "composer never starts the microphone");
console.log("Work composer protocol and transport recovery passed.");
