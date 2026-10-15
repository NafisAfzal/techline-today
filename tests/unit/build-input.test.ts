import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { expect, it } from 'vitest';
import { readSnapshot } from '../../scripts/read-snapshot.mjs';

it('fails with actionable guidance before Astro config loads missing or corrupt input',()=>{
  const directory=mkdtempSync(path.join(tmpdir(),'techline-build-input-'));
  const file=path.join(directory,'snapshot.json');
  try {
    expect(()=>readSnapshot(file)).toThrow('Restore the reviewed');
    writeFileSync(file,'{broken');
    expect(()=>readSnapshot(file)).toThrow('isolated workspace');
    writeFileSync(file,JSON.stringify({mode:'wrong',stories:[],sources:{},archive_index:[]}));
    expect(()=>readSnapshot(file)).toThrow('Invalid snapshot structure or mode');
    const legacy={mode:'live',stories:[],sources:{},archive_index:[]};
    writeFileSync(file,JSON.stringify(legacy));
    expect(readSnapshot(file)).toEqual(legacy);
  } finally {
    expect(path.dirname(path.resolve(directory))).toBe(path.resolve(tmpdir()));
    rmSync(directory,{recursive:true});
  }
});
