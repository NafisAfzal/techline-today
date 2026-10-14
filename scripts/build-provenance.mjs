import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const git = (...args) => { try { return execFileSync('git', args, { encoding:'utf8', stdio:['ignore','pipe','ignore'] }); } catch { return ''; } };
const walk = directory => fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry => entry.isDirectory() ? walk(path.join(directory,entry.name)) : [path.join(directory,entry.name)]);
function digestFiles(names, root = '.') {
  const hash = crypto.createHash('sha256');
  for (const name of [...names].sort()) {
    hash.update(name.replaceAll('\\','/') + '\0');
    hash.update(sha(fs.readFileSync(path.join(root,name))) + '\n');
  }
  return hash.digest('hex');
}
export function currentProvenance(root = 'apps/web/dist') {
  const source = [...new Set(git('ls-files','--cached','--others','--exclude-standard','-z').split('\0').filter(Boolean))].filter(name => /^(?:pipeline\/|packages\/|config\/|prompts\/|schemas\/|scripts\/|\.github\/workflows\/|apps\/web\/(?:src\/|public\/|[^/]+\.(?:json|mjs|ts))|(?:package\.json|pnpm-lock\.yaml|uv\.lock|pyproject\.toml|wrangler(?:\.preview)?\.jsonc|pnpm-workspace\.yaml)$)/.test(name));
  const assets = walk(root).map(name => path.relative(root,name)).filter(name => name !== 'release-manifest.json');
  const snapshot = fs.readFileSync('content/generated/snapshot.json');
  const data = JSON.parse(snapshot);
  const archiveRoot = data.mode === 'fixture' ? '.cache/fixture-archives' : 'content/archives';
  const archiveNames = [...new Set(data.archive_index.flatMap(entry => [entry.key+'.json',entry.key.slice(0,4)+'.json']))];
  return {version:1,revision:git('rev-parse','HEAD').trim() || null,source_sha256:digestFiles(source),snapshot_sha256:sha(snapshot),archive_sha256:digestFiles(archiveNames,archiveRoot),mode:data.mode,generated_at:data.generated_at,assets_sha256:digestFiles(assets,root)};
}
export function provenanceErrors(built, current) {
  return ['version','revision','source_sha256','snapshot_sha256','archive_sha256','mode','generated_at','assets_sha256'].filter(key => built?.[key] !== current[key]).map(key => `Build provenance mismatch: ${key}; rebuild the current live edition.`);
}
export function verifyProvenance(root = 'apps/web/dist') {
  const built = JSON.parse(fs.readFileSync(path.join(root,'release-manifest.json'),'utf8'));
  const errors = provenanceErrors(built,currentProvenance(root));
  const latest = JSON.parse(fs.readFileSync(path.join(root,'data/latest.json'),'utf8'));
  if (latest.mode !== built.mode || latest.generated_at !== built.generated_at) errors.push('Built data does not match the validated snapshot.');
  if (errors.length) throw Error(errors.join(' '));
  return built;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  fs.writeFileSync('apps/web/dist/release-manifest.json',JSON.stringify(currentProvenance(),null,2)+'\n');
  console.log('Build revision, source, snapshot and asset checksums recorded.');
}
