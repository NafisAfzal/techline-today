import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { siteUrl } from './site-url.mjs';

export function githubErrors(plan, runtime) {
  const errors = [];
  if (plan.github_publication_approved !== true) errors.push('Gate A: public GitHub publication is not authorized.');
  if (plan.public_files_reviewed !== true) errors.push('Gate A: public files are not reviewed.');
  if (plan.content_rights_reviewed !== true) errors.push('Gate A: content redistribution review is incomplete.');
  if (plan.durable_backup_verified !== true) errors.push('Gate A: independent backup restoration is unverified.');
  if (plan.source_ownership_confirmed !== true || plan.source_code_license !== 'MIT') errors.push('Gate A: original-code ownership/MIT license is incomplete.');
  if (plan.visibility !== 'public' || !/^[\w-]+\/[\w.-]+$/.test(plan.github_repository || '')) errors.push('Gate A: exact public repository is missing.');
  if (plan.github_repository?.split('/')[0] !== runtime.authenticatedLogin) errors.push('Gate A: authenticated personal owner does not match.');
  if (plan.brand_reviewed !== true) errors.push('Gate A: working-name risk needs the owner decision.');
  if (!/^[a-f0-9]{40}$/.test(runtime.approvedRevision || '') || runtime.approvedRevision !== runtime.revision) errors.push('Gate A: reviewed commit is not approved.');
  return errors;
}

