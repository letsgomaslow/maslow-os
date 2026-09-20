import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { resolve } from "node:path";

const source = readFileSync(resolve(import.meta.dirname, "../ui/VoiceController.qml"), "utf8");

function qmlFunction(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `missing ${name}`);
  const opening = source.indexOf("{", start);
  let depth = 0;
  for (let index = opening; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") depth -= 1;
    if (depth === 0) return source.slice(start, index + 1);
  }
  throw new Error(`unterminated ${name}`);
}

const context = {};
runInNewContext([
  qmlFunction("semanticEqual"),
  qmlFunction("reuseUnchanged"),
  qmlFunction("reconcileTasks"),
  qmlFunction("visibleTaskList"),
  qmlFunction("applySnapshot"),
].join("\n"), context);

context.voice = { enabled: false, state: "disabled" };
context.settings = {};
context.tasks = [];
context.visibleTasks = [];
context.session = { id: "", transcript: [] };
context.readiness = { ready: false, checks: [] };
context.taskViewRequest = null;
context.snapshot = {};
context.applySnapshot({
  schemaVersion: 1,
  voice: context.voice,
  settings: context.settings,
  tasks: [],
  session: context.session,
  readiness: context.readiness,
  task_view_request: { task_id: "codex-task", sequence: 4 },
});
assert.deepEqual(context.taskViewRequest, { task_id: "codex-task", sequence: 4 }, "task view requests survive controller snapshot reconciliation");
const firstTaskViewRequest = context.taskViewRequest;
context.applySnapshot({
  schemaVersion: 1,
  voice: context.voice,
  settings: context.settings,
  tasks: [],
  session: context.session,
  readiness: context.readiness,
  task_view_request: { task_id: "codex-task", sequence: 4 },
});
assert.strictEqual(context.taskViewRequest, firstTaskViewRequest, "unchanged view requests do not retrigger the panel");

const prior = [
  {
    id: "approval",
    updated_at: 10,
    state: "awaiting_approval",
    approval: { request_id: "one", detail: "Review the first version" },
    result: "",
    children: [{ id: "child", result: "waiting" }],
  },
  { id: "complete", updated_at: 10, state: "completed", result: "Ready", children: [] },
];
const equalIncoming = structuredClone(prior);
assert.strictEqual(context.reconcileTasks(prior, equalIncoming), prior, "level-only snapshots retain the whole task model");
assert.strictEqual(context.reconcileTasks(prior, equalIncoming)[0], prior[0], "unchanged task identity is retained");

const changedApproval = structuredClone(prior);
changedApproval[0].approval.detail = "Review the corrected version";
const approvalReconciled = context.reconcileTasks(prior, changedApproval);
assert.notStrictEqual(approvalReconciled, prior, "approval content changes replace the task model");
assert.notStrictEqual(approvalReconciled[0], prior[0], "approval changes propagate even with an unchanged timestamp");
assert.strictEqual(approvalReconciled[1], prior[1], "unrelated task identity is retained");

const changedResult = structuredClone(prior);
changedResult[0].result = "Task result changed without a timestamp change.";
assert.notStrictEqual(context.reconcileTasks(prior, changedResult)[0], prior[0], "task results propagate");

const changedChild = structuredClone(prior);
changedChild[0].children[0].result = "completed";
assert.notStrictEqual(context.reconcileTasks(prior, changedChild)[0], prior[0], "nested child results propagate");

const reordered = structuredClone(prior).reverse();
const reorderedTasks = context.reconcileTasks(prior, reordered);
assert.notStrictEqual(reorderedTasks, prior, "task order changes propagate");
assert.strictEqual(reorderedTasks[0], prior[1], "reordered unchanged task retains its object identity");
const dismissed = structuredClone(prior);
dismissed[0].dismissed = true;
const dismissedTasks = context.reconcileTasks(prior, dismissed);
assert.notStrictEqual(dismissedTasks[0], prior[0], "dismissal changes propagate");
const visibleDismissedTasks = context.visibleTaskList(dismissedTasks);
assert.equal(visibleDismissedTasks.length, 1, "dismissed tasks stay out of the visible model");
assert.strictEqual(visibleDismissedTasks[0], dismissedTasks[1]);

const changedSession = { id: "session", transcript: [{ role: "user", text: "first", partial: true }] };
assert.strictEqual(context.reuseUnchanged(changedSession, structuredClone(changedSession)), changedSession);
assert.notStrictEqual(context.reuseUnchanged(changedSession, { id: "session", transcript: [{ role: "user", text: "second", partial: true }] }), changedSession, "partial transcript text changes propagate");
