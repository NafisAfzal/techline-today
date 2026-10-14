import {describe, expect, it} from 'vitest';
import {contentRightsErrors} from '../../scripts/content-rights.mjs';

describe('public source policy', () => {
  const story = {source_ids:['one'],change_log:[],translations:{},is_demo:false};
  const source = {source_registry_id:'arxiv',is_demo:false};
  it('allows licensed descriptive metadata and rejects retained excluded sources', () => {
    expect(contentRightsErrors({mode:'live',stories:[story],sources:{one:source}})).toEqual([]);
    expect(contentRightsErrors({mode:'live',stories:[story],sources:{one:{...source,source_registry_id:'nvidia'}}})).not.toEqual([]);
  });
  it('rejects removed citations in correction history and synthetic editions', () => {
    expect(contentRightsErrors({mode:'live',stories:[{...story,change_log:[{source_ids:['gone'],previous_facts:[]}]}],sources:{one:source}})).not.toEqual([]);
    expect(contentRightsErrors({mode:'fixture',stories:[],sources:{}})).not.toEqual([]);
  });
});
