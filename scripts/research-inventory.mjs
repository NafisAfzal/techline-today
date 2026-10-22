import { pathToFileURL } from 'node:url';
import { contentRightsErrors } from './content-rights.mjs';
import { readSnapshot } from './read-snapshot.mjs';
import { researchPolicy, recordKind } from './research-policy.mjs';

// Diagnostics never infer approval from a rights allowlist or legacy digest.
export function researchEligibility(snapshot) {
  const rightsFailures = contentRightsErrors(snapshot);
  const excluded = snapshot.stories.map(story => ({
    id: story.id, kind: recordKind(story, snapshot.sources),
    reasons: [...(rightsFailures.length ? ['rights-or-provenance-review-required'] : []),
      ...(recordKind(story, snapshot.sources) === 'out-of-scope' ? ['outside-research-reference-scope'] : []),
      'no-verified-item-publication-decision', 'no-current-trusted-research-checkpoint', 'research-approval-adapter-unavailable'],
  }));
  return {policy: researchPolicy.policy, eligible: [], eligible_count: 0, excluded,
    publication_allowed: false, ai_submission_allowed: false};
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log(JSON.stringify(researchEligibility(readSnapshot(process.argv[2] || 'content/generated/snapshot.json')), null, 2));
}
