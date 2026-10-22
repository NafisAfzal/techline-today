import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { contentRightsErrors } from './content-rights.mjs';
import { readSnapshot } from './read-snapshot.mjs';
import { researchPolicy, recordKind } from './research-policy.mjs';

// Diagnostics never infer approval from a rights allowlist or legacy digest.
export function researchEligibility(snapshot) {
  const rightsFailures = contentRightsErrors(snapshot);
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const verification = spawnSync(python, ['-m', 'pipeline.research_cli', 'select-stdin'], {
    input: JSON.stringify(snapshot), encoding: 'utf8', maxBuffer: 8 * 1024 * 1024, timeout: 60000,
  });
  // Run the verifier for this exact snapshot every time. Never accept a cached
  // readiness JSON or mutable reviewer fields as permission.
  let report;
  try { report = JSON.parse(verification.stdout); } catch { /* Fail closed below. */ }
  if (verification.status === 0 && report?.policy === researchPolicy.policy && Array.isArray(report.items)
      && report.record_count === snapshot.stories.length && report.items.every((row, index) => row.id === snapshot.stories[index].id)) {
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
