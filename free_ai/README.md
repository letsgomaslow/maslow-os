# Free cloud AI integration

This is the source candidate for an optional everyday assistant, not a verified or published preview. Track acceptance in [the separate program](../docs/programs/free-cloud-ai/README.md). It uses the person's Groq account through a private headless FreeLLMAPI adapter; the existing Voice task service owns its lifetime. Ordinary agents and speech-provider settings remain separate.

## Ownership and entry points

- `router/` contains the small pinned upstream embedding patch and supported bootstrap contract.
- `maslow_free_ai/` contains the package-owned control, private settings, Secret Service encryption-key client and owned router lifecycle.
- `bin/omarchy-free-ai` is carried by the optional package, not by the base runtime. It uses fixed commands and a masked terminal for account input.
- `../voice/maslow_voice/assistant*.py`, `../voice/assistant_worker.py` and `../voice/assistant_plugin/` are carried by the separately updated Voice package. The package must include all three; an old Voice package is not task-ready.

The router has no login unit. Status does not start inference or read account keys. Setup and explicit connection checks start it temporarily; an admitted managed task holds it until its Hermes process has been cleaned up, then a five-second grace period closes it. Closing Hub or ending audio leaves task execution intact. Process ownership comes from directly spawned process groups and parent-death handling, never a matching health response or an unrelated PID. An occupied fixed port fails safely.

## Task-service contract

The private Voice control socket adds `task_submit` independently of `submit_text`. It starts no conversation, microphone or speech-provider connection:

```json
{"action":"task_submit","request_id":"unique-request","text":"Draft an invitation","project":"/absolute/chosen/workspace","execution_connection":"free-cloud","capabilities":{"documents":["agenda.md"],"note":"invitation.md","accounts":[]}}
```

`execution_connection` is `existing` or `free-cloud`. Changing the setting affects new requests. Existing execution continues with its persisted identity and grants. A free-cloud task persists the original text, canonical workspace and its inode identity, selected-file identities, explicit new-note path, policy revision and connection. Reusing the ID with changed text, workspace, mode, policy or requested permissions raises `REQUEST_CONFLICT`; repeated submission after a note was saved returns the original task. A continuation uses a new attempt under the same grants. It cannot add accounts/files or change the destination.

The typed Work composer is the explicit grant surface. A note path is permission only when the user selects the save checkbox. Spoken intents reuse the managed connection after existing intent validation, with no ambient file/account/save grants. For selected-document or save work, choose the scope in Work. Only one managed request can be active or cleaning up. Quota cooldown pauses the same task with Stop/Continue controls; it never changes provider. Restart marks managed work interrupted rather than replaying it.

The managed Hermes process uses a private home, profile, empty skills/bundled-plugin roots and one reviewed plugin. It disables memory, project context, general terminal/file/browser/coding tools, inherited MCP, tool discovery and fallback configuration. The compatibility wrapper checks the actual agent tool names after construction: exactly `maslow_list_documents`, `maslow_read_document`, `maslow_create_note`. Unsupported Hermes changes fail closed. The daemon resolves tool requests by out-of-band task session identity and its private bridge token.

Documents are bounded UTF-8 `.md`/`.txt` files opened by descriptor without symlink traversal; hard links and changed file/workspace identities are denied. Creation is restricted to the explicitly granted new `.md` path, uses exclusive creation, fsyncs and checks bytes before returning path, byte size and SHA-256. A persisted reservation prevents changed-content retries or overwrites. An incomplete crash result requires review. Connected accounts remain unavailable until the accepted Connect package and exact-account read/revocation contract are verified; the ordinary agents' relay is never inherited.

## Setup and privacy

The fixed masked setup flow opens instructions for [Groq account keys](https://console.groq.com/keys), asks the person to confirm Free with no billing upgrade, and asks consent for up to two harmless function requests. Authentication/tool success verifies connection behavior, not billing. The recorded confirmation is `user-confirmed`; upgrading requires a payment method according to [Groq's billing documentation](https://console.groq.com/docs/billing-faqs). The guide tells people to stay on Free and avoid adding billing. Selected text is sent to Groq; it is not offline inference. Existing Voice speech connections keep their separate account and privacy terms.

Review [Groq's data controls](https://console.groq.com/docs/your-data) before using private documents or accounts. Its current documentation permits temporary input/output retention for reliability or abuse investigation, normally up to 30 days unless legally required longer, and offers Zero Data Retention in the organization's Data Controls. Maslow does not independently verify that setting. This documentation was checked on 2026-10-11; a successful connection test does not establish a privacy setting.

One encrypted provider-account row is retained in upstream SQLite. Its encryption material lives only in Secret Service; a locked/unavailable/missing matching key fails closed. Setup credentials cross a private owner-only UNIX socket only after checking the peer PID against the managed Voice systemd service. Provider keys appear neither in argv nor agent configuration, task records, status, Hub state or logs. API responses and provider quotas remain external facts; checked note bytes do not verify model-generated factual statements.

Installation/update/recovery actions remain disabled until the fixed signed delivery and consistent database/key/package restoration gates pass. No production signing, package publication, installed host replacement or product merge is implied by the candidate source.

## Verification

Use the pinned Voice interpreter for `bash test/shell.d/voice-test.sh`. Additional checks:

```bash
PYTHONPATH=free_ai PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s free_ai/tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python free_ai/tests/hermes_profile_probe.py
node voice/tests/ui-controller-test.mjs
node voice/tests/ui-work-composer-test.mjs
python docs/programs/free-cloud-ai/manage.py validate
```

The Hermes probe constructs the actual installed agent without inference and records its tool/context/memory flags. Router regression/build instructions are in [the embedding README](router/README.md). Source tests, synthetic provider fixtures, compiled package tests, live Groq, real Secret Service, connected accounts, guest, Lenovo timing and heard speech are separate evidence. Read the candidate manifest before treating any capability as accepted.
