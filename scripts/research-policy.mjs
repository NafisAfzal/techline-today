import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readSnapshot } from './read-snapshot.mjs';
import policy from '../config/research-edition.json' with {type:'json'};
import { approvedResearchSnapshot, researchEligibility } from './research-inventory.mjs';

export const researchPolicy = policy;
export const researchRehearsal = process.env.TECHLINE_RESEARCH_REHEARSAL === 'true';
export const researchCandidate = process.env.TECHLINE_RESEARCH_CANDIDATE === 'true';
assert(!(researchRehearsal && researchCandidate), 'Research profiles cannot be combined.');
export const researchEdition = researchRehearsal || researchCandidate;
export const buildDirectory = researchEdition ? 'apps/web/dist-research' : 'apps/web/dist';

export function recordKind(story, sources) {
  const evidence = story.source_ids.map(id => sources[id]);
  if (story.category === 'research' && evidence.length && evidence.every(source => source?.source_registry_id === 'arxiv')) return 'research';
  if (evidence.length && evidence.every(source => source?.source_registry_id === 'cloudflare_ai_terms' && source.source_type === 'github_document')) return 'reference';
  return 'out-of-scope';
}

export function rehearsalSnapshot(snapshot) {
  assert.equal(snapshot.mode, 'fixture', 'Research rehearsal requires isolated synthetic fixtures; live content is forbidden.');
  assert(snapshot.stories.length && snapshot.stories.every(story => story.is_demo === true), 'Every rehearsal story must be synthetic.');
  const exampleUrl = value => {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && !url.username && !url.password && !url.port && /(?:^|\.)example\.(?:com|org|net)$/.test(url.hostname);
    } catch { return false; }
  };
  assert(Object.values(snapshot.sources).every(source => source.is_demo === true && exampleUrl(source.original_url) && exampleUrl(source.canonical_url)
    && !source.internal_only && !Object.hasOwn(source,'provenance') && source.rights_review == null), 'Every rehearsal source must be synthetic with reserved example URLs and no private review evidence.');
  const stories = snapshot.stories.filter(story => story.category === 'research');
  assert(stories.length, 'No synthetic research examples available.');
  const cited = new Set(stories.flatMap(story => [...story.source_ids,
    ...story.key_facts.flatMap(fact => fact.source_ids), ...story.key_numbers.flatMap(number => number.source_ids),
    ...(story.claim_map || []).flatMap(fact => fact.source_ids),
    ...story.change_log.flatMap(change => [...change.source_ids, ...change.previous_facts.flatMap(fact => fact.source_ids)])]));
  assert([...cited].every(id => snapshot.sources[id]), 'Rehearsal evidence is incomplete.');
  // Drop every aggregate rather than carrying prose from excluded records.
  return {...snapshot, stories, sources: Object.fromEntries([...cited].map(id => [id, snapshot.sources[id]])),
    digests: [], offers: [], model_releases: [], archive_index: []};
}

export function readBuildSnapshot(file) {
  if (researchCandidate) assert.equal(policy.publication_enabled, true, 'Research publication remains disabled by owner policy.');
  const snapshot = readSnapshot(file);
  if (researchCandidate) {
    // Astro bundles this module into its prerender directory. Derive the
    // verifier root from the exact canonical input, never a bundled import URL.
    const input = path.resolve(file instanceof URL ? fileURLToPath(file) : file);
    const root = path.resolve(path.dirname(input), '../..');
    assert.equal(input, path.join(root, 'content/generated/snapshot.json'), 'Use the canonical repository snapshot.');
    return approvedResearchSnapshot(snapshot, researchEligibility(snapshot, {root}));
  }
  return researchRehearsal ? rehearsalSnapshot(snapshot) : snapshot;
}
