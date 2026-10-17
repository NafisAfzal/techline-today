import {describe, expect, it} from 'vitest';
import {contentRightsErrors} from '../../scripts/content-rights.mjs';
import {contentKind, coverage} from '../../scripts/coverage.mjs';
import {editorialQuality} from '../../scripts/editorial-quality.mjs';

const source = {source_registry_id:'cisa_kev',source_type:'json_api',source_class:'primary',
  editorial_kind:'security-advisory',published_at:null,missing_publication_time:true,
  fetched_at:'2026-10-16T10:00:00Z',title:'CVE-2026-1234: synthetic advisory',
  excerpt:'A synthetic vulnerability description and a required action, with sufficient prose for the editorial test.',
  advisory:{catalog_added_on:'2026-10-16',remediation_due_on:'2026-10-23'},is_demo:false};
const story = {id:'one',source_ids:['one'],change_log:[],translations:{},is_demo:false,
  category:'security',headline:source.title,published_at:'2026-10-16T10:00:00Z',importance_score_internal:0.8};
const snapshot = {mode:'live',stories:[story],sources:{one:source},
  generated_at:'2026-10-16T10:00:00Z',last_successful_fetch_at:'2026-10-16T10:00:00Z'};
const now = Date.parse('2026-10-16T12:00:00Z');

describe('disabled local pilot isolation', () => {
  it.each(['research_pytorch', 'research_nodejs', 'research_rust_releases', 'research_rust_blog'])('denies %s research observations even under a hypothetical source grant', registryId => {
    const candidate = {...snapshot, sources: {one: {...source, source_registry_id: registryId,
      editorial_kind: 'news', advisory: null, rights_review: {state: 'REVIEW_REQUIRED'}}}};
    expect(contentRightsErrors(candidate, {[registryId]: {publication: 'allow'}}).join(' ')).toContain('Local-only');
  });
  it('KEV date-only advisory does not satisfy current-news or the production gate', () => {
    expect(contentKind(story, snapshot.sources)).toBe('unclassified');
    expect(coverage(snapshot, now).currentNews).toEqual([]);
    expect(editorialQuality(snapshot, {production:true,now}).errors.join(' ')).toContain('No prose-backed current technology news');
  });
  it.each(['kubernetes','cisa_kev'])('keeps %s rights-excluded', registryId => {
    expect(contentRightsErrors({...snapshot,sources:{one:{...source,source_registry_id:registryId}}}).join(' ')).toContain('Excluded');
  });
  it('keeps local advisory evidence out even if a hypothetical policy allows the source', () => {
    expect(contentRightsErrors(snapshot, {cisa_kev:{publication:'allow'}}).join(' ')).toContain('Local-only');
  });
  it.each(['REVIEW_REQUIRED','REJECTED','APPROVED_WITH_EVIDENCE'])('does not trust a raw %s review assertion', state => {
    const candidate = {...snapshot,sources:{one:{...source,advisory:null,editorial_kind:'news',rights_review:{state}}}};
    expect(contentRightsErrors(candidate, {cisa_kev:{publication:'allow'}}).join(' ')).toContain('Local-only');
  });
});
