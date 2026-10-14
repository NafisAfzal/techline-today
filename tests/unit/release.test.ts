import { describe, it, expect } from 'vitest';
import { releaseErrors, githubErrors } from '../../scripts/release-gate.mjs';
import { editorialQuality } from '../../scripts/editorial-quality.mjs';
import { provenanceErrors } from '../../scripts/build-provenance.mjs';
const revision = 'a'.repeat(40);
const plan = {approved:true, github_publication_approved:true, public_files_reviewed:true, preview_approved:true, preview_verified:true, hosted_ci_verified:true, free_plan_verified:true, zero_spend_verified:true, preview_worker_name:'ai-tech-intelligence-preview', preview_site_url:'https://ai-tech-intelligence-preview.operator.workers.dev', workers_dev_subdomain:'operator', github_repository:'owner/techline-today', visibility:'public', worker_name:'ai-tech-intelligence', cloudflare_account_id:'b'.repeat(32), site_url:'https://ai-tech-intelligence.operator.workers.dev', monthly_cost_ceiling_usd:0, ai_enabled:false, schedule_enabled:false, source_code_license:'MIT', source_ownership_confirmed:true, brand_reviewed:true, content_rights_reviewed:true, durable_backup_verified:true};
const runtime = {repository:plan.github_repository, visibility:'public', worker:plan.worker_name, account:plan.cloudflare_account_id, origin:plan.site_url, revision, approvedRevision:revision, event:'workflow_dispatch', aiEnabled:false};
describe('release authorization', () => {
  it.each(['github_publication_approved','public_files_reviewed','content_rights_reviewed','durable_backup_verified'])('blocks Gate A without %s', key => {
    expect(githubErrors({...plan,[key]:false},{authenticatedLogin:'owner',revision,approvedRevision:revision})).not.toEqual([]);
  });
  it('accepts only a concrete approved release', () => expect(releaseErrors(plan,runtime)).toEqual([]));
  it.each(['approved','github_publication_approved','public_files_reviewed','preview_verified','hosted_ci_verified','free_plan_verified','zero_spend_verified','source_ownership_confirmed','brand_reviewed','content_rights_reviewed','durable_backup_verified'])('blocks missing %s', key => expect(releaseErrors({...plan,[key]:false},runtime).length).toBeGreaterThan(0));
  it('keeps GitHub, preview and production approvals separate', () => {
    expect(githubErrors({...plan,approved:false,preview_approved:false},{authenticatedLogin:'owner',revision,approvedRevision:revision})).toEqual([]);
    expect(githubErrors(plan,{authenticatedLogin:'different-owner',revision,approvedRevision:revision})).not.toEqual([]);
    const preview = {...runtime,target:'preview',worker:plan.preview_worker_name,origin:plan.preview_site_url};
    expect(releaseErrors({...plan,approved:false,preview_verified:false,durable_backup_verified:false},preview)).toEqual([]);
    expect(releaseErrors({...plan,preview_approved:false},preview)).not.toEqual([]);
    expect(releaseErrors({...plan,github_publication_approved:false},preview)).not.toEqual([]);
    expect(releaseErrors({...plan,approved:false},runtime)).not.toEqual([]);
  });
  it('prevents preview approval from replacing production or using a different account subdomain', () => {
    const collision = {...plan,preview_worker_name:plan.worker_name,preview_site_url:plan.site_url};
    expect(releaseErrors(collision,{...runtime,target:'preview'})).not.toEqual([]);
    expect(releaseErrors({...plan,workers_dev_subdomain:'another-account'},runtime)).not.toEqual([]);
  });
  it.each(['repository','worker','account','origin','revision','approvedRevision','visibility'])('blocks mismatched %s', key => expect(releaseErrors(plan,{...runtime,[key]:'wrong'}).length).toBeGreaterThan(0));
  it('rejects pull requests and unapproved recurring jobs', () => {
    expect(releaseErrors(plan,{...runtime,event:'pull_request'}).length).toBeGreaterThan(0);
    expect(releaseErrors(plan,{...runtime,event:'schedule'}).length).toBeGreaterThan(0);
  });
  it('requires a separate budget and approval for AI', () => {
    expect(releaseErrors(plan,{...runtime,aiEnabled:true}).length).toBeGreaterThan(0);
    expect(releaseErrors({...plan,ai_enabled:true,monthly_cost_ceiling_usd:5},{...runtime,aiEnabled:true}).length).toBeGreaterThan(0);
  });
  it('fails closed without actual visibility evidence', () => expect(releaseErrors(plan,{...runtime,visibility:undefined}).length).toBeGreaterThan(0));
  it('blocks cache loss unless an initial manual seed is explicitly approved', () => {
    expect(releaseErrors(plan,{...runtime,seedRequested:true,allowInitialSeed:true}).length).toBeGreaterThan(0);
    expect(releaseErrors({...plan,initial_seed_authorized:true},{...runtime,seedRequested:true,allowInitialSeed:true})).toEqual([]);
    expect(releaseErrors({...plan,initial_seed_authorized:true},{...runtime,event:'schedule',seedRequested:true,allowInitialSeed:true}).length).toBeGreaterThan(0);
  });
});
describe('build provenance', () => {
  const manifest = {version:1,revision,source_sha256:'source',snapshot_sha256:'snapshot',archive_sha256:'archives',mode:'live',generated_at:'now',assets_sha256:'assets'};
  it('accepts an identical source/snapshot/asset revision', () => expect(provenanceErrors(manifest,manifest)).toEqual([]));
  it.each(['revision','source_sha256','snapshot_sha256','archive_sha256','mode','generated_at','assets_sha256'])('rejects changed %s', key => expect(provenanceErrors(manifest,{...manifest,[key]:'changed'}).length).toBeGreaterThan(0));
});
describe('editorial publication guard', () => {
  const now = Date.parse('2026-10-14T00:00:00Z');
  const snapshot = {mode:'live',last_successful_fetch_at:new Date(now).toISOString(),stories:[{id:'one',headline:'Original source headline',source_ids:['source'],importance_score_internal:.8,published_at:new Date(now).toISOString(),is_demo:false}],sources:{source:{source_class:'primary',title:'Original source headline',excerpt:'The source describes a specific change with enough collected prose to support an editorial preview and factual review.',is_demo:false}}};
  it('accepts a fresh evidence-backed live edition', () => expect(editorialQuality(snapshot,{production:true,now}).errors).toEqual([]));
  it('rejects fixtures and stale live content', () => {
    expect(editorialQuality({...snapshot,mode:'fixture'},{production:true,now}).errors.length).toBeGreaterThan(0);
    expect(editorialQuality(snapshot,{production:true,now:now+25*3600000}).errors.length).toBeGreaterThan(0);
  });
  it('rejects headline-only prominence and broken citations', () => {
    expect(editorialQuality({...snapshot,sources:{source:{...snapshot.sources.source,excerpt:''}}},{production:true,now}).errors.length).toBeGreaterThan(0);
    expect(editorialQuality({...snapshot,sources:{}},{production:true,now}).errors.length).toBeGreaterThan(0);
  });
});
