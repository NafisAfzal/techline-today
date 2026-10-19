import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { localFile, withGenerationRead } from './generation-state.mjs';

export function readSnapshot(file) {
  const name = path.resolve(file instanceof URL ? fileURLToPath(file) : file);
  if (name.endsWith(path.join('content', 'generated', 'snapshot.json'))) {
    const root = path.resolve(name, '../../..');
    return withGenerationRead(root, () => parseSnapshot(localFile(root, 'content/generated/snapshot.json')));
  }
  return parseSnapshot(name);
}

function parseSnapshot(file) {
  let snapshot;
  try { snapshot = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch { throw new Error('Snapshot missing or unreadable. Restore the reviewed content/generated/snapshot.json before building. Generate test fixtures only in an isolated workspace; preserve any live edition.'); }
  if (!['live', 'fixture'].includes(snapshot?.mode) || !Array.isArray(snapshot.stories) || !snapshot.sources || !Array.isArray(snapshot.archive_index)) {
    throw new Error('Invalid snapshot structure or mode. Validate the reviewed snapshot with python -m pipeline --validate before building.');
  }
  return snapshot;
}
