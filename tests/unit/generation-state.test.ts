import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { afterEach, expect, test } from 'vitest';
import { assertGenerationStable, withGenerationLock } from '../../scripts/generation-state.mjs';
import { readSnapshot } from '../../scripts/read-snapshot.mjs';

const roots: string[] = [];
const temporary = () => { const root = fs.mkdtempSync(path.join(os.tmpdir(), 'techline-generation-')); roots.push(root); return root; };
afterEach(() => { for (const root of roots.splice(0)) fs.rmSync(root, {recursive:true, force:true}); });

test('readers refuse an interrupted generation before even parsing the snapshot', () => {
  const root = temporary();
  fs.mkdirSync(path.join(root, '.cache'));
  fs.writeFileSync(path.join(root, '.cache/pipeline-transaction.json'), '{}');
  expect(() => readSnapshot(path.join(root, 'content/generated/snapshot.json'))).toThrow('Interrupted generation');
});

test('build and pipeline use an exclusive lock, released on ordinary build failure', () => {
  const root = temporary();
  expect(() => withGenerationLock(root, () => {
    expect(() => assertGenerationStable(root)).toThrow('writer');
    expect(() => withGenerationLock(root, () => {})).toThrow();
    throw Error('Synthetic child failure');
  })).toThrow('Synthetic child failure');
  expect(fs.existsSync(path.join(root, '.cache/pipeline-writer.lock'))).toBe(false);
  assertGenerationStable(root);
});

test('an outstanding journal blocks the build before executing children', () => {
  const root = temporary();
  fs.mkdirSync(path.join(root, '.cache'));
  fs.writeFileSync(path.join(root, '.cache/pipeline-transaction.json'), '{}');
  let invoked = false;
  expect(() => withGenerationLock(root, () => {invoked = true;})).toThrow('recovery');
  expect(invoked).toBe(false);
});
