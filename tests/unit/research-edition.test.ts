import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';
import { rehearsalSnapshot, recordKind, researchPolicy } from '../../scripts/research-policy.mjs';
import { researchEligibility, consistentEligibilityReport, approvedResearchSnapshot } from '../../scripts/research-inventory.mjs';
import { provenanceErrors } from '../../scripts/build-provenance.mjs';
import { editorialQuality } from '../../scripts/editorial-quality.mjs';

const source = {id:'one', title:'Synthetic paper', source_registry_id:'arxiv', source_type:'arxiv', is_demo:true,
  original_url:'https://example.com/research', canonical_url:'https://example.com/research', excerpt:'Synthetic preprint evidence. '.repeat(5), source_class:'primary'};
const story = {id:'research', slug:'research-example', category:'research', source_ids:['one'], primary_source_id:'one',
  key_facts:[], key_numbers:[], change_log:[], translations:{}, is_demo:true, headline:'Synthetic paper',
  importance_score_internal:1, published_at:'2026-10-20T00:00:00Z'};
const fixture = {mode:'fixture', sources:{one:source}, stories:[story], archive_index:[{key:'2020-01'}],
  digests:[{summary:'EXCLUDED_AGGREGATE'}], offers:[{title:'EXCLUDED_OFFER'}], model_releases:[{model:'EXCLUDED_MODEL'}]};

