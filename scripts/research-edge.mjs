import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync, execFileSync } from 'node:child_process';

execFileSync(process.execPath,['scripts/verify-research.mjs'],{stdio:'inherit'});
const env = {...process.env, WRANGLER_SEND_METRICS:'false'};
for (const key of Object.keys(env)) if (/(?:TOKEN|SECRET|API_KEY|ACCOUNT_ID)$/.test(key)) delete env[key];
const server = spawn(process.execPath,[path.resolve('node_modules/wrangler/bin/wrangler.js'),'dev','--local',
  '--config','wrangler.research-preview.jsonc','--ip','127.0.0.1','--port','4338','--inspector-port','0'],{env,stdio:['ignore','pipe','pipe']});
let output = '';
server.stdout.on('data', chunk => { output = (output + chunk).slice(-12000); });
server.stderr.on('data', chunk => { output = (output + chunk).slice(-12000); });
let startupError;
server.on('error', error => { startupError = error; });
const base = 'http://127.0.0.1:4338';
try {
  let ready = false;
  for (let attempt = 0; attempt < 120; attempt++) {
    if (startupError || server.exitCode !== null) throw Error('Local workerd failed: ' + (startupError?.message || output));
    try { ready = (await fetch(base,{signal:globalThis.AbortSignal.timeout(1000)})).ok; } catch { /* Startup only. */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve,250));
  }
  assert(ready, 'Local workerd startup timed out.');
  const astro = fs.readdirSync('apps/web/dist-research/_astro');
  const routes = ['/', '/bn/', '/robots.txt', '/rss.xml', '/data/latest.json', '/content-attribution.json',
    '/missing-route/', '/bn/missing-route/', '/_astro/' + astro.find(name => name.endsWith('.js')),
    '/_astro/' + astro.find(name => name.endsWith('.css'))];
  for (const route of routes) {
    const response = await fetch(base + route,{signal:globalThis.AbortSignal.timeout(5000)});
    assert.equal(response.status, route.includes('missing-route') ? 404 : 200, route);
    assert(response.headers.get('x-robots-tag')?.includes('noindex'), `Missing workerd noindex: ${route}`);
    assert(response.headers.get('cache-control')?.includes('no-store'), `Missing workerd no-store: ${route}`);
    assert.equal(response.headers.get('referrer-policy'), 'no-referrer', route);
    assert(response.headers.get('content-security-policy')?.includes("frame-ancestors 'none'"), `Missing workerd CSP: ${route}`);
    assert.equal(response.headers.get('x-content-type-options'), 'nosniff', route);
    assert(response.headers.get('link')?.includes('/content-attribution.json'), `Missing workerd attribution: ${route}`);
    if (route.endsWith('.js')) assert(response.headers.get('content-type')?.includes('javascript'), 'Incorrect JS MIME type');
    if (route.endsWith('.css')) assert(response.headers.get('content-type')?.includes('text/css'), 'Incorrect CSS MIME type');
    await response.arrayBuffer();
  }
  console.log(JSON.stringify({status:'passed', runtime:'local-workerd', routes:routes.length, smoke_origin:base, deployment_performed:false}));
} finally {
  // Terminate only this helper's process tree, including its local workerd child.
  if (process.platform === 'win32' && server.pid) spawnSync('taskkill',['/pid',String(server.pid),'/T','/F'],{stdio:'ignore'});
  else server.kill('SIGTERM');
}
