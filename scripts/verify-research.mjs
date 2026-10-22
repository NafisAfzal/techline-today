import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';

process.env.TECHLINE_RESEARCH_REHEARSAL = 'true';
const {readBuildSnapshot, buildDirectory} = await import('./research-policy.mjs');
const {readSnapshot} = await import('./read-snapshot.mjs');
const {verifyProvenance} = await import('./build-provenance.mjs');
const snapshot = readBuildSnapshot('content/generated/snapshot.json');
const raw = readSnapshot('content/generated/snapshot.json');
const manifest = verifyProvenance(buildDirectory);
assert.equal(manifest.profile, 'research-rehearsal');
const walk = directory => fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry => {
  assert(!entry.isSymbolicLink(), 'Linked build assets are forbidden.');
  return entry.isDirectory() ? walk(path.join(directory,entry.name)) : [path.join(directory,entry.name)];
});
const files = walk(buildDirectory);
const bytes = files.reduce((sum, file) => sum + fs.statSync(file).size, 0);
assert(files.length <= 18000 && bytes <= 25 * 1024 * 1024, 'Research bundle exceeds conservative Free/rollback budgets.');
assert(files.every(file => fs.statSync(file).size <= 25 * 1024 * 1024), 'Asset exceeds Free limit.');
const headers = fs.readFileSync(path.join(buildDirectory, '_headers'), 'utf8');
const patterns = headers.split('\n').filter(line => line.startsWith('/'));
assert.equal(new Set(patterns).size, patterns.length, 'Duplicate header patterns can discard Cloudflare security headers.');
for (const required of ['X-Robots-Tag: noindex, nofollow, noarchive', 'Cache-Control: no-store', "frame-ancestors 'none'", 'X-Content-Type-Options: nosniff', 'Referrer-Policy: no-referrer']) assert(headers.includes(required), `Missing research header: ${required}`);
assert(!/'unsafe-inline'|'unsafe-eval'|cloudflareinsights\.com/.test(headers), 'Unsafe CSP or analytics enabled.');
assert(headers.split('\n').every(line => line.length <= 2000), 'Header exceeds Cloudflare line limit.');
assert(/^Disallow: \/$/m.test(fs.readFileSync(path.join(buildDirectory,'robots.txt'),'utf8')), 'Research robots must disallow crawling.');
const excluded = raw.stories.filter(story => !snapshot.stories.some(selected => selected.id === story.id));
for (const file of files) {
  assert(!/(?:^|[\\/])(?:\.env|\.cache|\.git|pipeline|config|node_modules)(?:[\\/]|$)/.test(file), 'Private path in build.');
  if (!/\.(?:html|json|xml|js|txt|css)$/.test(file)) continue;
  const text = fs.readFileSync(file,'utf8');
  assert(!/GEMINI_API_KEY|GROQ_API_KEY|OPENROUTER_API_KEY|CLOUDFLARE_API_TOKEN|TECHLINE_EXTERNAL_CHECKPOINT|beacon\.min\.js/.test(text), 'Private configuration or analytics in output.');
  if (file.endsWith('.html')) {
    assert(/<meta[^>]+name="robots"[^>]+content="noindex, nofollow"/.test(text), `Indexable research route: ${file}`);
    assert(text.includes('research-edition-notice'), `Missing research notice: ${file}`);
  }
  if (/\.(?:html|json|xml)$/.test(file)) for (const story of excluded) assert(!text.includes(story.slug) && !text.includes(story.headline), 'Excluded story leaked into an aggregate or route.');
}
const latest = JSON.parse(fs.readFileSync(path.join(buildDirectory,'data/latest.json'),'utf8'));
assert.deepEqual(latest.stories.map(story => story.id), snapshot.stories.map(story => story.id));
const js = files.filter(file => file.endsWith('.js') && file.includes(`${path.sep}_astro${path.sep}`));
const css = files.filter(file => file.endsWith('.css') && file.includes(`${path.sep}_astro${path.sep}`));
const jsGzip = js.reduce((sum,file) => sum + gzipSync(fs.readFileSync(file)).length, 0);
const cssBytes = css.reduce((sum,file) => sum + fs.statSync(file).size, 0);
assert(jsGzip < 100000 && cssBytes < 40000, 'Research client asset budget exceeded.');
console.log(JSON.stringify({status:'passed', profile:manifest.profile, synthetic_stories:snapshot.stories.length,
  eligible_real_stories:0, assets:files.length, total_bytes:bytes, all_application_js_gzip:jsGzip, css_bytes:cssBytes,
  publication_allowed:false, deployment_performed:false}, null, 2));
if (process.argv.includes('--publish')) {
  const {researchEligibility} = await import('./research-inventory.mjs');
  const readiness = researchEligibility(raw);
  throw Error(`Research publication refused: ${readiness.eligible_count} real eligible records; independently authenticated current checkpoint custody is unavailable. Synthetic rehearsal cannot be deployed.`);
}