describe('research edition isolation', () => {
  it('requires actual synthetic mode and source provenance, even with forged reviewer fields', () => {
    expect(() => rehearsalSnapshot({...fixture, mode:'live'})).toThrow('live content is forbidden');
    expect(() => rehearsalSnapshot({...fixture, stories:[{...story,is_demo:false,review_status:'approved'}]})).toThrow('synthetic');
    expect(() => rehearsalSnapshot({...fixture, sources:{one:{...source,original_url:'https://arxiv.org/abs/real'}}})).toThrow('reserved example URLs');
    expect(() => rehearsalSnapshot({...fixture, sources:{one:{...source,canonical_url:'https://arxiv.org/abs/real'}}})).toThrow('reserved example URLs');
    expect(() => rehearsalSnapshot({...fixture, sources:{one:{...source,rights_review:{reviewer:'private'}}}})).toThrow('no private review evidence');
    expect(() => rehearsalSnapshot({...fixture, sources:{one:{...source,is_demo:false}}})).toThrow('synthetic');
  });
  it('removes unrelated content and all precomputed aggregate prose without modifying input', () => {
    const input = {...fixture, stories:[story,{...story,id:'news',category:'ai',source_ids:['excluded']}],
      sources:{one:source,excluded:{...source,id:'excluded',original_url:'https://example.com/excluded'}}};
    const before = JSON.stringify(input);
    const selected = rehearsalSnapshot(input);
    expect(selected.stories.map(row => row.id)).toEqual(['research']);
    expect(Object.keys(selected.sources)).toEqual(['one']);
    for (const key of ['digests','offers','model_releases','archive_index']) expect(selected[key]).toEqual([]);
    expect(JSON.stringify(selected)).not.toContain('EXCLUDED_');
    expect(JSON.stringify(input)).toBe(before);
  });
  it('retains correction evidence and refuses dangling history citations', () => {
    const changed = {...story,change_log:[{source_ids:['missing'],previous_facts:[]}]};
    expect(() => rehearsalSnapshot({...fixture,stories:[changed]})).toThrow('evidence is incomplete');
  });
  it('never treats source-level permission, copied approvals or policy switches as item authorization', () => {
    const live = {...fixture,mode:'live',sources:{one:{...source,is_demo:false}},stories:[{...story,is_demo:false,reviewer:'owner',publication_approved:true}]};
    const result = researchEligibility(live);
    expect(result.eligible_count).toBe(0);
    expect(result.publication_allowed).toBe(false);
    expect(result.excluded[0].reasons.some(reason => reason.startsWith('research-verifier-refused:'))).toBe(true);
    expect(researchPolicy.publication_enabled).toBe(false);
    expect(researchPolicy.approval_adapter).toBe('editorial-authority-research-v1');
  });
  it('rejects internally inconsistent Python eligibility reports before selecting anything', () => {
    const snapshot = {stories:[{id:'a'},{id:'b'}]};
    const row = (id, allowed) => ({id,publication_allowed:allowed,reasons:[]});
    const report = {policy:researchPolicy.policy,record_count:2,eligible_count:0,publication_allowed:false,
      ai_submission_allowed:false,items:[row('a',false),row('b',false)],eligible:[]};
    expect(consistentEligibilityReport(report, snapshot)).toBe(true);
    expect(consistentEligibilityReport({...report,policy:'another-policy'},snapshot)).toBe(false);
    expect(consistentEligibilityReport({...report,record_count:1},snapshot)).toBe(false);
    expect(consistentEligibilityReport({...report,items:[row('b',false),row('a',false)]},snapshot)).toBe(false);
    expect(consistentEligibilityReport({...report,items:[row('a',true),row('b',false)],eligible:['a'],
      eligible_count:1,publication_allowed:true},snapshot)).toBe(true);
    expect(consistentEligibilityReport({...report,items:[row('a',false),row('b',false)],eligible:['a'],
      eligible_count:1,publication_allowed:true},snapshot)).toBe(false);
    expect(consistentEligibilityReport({...report,eligible:['a','a'],eligible_count:2,
      publication_allowed:true},snapshot)).toBe(false);
    expect(consistentEligibilityReport({...report,items:[row('a',true),row('b',false)],eligible:[],
      publication_allowed:false},snapshot)).toBe(false);
    expect(consistentEligibilityReport({...report,ai_submission_allowed:true},snapshot)).toBe(false);
    expect(consistentEligibilityReport({...report,items:[row('a',false),row('a',false)]}, {stories:[{id:'a'},{id:'a'}]})).toBe(false);
  });
  it('projects only verified items and their evidence into every research route and aggregate', () => {
    const live = {...fixture,mode:'live',schema_version:1,generated_at:'2026-10-20T00:00:00Z',
      private_note:'MUST_NOT_LEAK',stories:[{...story,is_demo:false},{...story,id:'excluded',headline:'MUST_NOT_LEAK'}],
      sources:{one:{...source,is_demo:false},excluded:{...source,id:'excluded',title:'MUST_NOT_LEAK'}}};
    // Projection fixture only: this report is never used as real authority.
    const report = {policy:researchPolicy.policy,record_count:2,eligible_count:1,publication_allowed:true,
      ai_submission_allowed:false,eligible:['research'],items:[{id:'research',publication_allowed:true,reasons:[]},
        {id:'excluded',publication_allowed:false,reasons:['no-approval']}]};
    const selected = approvedResearchSnapshot(live,report);
    expect(selected.stories.map(row => row.id)).toEqual(['research']);
    expect(Object.keys(selected.sources)).toEqual(['one']);
    expect(JSON.stringify(selected)).not.toContain('MUST_NOT_LEAK');
    for (const key of ['digests','offers','model_releases','archive_index']) expect(selected[key]).toEqual([]);
    expect(() => approvedResearchSnapshot({...live,mode:'fixture'},report)).toThrow('live');
    expect(() => approvedResearchSnapshot(live,{...report,eligible_count:0})).toThrow('Malformed');
    for (const value of [{internal_only:true},{provenance:{private:'held'}},{rights_review:{status:'pending'}},{is_demo:true}]) {
      expect(() => approvedResearchSnapshot({...live,sources:{one:{...live.sources.one,...value}}},report)).toThrow('private');
    }
    const dangling = {...live,stories:[{...live.stories[0],key_facts:[{source_ids:['excluded']}]},live.stories[1]]};
    expect(() => approvedResearchSnapshot(dangling,report)).toThrow('Unapproved');
    const claimed = {...live,stories:[{...live.stories[0],claim_map:[{source_ids:['excluded']}]},live.stories[1]]};
    expect(() => approvedResearchSnapshot(claimed,report)).toThrow('Unapproved');
  });
  it('keeps real candidate mode blocked by default policy and rejects mixed profiles', () => {
    const script = "import {readBuildSnapshot} from './scripts/research-policy.mjs'; readBuildSnapshot('content/generated/snapshot.json');";
    const run = (extra = {}) => spawnSync(process.execPath,['--input-type=module','-e',script],{
      encoding:'utf8',env:{...process.env,TECHLINE_RESEARCH_CANDIDATE:'true',TECHLINE_RESEARCH_REHEARSAL:'',...extra}});
    expect(run().status).not.toBe(0);
    expect(run().stderr).toContain('disabled by owner policy');
    expect(run({TECHLINE_RESEARCH_REHEARSAL:'true'}).stderr).toContain('cannot be combined');
  });
  it('resolves the same authority bridge when Astro runs inside apps/web', () => {
    const script = `import {researchEligibility} from '../../scripts/research-inventory.mjs'; console.log(JSON.stringify(researchEligibility(${JSON.stringify(fixture)})));`;
    const result = spawnSync(process.execPath,['--input-type=module','-e',script],{cwd:'apps/web',encoding:'utf8'});
    expect(result.status).toBe(0);
    // Exact snapshot mismatch or missing clean-checkout snapshot is expected;
    // an unavailable interpreter/import is not an acceptable bridge result.
    expect(result.stdout).not.toContain('research-verifier-refused:unavailable');
    expect(JSON.parse(result.stdout).publication_allowed).toBe(false);
  });
  it('removes stale candidate assets when a new authorization preflight refuses', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(),'techline-research-refusal-'));
    try {
      fs.mkdirSync(path.join(root,'apps/web/dist-research'),{recursive:true});
      fs.mkdirSync(path.join(root,'content/generated'),{recursive:true});
      fs.writeFileSync(path.join(root,'apps/web/dist-research/previous.html'),'STALE_APPROVED_BYTES');
      fs.writeFileSync(path.join(root,'content/generated/snapshot.json'),JSON.stringify({...fixture,mode:'live'}));
      const result = spawnSync(process.execPath,[path.resolve('scripts/research-build.mjs')],{
        cwd:root,encoding:'utf8',env:{...process.env,npm_execpath:'test-pnpm.cjs',
          TECHLINE_RESEARCH_REHEARSAL:'',TECHLINE_RESEARCH_CANDIDATE:''}});
      expect(result.status).not.toBe(0);
      expect(result.stderr).toContain('live content is forbidden');
      expect(fs.existsSync(path.join(root,'apps/web/dist-research'))).toBe(false);
    } finally {
      fs.rmSync(root,{recursive:true,force:true});
    }
  });
  it('does not classify unknown sources or ordinary news as research/reference', () => {
    expect(recordKind(story,{one:source})).toBe('research');
    expect(recordKind({...story,category:'ai'},{one:source})).toBe('out-of-scope');
    expect(recordKind(story,{one:{...source,source_registry_id:'unknown'}})).toBe('out-of-scope');
    expect(recordKind(story,{})).toBe('out-of-scope');
    expect(recordKind(story,{one:{...source,source_registry_id:'cloudflare_ai_terms',source_type:'github_document'}})).toBe('reference');
  });
  it('binds output profile in provenance and retains the existing news gate', () => {
    expect(provenanceErrors({profile:'research-rehearsal'},{profile:'standard'})).toContain('Build provenance mismatch: profile; rebuild the current live edition.');
    const live = {...fixture,mode:'live',generated_at:'2026-10-21T00:00:00Z',last_successful_fetch_at:'2026-10-21T00:00:00Z',
      stories:[{...story,is_demo:false}],sources:{one:{...source,is_demo:false,source_type:'arxiv'}}};
    expect(editorialQuality(live,{production:true,now:Date.parse('2026-10-21T00:00:00Z')}).errors.join(' ')).toContain('Research and reference documents do not satisfy this gate');
  });
  it('rejects analytics/environment injection before building and keeps deploy scripts unchanged', () => {
    const result = spawnSync(process.execPath,['scripts/research-build.mjs'],{encoding:'utf8',env:{...process.env,PUBLIC_RESEARCH_SENTINEL:'must-never-ship'}});
    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain('forbid public environment injection');
    const scripts = JSON.parse(fs.readFileSync('package.json','utf8')).scripts;
    expect(scripts['deploy:preview']).toContain('scripts/editorial-quality.mjs --production');
    expect(scripts.deploy).toContain('scripts/release-gate.mjs --publish');
    const worker = JSON.parse(fs.readFileSync('wrangler.research-preview.jsonc','utf8'));
    expect(worker.assets.directory).toBe('./apps/web/dist-research');
    expect(worker.assets.run_worker_first).toBe(false);
    expect(worker.preview_urls).toBe(false);
    expect(worker.main).toBeUndefined();
    expect(Object.keys(worker).sort()).toEqual(['$schema','assets','compatibility_date','name','preview_urls','workers_dev']);
  });
});
