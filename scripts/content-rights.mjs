import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { assertGenerationStable } from './generation-state.mjs';
import rightsPolicy from '../config/source-rights.json' with {type:'json'};

export const rights = rightsPolicy.sources;
export function contentRightsErrors(snapshot, policy = rights) {
  const errors = [];
  if (snapshot.mode !== 'live') return ['Publication requires live content.'];
  for (const source of Object.values(snapshot.sources || {})) {
    // Local observation provenance has no trusted publication attestation.
    // Legacy public SourceItem records retain their established schema/policy.
    if (source.internal_only === true || Object.hasOwn(source, 'provenance')) errors.push('Local-only provenance evidence is present.');
    if (source.is_demo || policy[source.source_registry_id]?.publication !== 'allow') errors.push('Excluded or synthetic source evidence is present.');
    if (source.rights_review != null || source.advisory != null || source.editorial_kind === 'security-advisory') errors.push('Local-only review/advisory evidence is present.');
  }
  for (const story of snapshot.stories || []) {
    if (story.is_demo || story.translations?.bn?.review_status === 'fixture-reviewed') errors.push('Synthetic story/translation is present.');
    const ids = new Set([...story.source_ids, ...story.change_log.flatMap(change => [...change.source_ids, ...change.previous_facts.flatMap(fact => fact.source_ids)])]);
    if ([...ids].some(id => !snapshot.sources[id])) errors.push('A story or its correction history has missing evidence.');
  }
  return [...new Set(errors)];
}

export function verifyContentRights(root = 'apps/web/dist') {
  assertGenerationStable();
  const snapshot = JSON.parse(fs.readFileSync('content/generated/snapshot.json', 'utf8'));
  const errors = contentRightsErrors(snapshot);
  for (const entry of snapshot.archive_index) {
    const archive = JSON.parse(fs.readFileSync(path.join('content/archives', `${entry.key}.json`), 'utf8'));
    errors.push(...contentRightsErrors({mode: 'live', ...archive}));
  }
  if (fs.existsSync(root)) {
    const walk = directory => fs.readdirSync(directory, {withFileTypes: true}).flatMap(item => item.isDirectory() ? walk(path.join(directory, item.name)) : [path.join(directory, item.name)]);
    for (const file of walk(root).filter(file => file.endsWith('.json'))) {
      const payload = JSON.parse(fs.readFileSync(file, 'utf8'));
      const visit = value => {
        if (!value || typeof value !== 'object') return;
        if (value.internal_only === true || Object.hasOwn(value, 'provenance')) errors.push('Build JSON contains local-only provenance evidence.');
        if (value.is_demo === true || (value.source_registry_id && rights[value.source_registry_id]?.publication !== 'allow')) errors.push('Build JSON contains excluded or synthetic evidence.');
        if (value.rights_review != null || value.advisory != null || value.editorial_kind === 'security-advisory') errors.push('Build JSON contains local-only review/advisory evidence.');
        Object.values(value).forEach(visit);
      };
      visit(payload);
    }
    assert(fs.readFileSync(path.join(root, 'third-party-notices.txt'), 'utf8').includes('MIT License'), 'Software notices are missing.');
    const attribution = JSON.parse(fs.readFileSync(path.join(root, 'content-attribution.json'), 'utf8'));
    assert(Object.keys(snapshot.sources).every(id => attribution.sources[id]?.license_url), 'Content attribution is incomplete.');
    assert(fs.readFileSync(path.join(root, '_headers'), 'utf8').includes('Link: </content-attribution.json>'), 'Download attribution header is missing.');
  }
  assert.deepEqual([...new Set(errors)], [], 'Source rights policy rejected the candidate; inspect privately.');
  return {status: 'passed', stories: snapshot.stories.length, sources: Object.keys(snapshot.sources).length, policy: 'licensed descriptive metadata and attributed documentation only'};
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) console.log(JSON.stringify(verifyContentRights(process.argv.includes('--snapshot-only') ? '.cache/no-build-content-check' : undefined), null, 2));
