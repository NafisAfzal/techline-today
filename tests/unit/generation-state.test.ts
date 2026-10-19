import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL } from 'node:url';
import { afterEach, expect, test, vi } from 'vitest';
import { assertGenerationStable, withGenerationLock, withGenerationRead } from '../../scripts/generation-state.mjs';
import { readSnapshot } from '../../scripts/read-snapshot.mjs';

const roots: string[] = [];
const temporary = () => { const root = fs.mkdtempSync(path.join(os.tmpdir(), 'techline-generation-')); roots.push(root); return root; };
afterEach(() => { vi.unstubAllEnvs(); for (const root of roots.splice(0)) fs.rmSync(root, {recursive:true, force:true}); });

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

const edition = {mode:'live', stories:[], sources:{}, archive_index:[]};
function snapshotFile(root: string, bytes = JSON.stringify(edition)) {
  const file = path.join(root, 'content/generated/snapshot.json');
  fs.mkdirSync(path.dirname(file), {recursive:true});
  fs.writeFileSync(file, bytes);
  return file;
}

test('a valid snapshot read preserves the edition and releases its temporary lock', () => {
  const root = temporary();
  const file = snapshotFile(root);
  const before = fs.readFileSync(file);
  expect(readSnapshot(pathToFileURL(file))).toEqual(edition);
  expect(fs.readFileSync(file)).toEqual(before);
  expect(fs.existsSync(path.join(root, '.cache/pipeline-writer.lock'))).toBe(false);
});

test('a reader excludes a concurrent writer until the complete synchronous read returns', () => {
  const root = temporary();
  const file = snapshotFile(root);
  const lock = path.join(root, '.cache/pipeline-writer.lock');
  withGenerationRead(root, () => {
    expect(() => fs.openSync(lock, 'wx')).toThrow();
    expect(JSON.parse(fs.readFileSync(file, 'utf8'))).toEqual(edition);
  });
  const descriptor = fs.openSync(lock, 'wx');
  fs.closeSync(descriptor);
  fs.unlinkSync(lock);
});

test.each(['pipeline', 'build'])('an active or stale %s writer cannot be read under a foreign token', kind => {
  const root = temporary();
  const file = snapshotFile(root);
  fs.mkdirSync(path.join(root, '.cache'));
  fs.writeFileSync(path.join(root, '.cache/pipeline-writer.lock'), JSON.stringify({kind, token:'foreign'}));
  vi.stubEnv('TECHLINE_BUILD_TOKEN', 'reader');
  expect(() => readSnapshot(file)).toThrow('writer');
  expect(JSON.parse(fs.readFileSync(file, 'utf8'))).toEqual(edition);
});

test('build children read under their inherited token without reacquiring the exclusive lock', () => {
  const root = temporary();
  const file = snapshotFile(root);
  withGenerationLock(root, env => {
    vi.stubEnv('TECHLINE_BUILD_TOKEN', env.TECHLINE_BUILD_TOKEN);
    expect(readSnapshot(file)).toEqual(edition);
    expect(fs.existsSync(path.join(root, '.cache/pipeline-writer.lock'))).toBe(true);
  });
  expect(fs.existsSync(path.join(root, '.cache/pipeline-writer.lock'))).toBe(false);
});

test.each(['{corrupt', JSON.stringify({version:1, generation:'stale-generation'})])('unresolved generation metadata refuses while preserving the last good edition: %s', journal => {
  const root = temporary();
  const file = snapshotFile(root);
  fs.mkdirSync(path.join(root, '.cache'));
  fs.writeFileSync(path.join(root, '.cache/pipeline-transaction.json'), journal);
  expect(() => readSnapshot(file)).toThrow('Interrupted generation');
  expect(JSON.parse(fs.readFileSync(file, 'utf8'))).toEqual(edition);
});

test('corrupt input releases the reader lock and preserves the last built artifact', () => {
  const root = temporary();
  const file = snapshotFile(root, '{corrupt');
  const artifact = path.join(root, 'last-good.html');
  fs.writeFileSync(artifact, 'last reviewed edition');
  expect(() => readSnapshot(file)).toThrow('Snapshot missing or unreadable');
  expect(fs.existsSync(path.join(root, '.cache/pipeline-writer.lock'))).toBe(false);
  expect(fs.readFileSync(artifact, 'utf8')).toBe('last reviewed edition');
  fs.writeFileSync(file, JSON.stringify(edition));
  expect(readSnapshot(file)).toEqual(edition);
});
