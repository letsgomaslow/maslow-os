// Package-only embedding entry. Never import upstream index/app or .env loading.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { initDb, getDb, setSetting } from './db/index.js';
import { encrypt } from './lib/crypto.js';
import { createMaslowApp } from './maslow/app.js';
import { enforceDatabase } from './maslow/policy.js';
import { reapplyCachedCatalog, startCatalogSync, stopCatalogSync } from './services/catalog-sync.js';
import { NodeScheduler } from './lib/scheduler.js';

// Silence upstream diagnostics, which may include provider errors or key material.
// The parent receives only bounded machine-readable lifecycle records.
console.log = console.info = console.warn = console.error = () => {};
process.umask(0o077);
async function main() {
  let input = '';
  for await (const chunk of process.stdin) {
    input += chunk.toString();
    if (Buffer.byteLength(input) > 16384) throw new Error('Bootstrap too large');
  }
  const config = JSON.parse(input); input = '';
  if (!/^[0-9a-fA-F]{64}$/.test(config.encryptionKey ?? '') || !/^[A-Za-z0-9_-]{32,256}$/.test(config.instanceToken ?? '')) throw new Error('Credentials unavailable');
  if (typeof config.dbPath !== 'string' || !path.isAbsolute(config.dbPath)) throw new Error('Private database path required');
  const port = config.port ?? 18573;
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid port');
  if (config.groqKey !== undefined && (typeof config.groqKey !== 'string' || !/^gsk_[A-Za-z0-9_-]{8,250}$/.test(config.groqKey))) throw new Error('Invalid provider credential');
  const directory = path.dirname(config.dbPath);
  if (path.resolve(config.dbPath) !== config.dbPath) throw new Error('Canonical database path required');
  // Check ancestry before creating anything; do not traverse aliases or mutable parents.
  for (let current = directory;; current = path.dirname(current)) {
    if (fs.existsSync(current)) {
      const ancestor = fs.lstatSync(current);
      const trustedStickyRoot = ancestor.uid === 0 && Boolean(ancestor.mode & 0o1000);
      if (!ancestor.isDirectory() || ancestor.isSymbolicLink() || ((ancestor.mode & 0o022) !== 0 && !trustedStickyRoot)) throw new Error('Unsafe database ancestry');
    }
    if (current === path.dirname(current)) break;
  }
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const stat = fs.lstatSync(directory);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (stat.mode & 0o077) !== 0 || stat.uid !== process.getuid?.()) throw new Error('Private database directory required');
  for (const filename of [config.dbPath, `${config.dbPath}-wal`, `${config.dbPath}-shm`]) {
    let file: fs.Stats;
    try { file = fs.lstatSync(filename); }
    catch (error) { if ((error as NodeJS.ErrnoException).code === 'ENOENT') continue; throw error; }
    if (!file.isFile() || file.isSymbolicLink() || file.nlink !== 1 || (file.mode & 0o077) !== 0 || file.uid !== process.getuid?.()) throw new Error('Private unaliased database required');
  }
  // Ignore inherited optional routing, proxy, catalog and production overrides.
  for (const key of Object.keys(process.env)) {
    if (!['PATH', 'HOME', 'LANG', 'TZ'].includes(key)) delete process.env[key];
  }
  process.env.NODE_ENV = 'production';
  process.env.ENCRYPTION_KEY = config.encryptionKey;
  process.env.MASLOW_INSTANCE_TOKEN = config.instanceToken;
  const db = initDb(config.dbPath);
  delete process.env.ENCRYPTION_KEY;
  delete config.encryptionKey;
  // Persist ciphertext only; one account means shared limits are never multiplied.
  if (config.groqKey) {
    const e = encrypt(config.groqKey); delete config.groqKey;
    db.transaction(() => {
      const rows = db.prepare("SELECT id FROM api_keys WHERE platform='groq'").all() as { id: number }[];
      if (rows.length > 1) throw new Error('Multiple Groq accounts denied');
      if (rows.length === 1) {
        // Keep the key id: restarts/key replacement must not reset quota history.
        db.prepare("UPDATE api_keys SET encrypted_key=?,iv=?,auth_tag=?,status='unknown',enabled=1 WHERE id=?").run(e.encrypted,e.iv,e.authTag,rows[0].id);
      } else {
        db.prepare("INSERT INTO api_keys(platform,label,encrypted_key,iv,auth_tag,status,enabled) VALUES('groq','Personal Groq account',?,?,?,'unknown',1)").run(e.encrypted, e.iv, e.authTag);
      }
    })();
  }
  setSetting('response_cache_enabled', 'false');
  setSetting('compression', JSON.stringify({ mode: 'off' }));
  db.prepare("DELETE FROM settings WHERE key IN ('premium_license_key','premium_license_status')").run();
  reapplyCachedCatalog();
  enforceDatabase(db);
  const app = createMaslowApp(config.instanceToken);
  const server = app.listen(port, '127.0.0.1', () => {
    process.stdout.write(JSON.stringify({ event: 'ready', host: '127.0.0.1', port, tokenId: crypto.createHash('sha256').update(config.instanceToken).digest('hex') }) + '\n');
    startCatalogSync(new NodeScheduler());
  });
  server.on('error', () => { process.stderr.write('{"event":"error","code":"listen_failed"}\n'); process.exit(1); });
  const shutdown = () => { stopCatalogSync(); server.close(() => { getDb().close?.(); process.exit(0); }); setTimeout(() => process.exit(1), 3000).unref(); };
  process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);
}
main().catch(() => { process.stderr.write('{"event":"error","code":"startup_failed"}\n'); process.exit(1); });
