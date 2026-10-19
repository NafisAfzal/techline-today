import fs from 'node:fs';
import path from 'node:path';
import { inlineCspHashes } from './csp.mjs';
import { readSnapshot } from './read-snapshot.mjs';
const root = path.resolve('apps/web/dist');
function files(directory) { return fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry => entry.isDirectory() ? files(path.join(directory,entry.name)) : [path.join(directory,entry.name)]); }
const scripts = new Set(); const styles = new Set();
for (const file of files(root).filter(file => file.endsWith('.html'))) {
  const html = fs.readFileSync(file,'utf8');
  const hashes = inlineCspHashes(html);
  for (const hash of hashes.scripts) scripts.add(hash);
  for (const hash of hashes.styles) styles.add(hash);
}
const analytics = Boolean(process.env.PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN);
const csp = `default-src 'self'; script-src 'self' 'wasm-unsafe-eval' ${[...scripts].join(' ')}${analytics ? ' https://static.cloudflareinsights.com' : ''}; style-src 'self' ${[...styles].join(' ')}; img-src 'self' data:; font-src 'self'; connect-src 'self'${analytics ? ' https://cloudflareinsights.com' : ''}; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests`;
const headers = `/*\n  Content-Security-Policy: ${csp}\n  X-Content-Type-Options: nosniff\n  X-Frame-Options: DENY\n  Referrer-Policy: strict-origin-when-cross-origin\n  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()\n  Strict-Transport-Security: max-age=31536000\n/_astro/*\n  Cache-Control: public, max-age=31536000, immutable\n/data/*\n  Cache-Control: public, max-age=300, must-revalidate\n/pagefind/*\n  Cache-Control: public, max-age=0, must-revalidate\n`;
if (headers.split('\n').some(line => line.length > 2000)) throw new Error('Cloudflare header line limit exceeded');
fs.writeFileSync(path.join(root,'_headers'),headers);
const snapshot = readSnapshot('content/generated/snapshot.json');
const sourceRights = JSON.parse(fs.readFileSync('config/source-rights.json','utf8')).sources;
const exposedSources = {...snapshot.sources};
const archiveRoot = snapshot.mode === 'fixture' ? '.cache/fixture-archives' : 'content/archives';
for (const archive of snapshot.archive_index) {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(archive.key)) throw new Error('Unsafe archive path');
  fs.mkdirSync(path.join(root,'data/archives'),{recursive:true});
  fs.copyFileSync(path.join(archiveRoot, archive.key+'.json'), path.join(root,'data/archives',archive.key+'.json'));
  Object.assign(exposedSources, JSON.parse(fs.readFileSync(path.join(archiveRoot, archive.key+'.json'),'utf8')).sources);
}
for (const year of new Set(snapshot.archive_index.map(archive=>archive.key.slice(0,4)))) {
  fs.copyFileSync(path.join(archiveRoot,year+'.json'),path.join(root,'data/archives',year+'.json'));
}
const localized404 = path.join(root,'bn/404/index.html');
const attribution = {notice:'News material is separate from the MIT software license. Source wording has been excerpted, normalized, classified and summarized; no publisher endorsement is implied.',sources:Object.fromEntries(Object.entries(exposedSources).map(([id,source])=>[id,{title:source.title,publisher:source.publisher,original_url:source.original_url,license:sourceRights[source.source_registry_id]?.license || 'Synthetic test content; not cleared for publication',license_url:sourceRights[source.source_registry_id]?.license_url || null}]))};
fs.writeFileSync(path.join(root,'content-attribution.json'),JSON.stringify(attribution));
fs.appendFileSync(path.join(root,'_headers'),'/*\n  Link: </content-attribution.json>; rel="describedby"\n');
if (fs.existsSync(localized404)) {fs.renameSync(localized404,path.join(root,'bn/404.html'));fs.rmdirSync(path.join(root,'bn/404'));}
const assets = files(root);
if (assets.length > 18000 || assets.some(file => fs.statSync(file).size > 25 * 1024 * 1024)) throw new Error('Static asset budget exceeded');
console.log(`Hardened ${assets.length} assets. CSP permits ${scripts.size} exact inline script hashes.`);
