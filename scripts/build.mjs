import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { withGenerationLock } from './generation-state.mjs';
import { readSnapshot } from './read-snapshot.mjs';
import { verifyContentRights } from './content-rights.mjs';
import { verifyGovernance } from './governance-preflight.mjs';

const pnpm = process.env.npm_execpath;
assert(!process.env.TECHLINE_RESEARCH_REHEARSAL, 'The ordinary build does not accept the research rehearsal profile.');
assert(!process.env.TECHLINE_RESEARCH_CANDIDATE, 'Use the isolated research candidate build.');
assert(pnpm && /pnpm\.(?:c?js)$/.test(pnpm), 'Run this supported build through pnpm build.');
withGenerationLock('.', env => {
  // Preflight is inside the shared lock. The lock owner may read here, too.
  process.env.TECHLINE_BUILD_TOKEN = env.TECHLINE_BUILD_TOKEN;
  if (readSnapshot('content/generated/snapshot.json').mode === 'live') verifyContentRights('.cache/no-build-content-check');
  verifyGovernance();
  for (const args of [
    ['scripts/third-party-notices.mjs', '--check'],
    [pnpm, '--filter', '@intelligence/web', 'build'],
    ['scripts/postbuild.mjs'],
    [pnpm, 'exec', 'pagefind', '--site', 'apps/web/dist'],
    ['scripts/build-provenance.mjs'],
  ]) execFileSync(process.execPath, args, {env, stdio:'inherit'});
  // Risk-reducing ledger writes during a build must invalidate its completion.
  verifyGovernance();
});
