import { AsyncLocalStorage } from 'node:async_hooks';
import { parseBudget } from '../lib/budget.js';
import type { Db } from '../db/types.js';

// Software-owned policy. The signed upstream catalog is metadata, never authority.
export const MODELS = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b'] as const;
export const GROQ_CHAT_URL = 'https://api.groq.com/openai/v1/chat/completions';
let policyDb: Db | undefined;
export const inferenceScope = new AsyncLocalStorage<{ attempts: number }>();
export function approved(platform: string, model: string): boolean {
  return platform === 'groq' && (MODELS as readonly string[]).includes(model);
}
export function assertTextRequest(body: any, allowAuto = false): void {
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('Invalid request');
  if (!(allowAuto && body.model === 'auto') && !approved('groq', body.model)) throw new Error('Model denied by Maslow policy');
  const allowed = new Set(['model', 'messages', 'stream', 'stream_options', 'temperature', 'top_p', 'max_tokens', 'max_completion_tokens', 'stop', 'seed', 'presence_penalty', 'frequency_penalty', 'tools', 'tool_choice', 'parallel_tool_calls', 'response_format', 'reasoning_effort']);
  if (Object.keys(body).some(k => !allowed.has(k))) throw new Error('Unsupported request field');
  if (JSON.stringify([body.messages, body.tools ?? []]).length > 64000) throw new Error('Request context exceeds 64000 characters');
  for (const field of ['max_tokens', 'max_completion_tokens']) {
    if (body[field] !== undefined && (!Number.isInteger(body[field]) || body[field] < 1 || body[field] > 2048)) throw new Error('Output limit exceeds policy');
  }
  if (!Array.isArray(body.messages) || !body.messages.length) throw new Error('Messages required');
  for (const m of body.messages) {
    if (!m || !['system', 'user', 'assistant', 'tool'].includes(m.role)) throw new Error('Unsupported message');
    if (Object.keys(m).some(k => !['role', 'content', 'name', 'tool_calls', 'tool_call_id', 'reasoning_content'].includes(k))) throw new Error('Unsupported message field');
    if (m.content !== null && typeof m.content !== 'string' && !(Array.isArray(m.content) && m.content.every((p: any) => p && p.type === 'text' && typeof p.text === 'string' && Object.keys(p).every(k => ['type', 'text'].includes(k))))) throw new Error('Only text content is allowed');
    if (m.tool_calls !== undefined && (!Array.isArray(m.tool_calls) || m.tool_calls.some((t: any) => !t || t.type !== 'function' || typeof t.function?.name !== 'string' || typeof t.function?.arguments !== 'string'))) throw new Error('Only function calls are allowed');
  }
  if (body.tools !== undefined && (!Array.isArray(body.tools) || body.tools.some((t: any) => !t || t.type !== 'function' || typeof t.function?.name !== 'string' || Object.keys(t).some(k => !['type', 'function'].includes(k))))) throw new Error('Only client-executed function tools are allowed');
  if (body.tool_choice && typeof body.tool_choice === 'object' && body.tool_choice.type !== 'function') throw new Error('Only function tool choice is allowed');
}
export function assertDispatch(url: string, init: RequestInit | undefined, platform: string | undefined): void {
  if (!inferenceScope.getStore() || platform !== 'groq' || url !== GROQ_CHAT_URL || init?.method !== 'POST' || typeof init.body !== 'string') throw new Error('Dispatch denied by Maslow policy');
  const body = JSON.parse(init.body);
  assertTextRequest(body);
  const model = policyDb?.prepare("SELECT enabled,supports_tools FROM models WHERE platform='groq' AND model_id=?").get(body.model) as { enabled: number; supports_tools: number } | undefined;
  if (!model?.enabled) throw new Error('Model disabled by Maslow policy');
  if (body.tools?.length && !model.supports_tools) throw new Error('Functions disabled by catalog');
  const until = Number((policyDb?.prepare("SELECT value FROM settings WHERE key='maslow_groq_cooldown_until'").get() as { value: string } | undefined)?.value ?? 0);
  if (until > Date.now()) throw Object.assign(new Error('Groq account cooldown'), { status: 429, retryAfterMs: until-Date.now() });
  if (body.max_tokens === undefined && body.max_completion_tokens === undefined) throw new Error('Explicit bounded output required');
  const scope = inferenceScope.getStore()!;
  if (++scope.attempts > 2) throw new Error('Maslow dispatch attempt limit');
}
export function observeAccountCooldown(response: Response): void {
  if (response.status !== 429 || !policyDb) return;
  const raw = response.headers.get('retry-after');
  const parsed = raw && /^\d+(?:\.\d+)?$/.test(raw) ? Date.now() + Number(raw)*1000 : Date.parse(raw ?? '');
  // No supplied reset time: stop for the day rather than cycling sibling models.
  const until = Math.max(Date.now()+60000, Number.isFinite(parsed) ? parsed : Date.now()+86400000);
  policyDb.prepare("INSERT INTO settings(key,value) VALUES('maslow_groq_cooldown_until',?) ON CONFLICT(key) DO UPDATE SET value=MAX(CAST(value AS INTEGER),CAST(excluded.value AS INTEGER))").run(String(until));
}
const caps = { rpm: 30, rpd: 1000, tpm: 8000, tpd: 200000 };
export function boundedMonthlyBudget(label: string): number {
  // Upstream parseBudget returns zero both for unknown labels and explicit
  // zero budgets. Preserve an actual zero instead of granting the ceiling.
  const head = String(label ?? '').toLowerCase().replace(/\([^)]*\)/g, '').trim();
  const magnitude = head.match(/~?([\d.]+)(?:-([\d.]+))?([mk])(?![a-z])/);
  if (magnitude && Number(magnitude[2] ?? magnitude[1]) === 0) {
    const tail = head.slice((magnitude.index ?? 0) + magnitude[0].length);
    if (!/^\s*(?:rpd|rpm|rph|rps|req|requests?|calls?|messages?|prompts?|neurons?)\b/.test(tail)) return 0;
  }
  return Math.min(parseBudget(label) || 6000000, 6000000);
}
export function filterCatalog<T extends { models: any[]; [key: string]: any }>(catalog: T): T {
  return { ...catalog, models: catalog.models.filter(m => approved(m.platform, m.modelId) && (!m.modality || m.modality === 'text')).map(m => ({
    ...m, supportsVision: false, modality: 'text', contextWindow: Math.min(m.contextWindow ?? 131072, 131072), monthlyTokenBudget: `${boundedMonthlyBudget(m.monthlyTokenBudget) / 1000}K`,
    limits: Object.fromEntries(Object.entries(caps).map(([k, cap]) => [k, typeof m.limits[k] === 'number' && m.limits[k] >= 0 ? Math.min(cap, m.limits[k]) : cap])),
  })), embeddings: [], transcriptionModels: [], videoModels: [], managedPlatforms: ['groq'], quirks: [] };
}
export function enforceDatabase(db: Db): void {
  policyDb = db;
  for (const row of db.prepare("SELECT id, monthly_token_budget FROM models WHERE platform='groq'").all() as { id: number; monthly_token_budget: string }[]) {
    db.prepare('UPDATE models SET monthly_token_budget=? WHERE id=?').run(`${boundedMonthlyBudget(row.monthly_token_budget) / 1000}K`, row.id);
  }
  db.prepare("UPDATE models SET enabled = 0 WHERE platform != 'groq' OR model_id NOT IN (?, ?)").run(...MODELS);
  db.prepare(`UPDATE models SET supports_vision = 0, rpm_limit = MIN(COALESCE(rpm_limit,30),30), rpd_limit = MIN(COALESCE(rpd_limit,1000),1000), tpm_limit = MIN(COALESCE(tpm_limit,8000),8000), tpd_limit = MIN(COALESCE(tpd_limit,200000),200000), context_window = MIN(COALESCE(context_window,131072),131072) WHERE platform = 'groq'`).run();
  db.prepare('UPDATE models SET enabled=0 WHERE rpm_limit <= 0 OR rpd_limit <= 0 OR tpm_limit <= 0 OR tpd_limit <= 0 OR context_window <= 0').run();
  db.prepare("UPDATE models SET enabled=0 WHERE monthly_token_budget='0K'").run();
  db.prepare("UPDATE models SET enabled = 0 WHERE EXISTS (SELECT 1 FROM catalog_model_tombstones t WHERE t.kind='chat' AND t.platform=models.platform AND t.model_id=models.model_id)").run();
  db.prepare('UPDATE media_models SET enabled = 0').run();
  db.prepare('UPDATE embedding_models SET enabled = 0').run();
  db.prepare("UPDATE api_keys SET enabled = 0 WHERE platform != 'groq'").run();
  const count = db.prepare("SELECT COUNT(*) n FROM api_keys WHERE platform='groq' AND enabled=1").get() as { n: number };
  if (count.n > 1) throw new Error('Only one Groq account is supported');
}
