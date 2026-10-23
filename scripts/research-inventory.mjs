import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { contentRightsErrors } from './content-rights.mjs';
import { readSnapshot } from './read-snapshot.mjs';
import { researchPolicy, recordKind } from './research-policy.mjs';

// The Python verifier is the selector, but its report must be internally
// consistent before JavaScript will use any eligible ID. This is defense in
// depth against a stale/malformed report, not a second rights decision.
export function consistentEligibilityReport(report, snapshot) {
  if (!report || report.policy !== researchPolicy.policy || !Array.isArray(report.items)
      || !Array.isArray(report.eligible) || report.record_count !== snapshot.stories.length
      || report.record_count !== report.items.length || report.eligible_count !== report.eligible.length
      || !report.items.every((row, index) => row && row.id === snapshot.stories[index].id
        && typeof row.publication_allowed === 'boolean' && Array.isArray(row.reasons))) return false;
  const allowed = report.items.filter(row => row.publication_allowed === true).map(row => row.id);
  if (JSON.stringify(allowed) !== JSON.stringify(report.eligible)) return false;
  if (new Set(report.eligible).size !== report.eligible.length) return false;
  if (new Set(snapshot.stories.map(row => row.id)).size !== snapshot.stories.length) return false;
  if (report.publication_allowed !== (report.eligible.length > 0)) return false;
  if (report.ai_submission_allowed !== false) return false;
  return true;
}

// Internal build projection. Only call with the freshly recomputed verifier
// result, never with an operator-supplied manifest or packet.
export function approvedResearchSnapshot(snapshot, report) {
  assert.equal(snapshot.mode, 'live', 'Real research candidates require live canonical input.');
  assert(consistentEligibilityReport(report, snapshot), 'Malformed research eligibility result.');
  assert(report.publication_allowed && report.eligible_count > 0, 'No authenticated research items are eligible.');
  const selected = new Set(report.eligible);
  const stories = snapshot.stories.filter(story => selected.has(story.id));
  assert(stories.every(story => story.is_demo === false && recordKind(story, snapshot.sources) !== 'out-of-scope'), 'Invalid real research classification.');
  const cited = new Set(stories.flatMap(story => [...story.source_ids,
    ...story.key_facts.flatMap(fact => fact.source_ids), ...story.key_numbers.flatMap(number => number.source_ids),
    ...(story.claim_map || []).flatMap(fact => fact.source_ids),
    ...story.change_log.flatMap(change => [...change.source_ids, ...change.previous_facts.flatMap(fact => fact.source_ids)])]));
  const admitted = new Set(stories.flatMap(story => story.source_ids));
  assert([...cited].every(id => admitted.has(id) && snapshot.sources[id]?.is_demo === false
    && !snapshot.sources[id].internal_only && snapshot.sources[id].provenance == null
    && snapshot.sources[id].rights_review == null), 'Unapproved or private research evidence cannot enter assets.');
  // Explicit projection prevents precomputed news/archives and future private
  // top-level properties from crossing this boundary.
  return {schema_version:snapshot.schema_version, mode:snapshot.mode,
    generated_at:snapshot.generated_at, last_successful_fetch_at:snapshot.last_successful_fetch_at,
    categories:snapshot.categories, stories,
    sources:Object.fromEntries([...cited].map(id => [id, snapshot.sources[id]])),
    digests:[], offers:[], model_releases:[], archive_index:[]};
}

// Diagnostics never infer approval from a rights allowlist or legacy digest.
export function researchEligibility(snapshot, {root = fileURLToPath(new URL('../', import.meta.url))} = {}) {
  const rightsFailures = contentRightsErrors(snapshot);
  const python = path.resolve(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const verification = spawnSync(python, ['-m', 'pipeline.research_cli', 'select-stdin'], {
    cwd:root, input: JSON.stringify(snapshot), encoding: 'utf8', maxBuffer: 8 * 1024 * 1024, timeout: 60000,
  });
  // Run the verifier for this exact snapshot every time. Never accept a cached
  // readiness JSON or mutable reviewer fields as permission.
  let report;
  try { report = JSON.parse(verification.stdout); } catch { /* Fail closed below. */ }
  if (verification.status === 0 && consistentEligibilityReport(report, snapshot)) {
    if (rightsFailures.length) return {...report, eligible: [], eligible_count: 0, publication_allowed: false,
      excluded: report.items.map(row => ({...row, publication_allowed:false,
        reasons:[...row.reasons, 'rights-or-provenance-review-required']}))};
    return report;
  }
  const excluded = snapshot.stories.map(story => ({
    id: story.id, kind: recordKind(story, snapshot.sources),
    reasons: [...(rightsFailures.length ? ['rights-or-provenance-review-required'] : []),
      ...(recordKind(story, snapshot.sources) === 'out-of-scope' ? ['outside-research-reference-scope'] : []),
      'no-verified-item-publication-decision', 'no-current-trusted-research-checkpoint',
      'research-verifier-refused:' + (report?.code || 'unavailable')],
  }));
  return {policy: researchPolicy.policy, eligible: [], eligible_count: 0, excluded,
    publication_allowed: false, ai_submission_allowed: false};
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log(JSON.stringify(researchEligibility(readSnapshot(process.argv[2] || 'content/generated/snapshot.json')), null, 2));
}
