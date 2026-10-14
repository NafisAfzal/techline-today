import fs from 'node:fs';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const hash = value => crypto.createHash('sha256').update(value).digest('hex');
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])]));
  return value;
}
function omit(value, names) { return Object.fromEntries(Object.entries(value).filter(([key]) => !names.includes(key))); }
export function editionFingerprint(snapshot, revision, archiveHashes = {}) {
  const data = omit(snapshot, ['generated_at', 'last_successful_fetch_at']);
  data.stories = snapshot.stories.map(story => omit(story, ['last_verified_at', 'importance_score_internal', 'novelty_score_internal'])).sort((a,b) => a.id.localeCompare(b.id));
  data.sources = Object.fromEntries(Object.entries(snapshot.sources).map(([id, source]) => [id, omit(source, ['fetched_at', 'http_etag', 'http_last_modified'])]));
  data.offers = snapshot.offers.map(offer => omit(offer, ['last_verified_at']));
  data.digests = snapshot.digests.map(digest => omit(digest, ['generated_at']));
  return hash(JSON.stringify(stable({revision, data, storyOrder:snapshot.stories.map(story => story.id), archiveHashes})));
}
export function editionDecision(fingerprint, receipt) {
  return {changed: receipt?.fingerprint !== fingerprint, fingerprint, reason: receipt ? receipt.fingerprint === fingerprint ? 'No semantic content or revision changes; retain the published edition.' : 'Content, calendar status, archives or code revision changed.' : 'No published receipt; initial publication required.'};
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const snapshot = JSON.parse(fs.readFileSync('content/generated/snapshot.json', 'utf8'));
  const revision = execFileSync('git', ['rev-parse', 'HEAD'], {encoding:'utf8'}).trim();
  const archives = Object.fromEntries(snapshot.archive_index.map(entry => {
    const archive = JSON.parse(fs.readFileSync(`content/archives/${entry.key}.json`, 'utf8'));
    return [entry.key, editionFingerprint({ ...archive, offers: archive.offers || [], digests: archive.digests || [] }, '')];
  }));
  const fingerprint = editionFingerprint(snapshot, revision, archives);
  const location = '.cache/publication-receipt.json';
  const receipt = fs.existsSync(location) ? JSON.parse(fs.readFileSync(location, 'utf8')) : null;
  if (process.argv.includes('--record')) fs.writeFileSync(location, JSON.stringify({version:1, fingerprint, revision, deployed_at:new Date().toISOString()})+'\n');
  else {
    const result = editionDecision(fingerprint, receipt);
    if (fs.existsSync('.cache/published-state/manifest.json') && !receipt) throw Error('Restored production state lacks its publication receipt; restore a complete recovery generation.');
    console.log(JSON.stringify(result));
    if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, `changed=${result.changed}\n`);
  }
}
