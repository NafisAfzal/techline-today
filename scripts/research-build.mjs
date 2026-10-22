import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { withGenerationLock } from './generation-state.mjs';
import { readSnapshot } from './read-snapshot.mjs';
import { rehearsalSnapshot } from './research-policy.mjs';

const pnpm = process.env.npm_execpath;
assert(pnpm && /pnpm\.(?:c?js)$/.test(pnpm), 'Run through pnpm build:research.');
assert(!Object.entries(process.env).some(([key, value]) => key.startsWith('PUBLIC_') && value), 'Research builds forbid public environment injection, including analytics.');
for (const directory of ['.', 'apps/web']) {
  assert(!fs.readdirSync(directory).some(name => /^\.env(?:\.|$)/.test(name) && name !== '.env.example'), 'Remove local dotenv files from this isolated rehearsal worktree.');
}
withGenerationLock('.', inherited => {
  process.env.TECHLINE_BUILD_TOKEN = inherited.TECHLINE_BUILD_TOKEN;
  rehearsalSnapshot(readSnapshot('content/generated/snapshot.json'));
  const env = {...inherited, TECHLINE_RESEARCH_REHEARSAL:'true', SITE_NOINDEX:'true', PIPELINE_AI_ENABLED:'false',
    WRANGLER_SEND_METRICS:'false', ASTRO_TELEMETRY_DISABLED:'1'};
  for (const key of Object.keys(env)) if (/(?:TOKEN|SECRET|API_KEY|ACCOUNT_ID)$/.test(key) && key !== 'TECHLINE_BUILD_TOKEN') delete env[key];
  const output = path.resolve('apps/web/dist-research');
  assert.equal(path.dirname(output), path.resolve('apps/web'));
  fs.rmSync(output, {recursive:true, force:true});
  for (const args of [
    ['scripts/third-party-notices.mjs', '--check'], [pnpm, '--filter', '@intelligence/web', 'build'],
    ['scripts/postbuild.mjs'], [pnpm, 'exec', 'pagefind', '--site', output],
    ['scripts/build-provenance.mjs'], ['scripts/verify-research.mjs'],
  ]) execFileSync(process.execPath, args, {env, stdio:'inherit'});
});
