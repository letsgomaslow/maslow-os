// Run with Node 22.23.3: node --test free_ai/tests/router-bootstrap.test.mjs
// Set MASLOW_ROUTER_ENTRY to the built server/dist/maslow-main.js first.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, stat, rm, mkdir, symlink, link, unlink, chmod } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import net from 'node:net';
import { DatabaseSync } from 'node:sqlite';
const entry = process.env.MASLOW_ROUTER_ENTRY;
if (!entry) throw new Error('MASLOW_ROUTER_ENTRY must identify the compiled isolated entry');
const token='synthetic-bootstrap-token-000000000000000000000000';
const groqKey='gsk_synthetic_000000000000000000';
async function port() {
  const s=net.createServer(); await new Promise(r=>s.listen(0,'127.0.0.1',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;
}
async function launch(config, blocker) {
 const p=spawn(process.execPath,['--import',blocker,entry],{stdio:['pipe','pipe','pipe']});
 let stdout='',stderr='';p.stdout.on('data',b=>stdout+=b);p.stderr.on('data',b=>stderr+=b);
 const exited=new Promise(r=>p.once('exit',r));p.stdin.end(JSON.stringify(config));
 const deadline=Date.now()+8000;
 while(!stdout.includes('\n') && p.exitCode===null && Date.now()<deadline) await new Promise(r=>setTimeout(r,20));
 if(!stdout.includes('\n') && p.exitCode===null){p.kill('SIGKILL');await exited;throw new Error('Startup timeout');}
 return {p,exited,output:()=>({stdout,stderr})};
}
test('private bootstrap fails closed and preserves encrypted account identity/quota across restart', async()=>{
 const dir=await mkdtemp(path.join(tmpdir(),'maslow-router-bootstrap-'));
 const blocker=path.join(dir,'no-network.mjs');await writeFile(blocker,"globalThis.fetch=async()=>{throw new Error('Network forbidden in bootstrap test')};\n",{mode:0o600});
 const dbPath=path.join(dir,'router.sqlite');
 const config={encryptionKey:'1'.repeat(64),instanceToken:token,groqKey,dbPath,port:await port()};
 let child;
 try {
  for (const missing of [{encryptionKey:undefined},{instanceToken:undefined}]) {
   child=await launch({...config,...missing},blocker);await child.exited;assert.equal(child.p.exitCode,1);assert.equal(child.output().stdout,'');assert.match(child.output().stderr,/startup_failed/);
  }
  const target=path.join(dir,'alias-target');await mkdir(target,{mode:0o700});
  const alias=path.join(dir,'alias');await symlink(target,alias);
  child=await launch({...config,dbPath:path.join(alias,'router.sqlite')},blocker);await child.exited;assert.equal(child.p.exitCode,1);assert.match(child.output().stderr,/startup_failed/);
  const mutable=path.join(dir,'mutable');await mkdir(mutable,{mode:0o700});await chmod(mutable,0o777);
  child=await launch({...config,dbPath:path.join(mutable,'nested','router.sqlite')},blocker);await child.exited;assert.equal(child.p.exitCode,1);assert.match(child.output().stderr,/startup_failed/);
  await writeFile(dbPath,'',{mode:0o600});const hard=path.join(dir,'snapshot.sqlite');await link(dbPath,hard);
  child=await launch(config,blocker);await child.exited;assert.equal(child.p.exitCode,1);assert.match(child.output().stderr,/startup_failed/);
  await unlink(hard);await unlink(dbPath);
  for(let iteration=0;iteration<2;iteration++) {
   child=await launch(config,blocker);const ready=JSON.parse(child.output().stdout);assert.equal(ready.event,'ready');assert.equal(ready.host,'127.0.0.1');assert.equal(ready.port,config.port);
   const response=await fetch(`http://127.0.0.1:${config.port}/v1/models`,{headers:{Authorization:`Bearer ${token}`}});assert.equal(response.status,200);assert.equal((await response.json()).data.length,2);
   const unauth=await fetch(`http://127.0.0.1:${config.port}/v1/models`);assert.equal(unauth.status,401);
   child.p.kill('SIGTERM');await child.exited;assert.equal(child.p.exitCode,0);assert.equal(child.output().stderr,'');assert.equal(child.output().stdout.split('\n').filter(Boolean).length,1);
   assert.equal((await stat(dbPath)).mode & 0o777,0o600);
   const bytes=await readFile(dbPath);assert.equal(bytes.includes(Buffer.from(groqKey)),false);assert.equal(bytes.includes(Buffer.from(token)),false);
   const db=new DatabaseSync(dbPath);const rows=db.prepare('SELECT id FROM api_keys').all();assert.equal(rows.length,1);assert.equal(rows[0].id,1);
   if(iteration===0)db.prepare("INSERT INTO rate_limit_usage(platform,model_id,key_id,kind,tokens,created_at_ms) VALUES('groq','openai/gpt-oss-120b',1,'tokens',42,?)").run(Date.now());
   else assert.equal(db.prepare('SELECT tokens FROM rate_limit_usage WHERE key_id=1').get().tokens,42);
   db.close();
  }
 } finally { if(child?.p.exitCode===null){child.p.kill('SIGKILL');await child.exited;} await rm(dir,{recursive:true,force:true}); }
});
