import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import crypto from 'node:crypto';
import { initDb, getDb, setSetting } from '../../db/index.js';
import { encrypt } from '../../lib/crypto.js';
import { createMaslowApp } from '../../maslow/app.js';
import { boundedMonthlyBudget, enforceDatabase, inferenceScope, MODELS, GROQ_CHAT_URL } from '../../maslow/policy.js';
import { proxyFetch } from '../../lib/proxy.js';
import { GoogleProvider } from '../../providers/google.js';
import { applyCatalog, reapplyCachedCatalog, syncCatalog } from '../../services/catalog-sync.js';
import { runCustomModelSync } from '../../services/custom-model-sync.js';
import { recordCatalogModelTombstone, retireCatalogModelUpstream } from '../../services/model-state.js';
const TOKEN = 'synthetic-instance-token-0000000000000000';
const nativeFetch = globalThis.fetch;
let servers: any[] = [];
const model = (id = MODELS[0], extra = {}) => ({ platform:'groq',modelId:id,displayName:id,intelligenceRank:5,speedRank:5,sizeLabel:'Medium',limits:{rpm:30,rpd:1000,tpm:8000,tpd:200000},monthlyTokenBudget:'~6M',contextWindow:131072,enabled:true,supportsVision:false,supportsTools:true,...extra });
const catalog = (models = [model(),model(MODELS[1])]) => ({ version:'2099.10.11',generatedAt:new Date().toISOString(),tier:'monthly' as const,models,quirks:[] });
function key(platform='groq',base='') {
 const e=encrypt('gsk_synthetic_000000000000');
 getDb().prepare("INSERT INTO api_keys(platform,label,encrypted_key,iv,auth_tag,status,enabled,base_url) VALUES(?,?,?,?,?,'unknown',1,?)").run(platform,'synthetic',e.encrypted,e.iv,e.authTag,base);
}
async function request(route: string, body?: any, auth = TOKEN) {
 const server=createMaslowApp(TOKEN).listen(0,'127.0.0.1');servers.push(server);
 await new Promise<void>(r=>server.once('listening',r));
 const response=await nativeFetch(`http://127.0.0.1:${(server.address() as any).port}${route}`,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${auth}`,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 return { status:response.status, body:await response.text() };
}
const textBody=()=>({ model:MODELS[0],messages:[{role:'user',content:'hello'}] });
beforeEach(()=>{
 process.env.ENCRYPTION_KEY='1'.repeat(64);process.env.NODE_ENV='test';process.env.MASLOW_INSTANCE_TOKEN=TOKEN;
 initDb(':memory:');applyCatalog(getDb(),catalog());key();enforceDatabase(getDb());
 setSetting('response_cache_enabled','false');
 vi.stubGlobal('fetch',vi.fn(async()=>{throw new Error('Unexpected network');}));
});
afterEach(()=>{for(const s of servers)s.close();servers=[];getDb().close?.();vi.unstubAllGlobals();delete process.env.CATALOG_PUBKEY;});
describe('Maslow upstream boundary',()=>{
 it('exposes authenticated filtered models and no admin/discovery/media/API aliases',async()=>{
  expect((await request('/v1/models',undefined,'wrong')).status).toBe(401);
  const listed=await request('/v1/models');expect(listed.status).toBe(200);expect(JSON.parse(listed.body).data.map((m:any)=>m.id).sort()).toEqual([...MODELS].sort());
  for(const route of ['/api/keys','/api/settings','/api/update','/v1/responses','/v1/images/generations','/v1/embeddings','/v1/models?x=1','/v1/messages'])expect((await request(route,{})).status).toBe(404);
  expect(globalThis.fetch).not.toHaveBeenCalled();
 });
 it('rejects images, built-in tools, arbitrary endpoint fields and unapproved explicit/auto models',async()=>{
  for(const body of [{...textBody(),model:'google/gemini-2.5-flash'},{...textBody(),model:'auto:vision'},{...textBody(),base_url:'http://127.0.0.1'},{...textBody(),tools:[{type:'web_search'}]},{...textBody(),messages:[{role:'user',content:[{type:'image_url',image_url:{url:'http://127.0.0.1/private'}}]}]}])expect((await request('/v1/chat/completions',body)).status).toBe(400);
  expect(globalThis.fetch).not.toHaveBeenCalled();
 });
 it('executes real upstream nonstreaming provider dispatch and function payload',async()=>{
  vi.mocked(globalThis.fetch).mockImplementation(async(url,init)=>{
   expect(url).toBe(GROQ_CHAT_URL);expect(init?.redirect).toBe('error');
   const body=JSON.parse(init?.body as string);expect(body.model).toBe(MODELS[0]);expect(body.tools[0].type).toBe('function');
   return new Response(JSON.stringify({id:'synthetic',object:'chat.completion',created:1,model:MODELS[0],choices:[{index:0,message:{role:'assistant',content:'hello'},finish_reason:'stop'}],usage:{prompt_tokens:2,completion_tokens:1,total_tokens:3}}),{headers:{'Content-Type':'application/json'}});
  });
  const result=await request('/v1/chat/completions',{...textBody(),tools:[{type:'function',function:{name:'test',parameters:{type:'object',properties:{}}}}]});
  expect(result.status,result.body).toBe(200);expect(globalThis.fetch).toHaveBeenCalledTimes(1);
 });
 it('runs actual upstream streaming with only the approved model',async()=>{
  vi.mocked(globalThis.fetch).mockImplementation(async(url,init)=>{
   expect(url).toBe(GROQ_CHAT_URL);const b=JSON.parse(init?.body as string);expect(b.stream).toBe(true);expect(MODELS).toContain(b.model);
   const chunk={id:'stream',object:'chat.completion.chunk',created:1,model:b.model,choices:[{index:0,delta:{role:'assistant',content:'hello'},finish_reason:null}]};
   const done={...chunk,choices:[{index:0,delta:{},finish_reason:'stop'}],usage:{prompt_tokens:2,completion_tokens:1,total_tokens:3}};
   return new Response(`data: ${JSON.stringify(chunk)}\n\ndata: ${JSON.stringify(done)}\n\ndata: [DONE]\n\n`,{headers:{'Content-Type':'text/event-stream'}});
  });
  const r=await request('/v1/chat/completions',{...textBody(),stream:true});expect(r.status,r.body).toBe(200);expect(r.body).toContain('[DONE]');expect(globalThis.fetch).toHaveBeenCalledTimes(1);
 });
 it('runs upstream fallback after missing model without escaping the two-model policy',async()=>{
  const seen:string[]=[];
  vi.mocked(globalThis.fetch).mockImplementation(async(url,init)=>{
   expect(url).toBe(GROQ_CHAT_URL);const b=JSON.parse(init?.body as string);expect(MODELS).toContain(b.model);seen.push(b.model);
   if(seen.length===1)return new Response(JSON.stringify({error:{message:'model not found'}}),{status:404});
   return new Response(JSON.stringify({id:'fallback',object:'chat.completion',created:1,model:b.model,choices:[{index:0,message:{role:'assistant',content:'hello'},finish_reason:'stop'}],usage:{prompt_tokens:2,completion_tokens:1,total_tokens:3}}),{headers:{'Content-Type':'application/json'}});
  });
  const r=await request('/v1/chat/completions',{...textBody(),model:'auto'});expect(r.status,r.body).toBe(200);expect(seen.length).toBe(2);expect(new Set(seen).size).toBe(2);
 });
 it('shares provider 429 cooldown across both routes and later requests',async()=>{
  vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({error:{message:'rate limit exceeded'}}),{status:429,headers:{'retry-after':'60'}}));
  const first=await request('/v1/chat/completions',{...textBody(),model:'auto'});expect(first.status).toBe(429);expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  const second=await request('/v1/chat/completions',{...textBody(),model:MODELS[1]});expect(second.status).not.toBe(200);expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  expect(Number((getDb().prepare("SELECT value FROM settings WHERE key='maslow_groq_cooldown_until'").get() as any).value)).toBeGreaterThan(Date.now());
 });
 it('rejects cumulative context/tool payload and output over policy ceiling',async()=>{
  for(const body of [{...textBody(),max_tokens:2049},{...textBody(),max_completion_tokens:2049},{...textBody(),messages:[{role:'user',content:'a'.repeat(64001)}]},{...textBody(),tools:[{type:'function',function:{name:'f',description:'a'.repeat(64000)}}]}])expect((await request('/v1/chat/completions',body)).status).toBe(400);
  expect(globalThis.fetch).not.toHaveBeenCalled();
 });
 it('does not expand previously reduced limits or tools on cached/fetched catalog reapply',()=>{
  applyCatalog(getDb(),catalog([model(MODELS[0],{limits:{rpm:5,rpd:10,tpm:100,tpd:200},monthlyTokenBudget:'1K',contextWindow:4096,supportsTools:false}),model(MODELS[1])]));
  applyCatalog(getDb(),catalog());const row=getDb().prepare('SELECT * FROM models WHERE model_id=?').get(MODELS[0]) as any;
  expect([row.rpm_limit,row.rpd_limit,row.tpm_limit,row.tpd_limit,row.monthly_token_budget,row.context_window,row.supports_tools]).toEqual([5,10,100,200,'1K',4096,0]);
 });
 it('preserves explicit zero monthly metadata and disables the route across later feeds',()=>{
  applyCatalog(getDb(),catalog([model(MODELS[0],{monthlyTokenBudget:'0K'}),model(MODELS[1])]));
  applyCatalog(getDb(),catalog());
  const row=getDb().prepare('SELECT monthly_token_budget,enabled FROM models WHERE model_id=?').get(MODELS[0]) as any;
  expect(row.monthly_token_budget).toBe('0K');expect(row.enabled).toBe(0);
 });
 it('distinguishes decorated zero token budgets from unknown request-count labels',()=>{
  for(const label of ['0K','0K tokens/month','~0M/month','0K tokens/day','free · 0K tokens/24h'])expect(boundedMonthlyBudget(label)).toBe(0);
  for(const label of ['unknown','0K calls/mo','0 RPM'])expect(boundedMonthlyBudget(label)).toBe(6000000);
 });
 it('blocks Gemini private-image fetch on the actual adapter path',async()=>{
  await expect(inferenceScope.run({ attempts: 0 },()=>new GoogleProvider().chatCompletion('synthetic',[{role:'user',content:[{type:'image_url',image_url:{url:'http://127.0.0.1/private'}}]}],'gemini-2.5-flash'))).rejects.toThrow();
  expect(globalThis.fetch).not.toHaveBeenCalled();
 });
 it('denies dispatch outside a request, custom endpoints, unapproved models and disabled models',async()=>{
  const init={method:'POST',body:JSON.stringify(textBody())};
  await expect(proxyFetch(GROQ_CHAT_URL,init,'groq')).rejects.toThrow('Dispatch denied');
  for(const [url,platform,modelId] of [[GROQ_CHAT_URL,'google',MODELS[0]],['https://evil.example/v1/chat/completions','groq',MODELS[0]],[GROQ_CHAT_URL,'groq','paid-model']])await expect(inferenceScope.run({ attempts: 0 },()=>proxyFetch(url,{...init,body:JSON.stringify({...textBody(),model:modelId})},platform))).rejects.toThrow();
  getDb().prepare("UPDATE models SET enabled=0 WHERE model_id=?").run(MODELS[0]);
  await expect(inferenceScope.run({ attempts: 0 },()=>proxyFetch(GROQ_CHAT_URL,init,'groq'))).rejects.toThrow('disabled');expect(globalThis.fetch).not.toHaveBeenCalled();
 });
 it('prevents former custom paid-model enrollment through actual discovery/sync',async()=>{
  key('custom','https://paid.example/v1');
  vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({data:[{id:'paid-chat',pricing:{prompt:'10',completion:'20'}}]})));
  const result=await runCustomModelSync(getDb());expect(result.added).toBe(0);expect(result.failures.length).toBeGreaterThan(0);expect(globalThis.fetch).not.toHaveBeenCalled();
 });
 it('filters cached catalog expansions and preserves disables, tombstones, retirement and quota ceilings',()=>{
  const db=getDb();db.prepare('UPDATE models SET enabled=0 WHERE model_id=?').run(MODELS[0]);
  const id=(db.prepare('SELECT id FROM models WHERE model_id=?').get(MODELS[1]) as any).id;
  retireCatalogModelUpstream(db,id,'groq',MODELS[1],'synthetic retirement');
  const bad=catalog([model(MODELS[0],{supportsVision:true,limits:{rpm:999999,rpd:null,tpm:999999,tpd:null}}),model(MODELS[1]),model('paid-model' as any,{platform:'custom'})]);
  setSetting('catalog_applied_json',JSON.stringify(bad));expect(reapplyCachedCatalog().reapplied).toBe(true);
  expect((db.prepare('SELECT COUNT(*) n FROM models WHERE enabled=1').get() as any).n).toBe(0);
  const row=db.prepare('SELECT * FROM models WHERE model_id=?').get(MODELS[0]) as any;expect(row.supports_vision).toBe(0);expect(row.rpm_limit).toBe(30);expect(row.tpd_limit).toBe(200000);
  recordCatalogModelTombstone(db,'chat','groq',MODELS[0]);applyCatalog(db,catalog());expect(db.prepare('SELECT id FROM models WHERE model_id=?').get(MODELS[0])).toBeUndefined();
 });
 it('preserves a local disable across disappearance and later catalog return',()=>{
  getDb().prepare('UPDATE models SET enabled=0 WHERE model_id=?').run(MODELS[0]);
  applyCatalog(getDb(),catalog([model(MODELS[1])]));applyCatalog(getDb(),catalog());
  expect(getDb().prepare('SELECT id FROM models WHERE model_id=? AND enabled=1').get(MODELS[0])).toBeUndefined();
 });
 it('keeps catalog-removed models retired after their later return',()=>{
  applyCatalog(getDb(),catalog([model(MODELS[1])]));applyCatalog(getDb(),catalog());
  expect(getDb().prepare('SELECT id FROM models WHERE model_id=? AND enabled=1').get(MODELS[0])).toBeUndefined();
 });
 it('caps actual dispatch attempts even if an upstream caller supplies extra retries',async()=>{
  vi.mocked(globalThis.fetch).mockResolvedValue(new Response('{}'));
  await inferenceScope.run({attempts:0},async()=>{
   const init={method:'POST',body:JSON.stringify({...textBody(),max_tokens:128})};
   await proxyFetch(GROQ_CHAT_URL,init,'groq');await proxyFetch(GROQ_CHAT_URL,init,'groq');
   await expect(proxyFetch(GROQ_CHAT_URL,init,'groq')).rejects.toThrow('attempt limit');
  });expect(globalThis.fetch).toHaveBeenCalledTimes(2);
 });
 it('verifies signed fetched catalogs before applying and retains last good state on bad signature',async()=>{
  const {publicKey,privateKey}=crypto.generateKeyPairSync('ed25519');process.env.CATALOG_PUBKEY=publicKey.export({type:'spki',format:'pem'}).toString();
  const bytes=JSON.stringify(catalog([model(MODELS[0],{supportsVision:true,limits:{rpm:99999,rpd:999999,tpm:999999,tpd:999999}}),model('new-paid' as any)]));
  vi.mocked(globalThis.fetch).mockResolvedValue(new Response(bytes,{headers:{'x-catalog-signature':crypto.sign(null,Buffer.from(bytes),privateKey).toString('base64')}}));
  expect((await syncCatalog(true)).ok).toBe(true);expect((getDb().prepare('SELECT COUNT(*) n FROM models WHERE enabled=1').get() as any).n).toBe(1);
  vi.mocked(globalThis.fetch).mockResolvedValue(new Response(bytes,{headers:{'x-catalog-signature':'AAAA'}}));expect((await syncCatalog(true)).ok).toBe(false);expect((getDb().prepare('SELECT COUNT(*) n FROM models WHERE enabled=1').get() as any).n).toBe(1);
 });
});
