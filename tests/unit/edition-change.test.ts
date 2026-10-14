import {describe, expect, it} from 'vitest';
import {editionFingerprint, editionDecision} from '../../scripts/edition-change.mjs';

describe('incremental publication', () => {
  const snapshot = {mode:'live',generated_at:'one',last_successful_fetch_at:'one',stories:[{id:'a',headline:'Supported news',last_verified_at:'one',importance_score_internal:1,novelty_score_internal:1}],sources:{a:{title:'Source',fetched_at:'one',excerpt:'Evidence'}},offers:[],digests:[{id:'daily',status:'in-progress',generated_at:'one'}]};
  const first = editionFingerprint(snapshot, 'revision');
  it('skips rechecks without content changes', () => {
    const next = {...snapshot,generated_at:'two',last_successful_fetch_at:'two',stories:[{...snapshot.stories[0],last_verified_at:'two',importance_score_internal:0.8}],sources:{a:{...snapshot.sources.a,fetched_at:'two'}},digests:[{...snapshot.digests[0],generated_at:'two'}]};
    expect(editionDecision(editionFingerprint(next,'revision'),{fingerprint:first}).changed).toBe(false);
  });
  it('publishes changed evidence, code, calendar status and archives', () => {
    for (const fingerprint of [editionFingerprint(snapshot,'new-code'),editionFingerprint({...snapshot,sources:{a:{...snapshot.sources.a,excerpt:'Corrected evidence'}}},'revision'),editionFingerprint({...snapshot,digests:[{...snapshot.digests[0],status:'finalized'}]},'revision'),editionFingerprint(snapshot,'revision',{'2025-01':'new-hash'})]) expect(editionDecision(fingerprint,{fingerprint:first}).changed).toBe(true);
    expect(editionDecision(first,null).changed).toBe(true);
  });
});
