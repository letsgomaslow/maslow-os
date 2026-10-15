import express from 'express';
import { getDb } from '../db/index.js';
import { timingSafeStringEqual } from '../lib/system-prompt.js';
import { proxyRouter } from '../routes/proxy.js';
import { assertTextRequest, enforceDatabase, inferenceScope, MODELS } from './policy.js';

export function createMaslowApp(token: string) {
  if (!/^[A-Za-z0-9_-]{32,256}$/.test(token)) throw new Error('Instance token required');
  const app = express();
  app.disable('x-powered-by');
  app.use((req, res, next) => {
    if (req.headers.origin || !timingSafeStringEqual(req.headers.authorization ?? '', `Bearer ${token}`)) {
      res.status(401).json({ error: 'Unauthorized' }); return;
    }
    if (!((req.method === 'POST' && req.path === '/v1/chat/completions') || (req.method === 'GET' && req.path === '/v1/models')) || req.url.includes('?')) {
      res.status(404).json({ error: 'Unsupported endpoint' }); return;
    }
    next();
  });
  app.use(express.json({ limit: '1mb' }));
  app.get('/v1/models', (_req, res) => {
    enforceDatabase(getDb());
    const rows = getDb().prepare("SELECT model_id FROM models WHERE platform='groq' AND enabled=1 AND model_id IN (?,?)").all(...MODELS) as { model_id: string }[];
    res.json({ object: 'list', data: rows.map(r => ({ id: r.model_id, object: 'model', owned_by: 'groq' })) });
  });
  app.use('/v1', (req, res, next) => {
    try { assertTextRequest(req.body, true); enforceDatabase(getDb()); }
    catch { res.status(400).json({ error: 'Request denied by Maslow text/function policy' }); return; }
    if (req.body.max_tokens === undefined && req.body.max_completion_tokens === undefined) req.body.max_tokens = 2048;
    inferenceScope.run({ attempts: 0 }, next);
  }, proxyRouter);
  app.use((_err: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    res.status(400).json({ error: 'Invalid request' });
  });
  return app;
}
