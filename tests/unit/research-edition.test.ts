import fs from 'node:fs';
import { spawnSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';
import { rehearsalSnapshot, recordKind, researchPolicy } from '../../scripts/research-policy.mjs';
import { researchEligibility } from '../../scripts/research-inventory.mjs';
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
