import fs from 'node:fs';

export function readSnapshot(file) {
  let snapshot;
  try { snapshot = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch { throw new Error('Snapshot missing or unreadable. Restore the reviewed content/generated/snapshot.json before building. Generate test fixtures only in an isolated workspace; preserve any live edition.'); }
  if (!['live', 'fixture'].includes(snapshot?.mode) || !Array.isArray(snapshot.stories) || !snapshot.sources || !Array.isArray(snapshot.archive_index)) {
    throw new Error('Invalid snapshot structure or mode. Validate the reviewed snapshot with python -m pipeline --validate before building.');
  }
  return snapshot;
}