export function releaseErrors(plan, runtime) {
  const errors = [];
  const preview = runtime.target === 'preview';
  if (plan.github_publication_approved !== true) errors.push('Gate A: public GitHub publication is not authorized.');
  if (plan.public_files_reviewed !== true) errors.push('Gate A: the public file inventory is unreviewed.');
  if (preview ? plan.preview_approved !== true : plan.approved !== true) errors.push(preview ? 'Gate B: Cloudflare preview is not authorized.' : 'Gate C: public production launch is not authorized.');
  if (!preview && plan.preview_verified !== true) errors.push('Gate C: hosted preview has not passed.');
  if (plan.hosted_ci_verified !== true) errors.push('Hosted CI has not passed.');
  if (plan.free_plan_verified !== true || plan.zero_spend_verified !== true) errors.push('Cloudflare Free plan and account zero-spend controls are unverified.');
  if (!/^[\w-]+\/[\w.-]+$/.test(plan.github_repository || '')) errors.push('Exact GitHub owner/repository is missing.');
  if (!['public', 'private'].includes(plan.visibility)) errors.push('Repository visibility is unapproved.');
  if (plan.github_repository !== runtime.repository) errors.push('Intended repository does not match the release plan.');
  const worker = preview ? plan.preview_worker_name : plan.worker_name;
  if (preview && (worker === plan.worker_name || plan.preview_site_url === plan.site_url)) errors.push('Gate B: preview must use a separate Worker and origin from production.');
  if (worker !== runtime.worker || !/^[a-z0-9][a-z0-9-]+$/.test(worker || '')) errors.push('Cloudflare Worker destination differs from the approved plan.');
  if (!/^[a-f0-9]{32}$/.test(plan.cloudflare_account_id || '') || plan.cloudflare_account_id !== runtime.account) errors.push('Exact Cloudflare account is unapproved or mismatched.');
  const origin = preview ? plan.preview_site_url : plan.site_url;
  try { siteUrl(origin, { production: true }); } catch { errors.push('An approved public HTTPS origin is required.'); }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(plan.workers_dev_subdomain || '') || origin !== `https://${worker}.${plan.workers_dev_subdomain}.workers.dev`) errors.push('The initial origin must match the selected Worker and confirmed account workers.dev subdomain.');
  if (origin !== runtime.origin) errors.push('SITE_URL differs from the approved origin.');
  if (!Number.isFinite(plan.monthly_cost_ceiling_usd) || plan.monthly_cost_ceiling_usd < 0) errors.push('Operational cost ceiling is missing.');
  if (!['MIT', 'Apache-2.0', 'BSD-3-Clause', 'Proprietary'].includes(plan.source_code_license)) errors.push('Source-code ownership/license decision is pending.');
  if (plan.source_ownership_confirmed !== true) errors.push('Source-code ownership has not been confirmed.');
  if (plan.brand_reviewed !== true) errors.push('Brand collision review requires an owner decision.');
  if (plan.content_rights_reviewed !== true) errors.push('News-content redistribution review is pending.');
  if (!preview && plan.durable_backup_verified !== true) errors.push('Off-machine backup and restoration are unverified.');
  if (!/^[a-f0-9]{40}$/.test(runtime.approvedRevision || '') || runtime.approvedRevision !== runtime.revision) errors.push('RELEASE_APPROVED_SHA does not identify the current approved revision.');
  if (!['local', 'workflow_dispatch', 'schedule'].includes(runtime.event)) errors.push('This event is not permitted to publish.');
  if (runtime.event === 'schedule' && plan.schedule_enabled !== true) errors.push('Recurring publication has not been approved.');
  if (preview && runtime.event === 'schedule') errors.push('Preview publication must be manually authorized.');
  if (runtime.aiEnabled) errors.push('Production AI/translation cost enforcement is unverified; inference must remain disabled.');
  if (!['public', 'private'].includes(runtime.visibility) || runtime.visibility !== plan.visibility) errors.push('Actual repository visibility is unverified or differs from approval.');
  if (runtime.seedRequested && (plan.initial_seed_authorized !== true || !runtime.allowInitialSeed || runtime.event !== 'workflow_dispatch')) errors.push('Missing production state requires an explicitly approved first seed or durable restoration.');
  return errors;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const plan = JSON.parse(fs.readFileSync('config/release.json', 'utf8'));
  const target = process.argv.includes('--github') ? 'github' : process.argv.includes('--preview') ? 'preview' : 'production';
  const worker = JSON.parse(fs.readFileSync(target === 'preview' ? 'wrangler.preview.jsonc' : 'wrangler.jsonc', 'utf8')).name;
  const git = (...args) => { try { return execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch { return ''; } };
  const remote = git('config', '--get', 'remote.origin.url');
  const repository = process.env.GITHUB_REPOSITORY || remote.match(/github\.com[:/]([^/]+\/[^/]+?)(?:\.git)?$/)?.[1];
  const event = process.env.GITHUB_EVENT_PATH ? JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8')) : null;
  let visibility = event?.repository ? event.repository.private ? 'private' : 'public' : undefined;
  const dirty = git('status', '--porcelain', '--untracked-files=normal');
  if (!dirty && !event && (target === 'preview' ? plan.preview_approved : plan.approved) === true && process.argv.includes('--publish') && /^[\w-]+\/[\w.-]+$/.test(repository || '')) {
    try {
      const actual = JSON.parse(execFileSync('gh', ['repo', 'view', repository, '--json', 'nameWithOwner,visibility'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }));
      if (actual.nameWithOwner === repository) visibility = actual.visibility.toLowerCase();
    } catch { /* Fail closed without actual repository evidence. */ }
  }
  const errors = releaseErrors(plan, { target, repository, worker, account: process.env.CLOUDFLARE_ACCOUNT_ID, origin: process.env.SITE_URL, revision: process.env.GITHUB_SHA || git('rev-parse', 'HEAD'), approvedRevision: process.env.RELEASE_APPROVED_SHA, event: process.env.GITHUB_EVENT_NAME || 'local', aiEnabled: process.env.PIPELINE_AI_ENABLED === 'true', visibility, seedRequested:process.argv.includes('--seed'), allowInitialSeed:process.env.ALLOW_INITIAL_SEED === 'true' });
  if (target === 'github') {
    let authenticatedLogin;
    if (plan.github_publication_approved === true && process.argv.includes('--publish')) {
      try { authenticatedLogin = JSON.parse(execFileSync('gh', ['api', 'user'], {encoding:'utf8', stdio:['ignore','pipe','ignore']})).login; } catch { /* No credential details in output. */ }
    }
    errors.splice(0, errors.length, ...githubErrors(plan, {authenticatedLogin, revision:git('rev-parse','HEAD'), approvedRevision:process.env.RELEASE_APPROVED_SHA}));
  }
  if (dirty) errors.push('The release working tree contains uncommitted/untracked files.');
  if (process.env.GITHUB_SHA && process.env.GITHUB_SHA !== git('rev-parse', 'HEAD')) errors.push('Checked-out HEAD differs from the claimed workflow revision.');
  if (plan.source_code_license && plan.source_code_license !== 'Proprietary' && !fs.existsSync('LICENSE')) errors.push('The approved open-source license text is missing.');
  console.log(JSON.stringify({ gate: errors.length ? 'RELEASE_APPROVAL_REQUIRED' : 'APPROVED', publicationPerformed: false, errors }, null, 2));
  if (process.argv.includes('--publish') && errors.length) process.exitCode = 1;
}
