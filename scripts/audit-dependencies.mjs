import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import assert from 'node:assert/strict';

// Inspect the complete tree. No advisory is globally suppressed in pnpm configuration.
const command = process.platform === 'win32' ? 'pnpm.cmd audit --json' : 'pnpm audit --json';
const result = spawnSync(command, {shell: true, encoding: 'utf8', timeout: 120000, maxBuffer: 8 * 1024 * 1024});
if (result.error || ![0, 1].includes(result.status)) throw Error('Dependency audit failed to run; refusing to assume safety.');
const report = JSON.parse(result.stdout);
if (report.error || !report.advisories || !report.metadata) throw Error('Dependency audit returned an unexpected response.');
assert.equal(report.muted?.length || 0, 0, 'Suppressed advisories require review');
const webRequire = createRequire(new URL('../apps/web/package.json', import.meta.url));
const astroRequire = createRequire(webRequire.resolve('astro/package.json'));
const CachePolicy = astroRequire('http-cache-semantics');
const installed = astroRequire('http-cache-semantics/package.json').version;
assert.equal(installed, '4.3.0', 'Cache dependency changed; review the temporary mitigation.');
assert.equal(astroRequire('./package.json').version, '7.3.5', 'Astro changed; reassess cache exposure.');
for (const advisory of Object.values(report.advisories)) {
  console.log(`${advisory.severity.toUpperCase()} ${advisory.module_name}: ${advisory.github_advisory_id} — ${advisory.url}`);
  const accepted = advisory.github_advisory_id === 'GHSA-ch52-4w7c-c8xp'
    && advisory.module_name === 'http-cache-semantics'
    && advisory.patched_versions === '<0.0.0'
    && advisory.findings.length > 0
    && advisory.findings.every(finding => finding.version === installed && finding.paths.length > 0 && finding.paths.every(path => path === 'apps__web>astro>http-cache-semantics'));
  assert(accepted, 'Unreviewed advisory or a newly available upstream fix: update dependencies before proceeding.');
}
assert.equal(result.status, Object.keys(report.advisories).length ? 1 : 0, 'Unexpected audit exit status');
// 4.3.0 is outside the advisory database range, but its published code retains
// the reported behavior. Never interpret an empty registry report as a fix.
assert(Date.now() < Date.parse('2026-11-03T00:00:00Z'), 'Temporary cache mitigation expired; recheck upstream and deployment exposure.');
const request = {url: 'https://example.com/test', method: 'GET', headers: {host: 'example.com'}};
const attack = {...request, headers: {...request.headers, 'cache-control': 'max-stale=999999'}};
for (const headers of [{'set-cookie': 'session=synthetic'}, {'cache-control': 'private'}, {'cache-control': 'no-cache'}, {'cache-control': 'proxy-revalidate'}, {'cache-control': 's-maxage=0'}]) {
  const policy = new CachePolicy(request, {status: 200, headers: {...headers, 'cache-control': headers['cache-control'] || 'max-age=0, stale-if-error=3600, stale-while-revalidate=3600'}});
  assert.equal(policy.satisfiesWithoutRevalidation(attack), false, 'Local patch missing or ineffective');
  assert.equal(policy.useStaleWhileRevalidate(), false, 'Unsafe stale fallback');
  assert.equal(policy.revalidatedPolicy(attack, {status: 503, headers: {}}).modified, true, 'Unsafe error fallback');
}
assert.match(fs.readFileSync('apps/web/astro.config.mjs', 'utf8'), /output:\s*['"]static['"]/);
const wrangler = JSON.parse(fs.readFileSync('wrangler.jsonc', 'utf8'));
assert(!wrangler.main && !wrangler.assets?.binding, 'Runtime architecture changed; reassess the advisory.');
console.log(`Registry audit: ${Object.keys(report.advisories).length} advisory(s); none globally suppressed.`);
console.log('VISIBLE LOCAL MITIGATION: GHSA-ch52-4w7c-c8xp behavior persists in upstream 4.3.0 despite its database range. Locked patch verified; build-only Astro dependency has no deployed shared-cache path. Review by 2026-11-03. See docs/SECURITY.md.');
console.log('Dependency policy passed with one explicitly documented temporary mitigation; this is not proof of an upstream security fix.');
