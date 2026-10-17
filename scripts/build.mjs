import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { withGenerationLock } from './generation-state.mjs';
import { readSnapshot } from './read-snapshot.mjs';
import { verifyContentRights } from './content-rights.mjs';

const pnpm = process.env.npm_execpath;
assert(pnpm && /pnpm\.(?:c?js)$/.test(pnpm), 'Run this supported build through pnpm build.');
withGenerationLock('.', env => {
  // Preflight is inside the shared lock. The lock owner may read here, too.
  process.env.TECHLINE_BUILD_TOKEN = env.TECHLINE_BUILD_TOKEN;
  if (readSnapshot('content/generated/snapshot.json').mode === 'live') verifyContentRights('.cache/no-build-content-check');
  for (const args of [
    ['scripts/third-party-notices.mjs', '--check'],
    [pnpm, '--filter', '@intelligence/web', 'build'],
    ['scripts/postbuild.mjs'],
    [pnpm, 'exec', 'pagefind', '--site', 'apps/web/dist'],
    ['scripts/build-provenance.mjs'],
  ]) execFileSync(process.execPath, args, {env, stdio:'inherit'});
});
