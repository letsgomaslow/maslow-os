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
  assistantAccounts: [], assistantSelectedAccounts: [], assistantAccountsAvailable: false,
  assistantAccountsLoading: false, assistantAccountsLoaded: false, assistantAccountsRequestId: "", assistantAccountsError: "",
  assistantAccountConsent: false,
  freeCloudSelected: true, feedback: "", voiceStartPending: false, livekitSetupSaving: false,
  geminiLiveSetupSaving: false, send: (action, payload) => requests.push({ action, ...payload }),
};
runInNewContext(["submitAssistant", "handleTransportError", "refreshAssistantAccounts", "selectAssistantAccount", "handleAssistantAccounts", "handleControlResponse"].map(extract).join("\n"), context);
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

// Correlated read-only discovery grants nothing and leaves plain requests usable.
context.handleTransportError("Connection lost.");
context.freeCloudSelected = true;
context.settings.execution_connection = "free-cloud";
context.refreshAssistantAccounts();
const discoveryId = context.assistantAccountsRequestId;
assert.equal(requests.at(-1).action, "assistant_accounts");
assert.equal(requests.at(-1).account_request_id, discoveryId);
assert.equal(requests.at(-1).capabilities, undefined);
context.refreshAssistantAccounts();
assert.equal(requests.filter(request => request.action === "assistant_accounts").length, 1, "single refresh in flight");
context.submitAssistant();
assert.equal(requests.at(-1).action, "task_submit", "plain ask/save works while discovery loads");
const plainId = context.assistantRequestId;
context.handleControlResponse({ ok: false, assistant_accounts_reply: true, account_request_id: "stale", error: { message: "late" } });
assert.equal(context.assistantAccountsLoading, true);
assert.equal(context.assistantSubmitting, true);
context.handleControlResponse({ ok: false, assistant_accounts_reply: true, account_request_id: discoveryId, error: { message: "private marker" } });
assert.equal(context.assistantAccountsLoading, false);
assert.equal(context.assistantSubmitting, true, "account errors never cancel pending task submission");
assert.equal(context.assistantRequestId, plainId);
assert.equal(context.assistantDraft, "Draft a summary");
assert.doesNotMatch(context.assistantAccountsError, /private marker/);
context.handleTransportError("Connection lost.");
context.refreshAssistantAccounts();
const accounts = [{ id: "b", label: "Personal Calendar" }, { id: "a", label: "Work Calendar" }, { id: "c", label: "Family Calendar" }, { id: "d", label: "Study Calendar" }, { id: "e", label: "Other Calendar" }];
context.handleControlResponse({ ok: true, assistant_accounts_reply: true, account_request_id: context.assistantAccountsRequestId, available: true, accounts });
assert.deepEqual(Array.from(context.assistantSelectedAccounts), [], "discovery never selects an account");
for (const identity of ["b", "a", "c", "d", "e"]) context.selectAssistantAccount(identity, true);
assert.deepEqual(Array.from(context.assistantSelectedAccounts), ["a", "b", "c", "d"], "four stable sorted account IDs maximum");
const beforeNoConsent = requests.length;
context.submitAssistant();
assert.equal(requests.length, beforeNoConsent, "selecting is not permission to send account data");
context.assistantAccountConsent = true;
context.submitAssistant();
const selectedRequest = requests.at(-1);
assert.deepEqual(Array.from(selectedRequest.capabilities.accounts), ["a", "b", "c", "d"]);
assert.equal(selectedRequest.capabilities.send_to_groq_confirmed, true);
const selectedId = selectedRequest.request_id;
assert.notEqual(selectedId, plainId, "account grants alter idempotency fingerprint");
context.handleTransportError("Connection lost.");
context.submitAssistant();
assert.equal(requests.at(-1).request_id, selectedId, "unchanged account/consent retry preserves request identity");
context.handleTransportError("Connection lost.");
context.selectAssistantAccount("b", false);
assert.equal(context.assistantAccountConsent, false, "selection changes require fresh privacy consent");
context.assistantAccountConsent = true;
context.submitAssistant();
assert.notEqual(requests.at(-1).request_id, selectedId, "changed selected IDs have a new request identity");
context.handleTransportError("Connection lost.");
context.refreshAssistantAccounts();
context.handleControlResponse({ ok: true, assistant_accounts_reply: true, account_request_id: context.assistantAccountsRequestId, available: true, accounts: [accounts[2]] });
assert.deepEqual(Array.from(context.assistantSelectedAccounts), ["c"], "refresh removes stale selections without granting a replacement");
assert.equal(context.assistantAccountConsent, false);
context.refreshAssistantAccounts();
context.handleControlResponse({ ok: true, assistant_accounts_reply: true, account_request_id: context.assistantAccountsRequestId, available: false, accounts: [] });
assert.deepEqual(Array.from(context.assistantSelectedAccounts), []);
assert.equal(context.assistantAccountsAvailable, false);
context.submitAssistant();
assert.equal(requests.at(-1).capabilities.send_to_groq_confirmed, undefined, "empty account selection carries no account consent field");
const completedId = context.assistantRequestId;
const completedDraft = context.assistantDraft;
context.handleControlResponse({ ok: true, assistant_accounts_reply: true, account_request_id: "late", available: false, accounts: [] });
assert.equal(context.assistantRequestId, completedId, "account discovery cannot consume task request identity");
assert.equal(context.assistantDraft, completedDraft);
context.handleControlResponse({ ok: true, submitted_request_id: "unrelated-task" });
assert.equal(context.assistantRequestId, completedId, "only the matching acknowledgment ends a request");
context.handleControlResponse({ ok: true, submitted_request_id: completedId });
assert.equal(context.assistantDraft, "");
assert.equal(context.assistantRequestId, "");
assert.equal(context.assistantRequestFingerprint, "");
context.assistantDraft = completedDraft;
context.submitAssistant();
assert.notEqual(context.assistantRequestId, completedId, "accepted then retyped identical request/grants create a fresh task identity");
context.handleTransportError("Connection lost.");
context.refreshAssistantAccounts();
const retainedDraft = context.assistantDraft;
context.handleControlResponse({ ok: true, assistant_accounts_reply: true, account_request_id: context.assistantAccountsRequestId, available: true,
  accounts: [{ id: "__proto__", label: "One Calendar" }, { id: "__proto__", label: "Other Calendar" }] });
assert.equal(context.assistantAccountsAvailable, false, "duplicate IDs cannot escape validation through prototype property names");
assert.equal(context.assistantDraft, retainedDraft, "malformed account data preserves the request");
context.refreshAssistantAccounts();
context.handleControlResponse({ ok: true, assistant_accounts_reply: true, account_request_id: context.assistantAccountsRequestId, available: true,
  accounts: [{ id: "valid", label: "Calendar\nInjected line" }] });
assert.equal(context.assistantAccountsAvailable, false, "control characters are not rendered as account labels");
assert.equal(requests.every(request => ["task_submit", "assistant_accounts"].includes(request.action)), true, "accounts/composer never start speech or microphones");
assert.match(source, /Send information from these selected accounts to Groq/);
assert.match(source, /Private results stay in Work; Voice reports when ready/);
assert.match(source, /text: modelData.label/);
assert.doesNotMatch(source, /text: modelData.id/);
assert.match(source, /id: tasksScroll\s+contentWidth: availableWidth/);
console.log("Work composer protocol and transport recovery passed.");
