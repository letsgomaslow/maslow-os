# Maslow Free Cloud AI router embedding

This small source adapter and five-file patch embed FreeLLMAPI at **65ec96df6450224a95a0eabfff8b41b394b2396f**. Upstream remains MIT licensed; preserve its LICENSE and attribution in packaged artifacts. This is a private single-user text/function pilot, not a general FreeLLMAPI deployment. Never launch upstream `server/dist/index.js` or `createApp` in the package.

## Build contract

Use a dedicated clean upstream checkout at the pinned revision. The unchanged root `package-lock.json` SHA-256 is `3e6265bd3a3346ca362fd54405e5ed404df72e6a0002cd07d2390dce54463038`.

```bash
/path/to/free_ai/router/apply-upstream.sh /path/to/upstream
cd /path/to/upstream
# PATH must select the package's pinned Node 22.23.3 and its npm.
npm ci --ignore-scripts --no-audit --no-fund --workspace server --workspace shared
npm rebuild better-sqlite3
npm run build -w server
npm run test -w server -- src/__tests__/maslow/boundary.test.ts
MASLOW_ROUTER_ENTRY="$PWD/server/dist/maslow-main.js" node --test /path/to/free_ai/tests/router-bootstrap.test.mjs
```

No dependency or lockfile additions are made. Runtime dependencies come from the existing server workspace lock: Express, zod, better-sqlite3 and the existing upstream provider/router dependency graph. Node native SQLite is used only to inspect the synthetic database in the bootstrap test. `better-sqlite3` must be built for the same Node ABI as the packaged interpreter. Ship the server production dependencies and compiled server output (or a separately tested equivalent bundle), not development dependencies, client, CLI, Electron, desktop update tooling or their entry points. The package must preserve module resolution from `server/dist` to the production dependencies. No installed-package test is implied by source builds.

## Lifecycle contract

The launcher starts the pinned Node with `server/dist/maslow-main.js`. It writes exactly one UTF-8 JSON object to stdin and closes stdin. Maximum bootstrap size is 16 KiB:

```json
{"encryptionKey":"64 hex characters from the credential store","instanceToken":"32–256 URL-safe random characters","groqKey":"gsk_… optional supplied account key","dbPath":"/absolute/private/state/router.sqlite","port":18573}
```

Encryption material and the instance token are required every launch; there is no generated or plaintext fallback. The provider key is optional only when an encrypted account row already exists or the user has not configured a provider. Bootstrap updates one existing Groq key in place so restart/key replacement preserves its ID and quota history. More than one Groq account is refused. Keys never appear in argv, bootstrap output, or persistent plaintext. The parent owns credential-store lock/unlock/revocation and secret transport; the running process necessarily holds usable credentials in memory.

Symlinked ancestors, group/world-writable non-sticky ancestry, hardlinked databases and aliased SQLite sidecars are rejected. A root-owned sticky directory such as `/tmp` is allowed as an ancestor of an owner-private test directory. The existing data directory must be owned by this UID, mode 0700, and not a symlink. An existing database must be a regular owner-only file. New state is created with umask 0077. The daemon binds **127.0.0.1 only**, defaults to port 18573, and fails on occupation without selecting another port. The parent must wait for a ready record before changing client configuration:

```json
{"event":"ready","host":"127.0.0.1","port":18573,"tokenId":"sha256 of instance token"}
```

Stdout contains only that record. Upstream diagnostics are suppressed to avoid accidental prompt/provider-key disclosure. Startup/listen failures emit generic JSON on stderr and exit nonzero. SIGTERM/SIGINT close the listener and database. The only HTTP surface is Bearer-authenticated `POST /v1/chat/completions` and filtered `GET /v1/models`. Requests with Origin, query parameters, other endpoints, unsupported fields, media input, hosted tools or arbitrary endpoints fail closed. Client-executed function definitions, calls and results are supported. The combined serialized message/tool context is capped at 64,000 characters; output is capped at 2048 tokens and defaults to that ceiling. A setup probe can request 128 tokens. `auto` selects only approved routes; profiles, fusion, Responses, Anthropic, MCP, admin and discovery surfaces are absent.

## Independent policy and updates

Software-owned policy permits only Groq `openai/gpt-oss-120b` and `openai/gpt-oss-20b`, with text and client-executed functions. Every actual provider `proxyFetch` dispatch checks request scope, platform, model, live enabled state, text/function body, exact HTTPS endpoint and POST method. It uses direct fetch with redirect rejection, ignoring stored/inherited custom proxies. There are at most two actual provider dispatches per request. A provider 429 sets a persistent account-wide cooldown shared by both models; it honors Retry-After (minimum 60 seconds), or conservatively stops for 24 hours without a usable reset hint. It never rotates to the sibling model to escape that cooldown. This covers retries/fallback and blocks auxiliary/custom/discovery/private-image calls, including the formerly vulnerable Gemini image conversion path. Health-triggered discovery is explicitly removed; no upstream discovery, health, media, backup or self-update scheduler starts.

Only the upstream signed catalog timer starts. Environment overrides are cleared by the entry, and premium license state is removed. The central `applyCatalog` patch filters both verified fetched and cached catalogs. It keeps only approved text tuples, strips media/embeddings/quirks, clamps vision off and context to 131072, and caps metadata estimates at 30 RPM, 1000 RPD, 8000 TPM, 200000 TPD and 6M monthly tokens. Previously reduced limits/context/function support are monotonic and cannot be raised by a later catalog. Lower finite feed limits are retained; post-override enforcement prevents local metadata overrides escaping these caps. Feed enablement cannot override user disables, user tombstones or upstream-retirement tombstones. Signed retirement/removal still takes effect and remains retired even if a later catalog reintroduces the tuple. Local disables also survive disappearance and reappearance. Cached source bytes remain upstream-owned authenticated metadata, but can never expand this software policy. Invalid signatures retain the prior state.

These numbers are conservative router ceilings from the reviewed snapshot, not a provider account entitlement or a billing guarantee. One account is enforced; additional keys never multiply allowances. The parent enrollment flow must require the user's approved free account/no-charge settings. Actual provider availability and account quotas remain external. A catalog update can reduce availability but cannot approve another provider/model/capability. Any widening requires a reviewed Maslow software change.

## Verification boundary

The focused upstream tests execute the actual HTTP router, Groq provider, SSE, missing-model fallback, shared 429 stop, context/output ceilings, Gemini private-image adapter, custom paid-model sync, signed fetched catalog and cached reapply paths with synthetic credentials and mocked network. The compiled bootstrap test runs isolated child processes with outbound fetch disabled, checks auth/loopback/modes, plaintext absence, restart key identity and quota retention. No live provider, real credentials, installed Arch package, real agent workflow or old-hardware claim follows from these checks. Full upstream tests are intentionally not claimed: upstream tests assuming unrestricted providers/admin APIs conflict with this narrower product policy.
