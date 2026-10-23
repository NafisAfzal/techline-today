import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { withGenerationLock } from './generation-state.mjs';
import { readSnapshot } from './read-snapshot.mjs';
import { rehearsalSnapshot } from './research-policy.mjs';
import { approvedResearchSnapshot, researchEligibility } from './research-inventory.mjs';

const real = process.argv.includes('--real');
assert(process.argv.slice(2).every(arg => arg === '--real'), 'Only --real is supported; this command never publishes.');

assert(!Object.entries(process.env).some(([key, value]) => key.startsWith('PUBLIC_') && value), 'Research builds forbid public environment injection, including analytics.');
const pnpm = process.env.npm_execpath;
assert(pnpm && /pnpm\.(?:c?js)$/.test(pnpm), 'Run through pnpm build:research.');
for (const directory of ['.', 'apps/web']) {
  assert(!fs.readdirSync(directory).some(name => /^\.env(?:\.|$)/.test(name) && name !== '.env.example'), 'Remove local dotenv files from this isolated rehearsal worktree.');
}
withGenerationLock('.', inherited => {
  process.env.TECHLINE_BUILD_TOKEN = inherited.TECHLINE_BUILD_TOKEN;
  const output = path.resolve('apps/web/dist-research');
  assert.equal(path.dirname(output), path.resolve('apps/web'));
  // A refused rebuild must not leave old eligible bytes looking current.
  fs.rmSync(output, {recursive:true, force:true});
  try {
  const raw = readSnapshot('content/generated/snapshot.json');
  if (real) approvedResearchSnapshot(raw, researchEligibility(raw));
  else rehearsalSnapshot(raw);
  const env = {...inherited, TECHLINE_RESEARCH_REHEARSAL:real ? '' : 'true', TECHLINE_RESEARCH_CANDIDATE:real ? 'true' : '', SITE_NOINDEX:'true', PIPELINE_AI_ENABLED:'false',
    WRANGLER_SEND_METRICS:'false', ASTRO_TELEMETRY_DISABLED:'1'};
  for (const key of Object.keys(env)) if (/(?:TOKEN|SECRET|API_KEY|ACCOUNT_ID)$/.test(key)
    && !['TECHLINE_BUILD_TOKEN','TECHLINE_CUSTODIAN_RUN_TOKEN'].includes(key)) delete env[key];
  for (const args of [
    ['scripts/third-party-notices.mjs', '--check'], [pnpm, '--filter', '@intelligence/web', 'build'],
    ['scripts/postbuild.mjs'], [pnpm, 'exec', 'pagefind', '--site', output],
    ['scripts/build-provenance.mjs'], ['scripts/verify-research.mjs'],
  ]) execFileSync(process.execPath, args, {env, stdio:'inherit'});
  // Revocation, STOP, rights withdrawal or a changed head invalidate completion.
  if (real) approvedResearchSnapshot(readSnapshot('content/generated/snapshot.json'), researchEligibility(raw));
  } catch (error) {
    fs.rmSync(output, {recursive:true, force:true});
    throw error;
  }
});
