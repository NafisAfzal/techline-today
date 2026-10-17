import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export function localFile(root, name) {
  const target = path.resolve(root, name);
  for (let candidate = target; candidate !== path.dirname(candidate); candidate = path.dirname(candidate)) {
    if (fs.lstatSync(candidate, {throwIfNoEntry:false})?.isSymbolicLink()) throw Error('Linked generation paths are forbidden');
  }
  return target;
}

export function assertGenerationStable(root = '.') {
  if (fs.existsSync(localFile(root, '.cache/pipeline-transaction.json'))) throw Error('Interrupted generation: recover finish or rollback before building or releasing.');
  const lock = localFile(root, '.cache/pipeline-writer.lock');
  if (fs.existsSync(lock)) {
    // Only the build wrapper's own children may read under its exclusive lock.
    const owner = JSON.parse(fs.readFileSync(lock, 'utf8'));
    if (owner.kind !== 'build' || !process.env.TECHLINE_BUILD_TOKEN || owner.token !== process.env.TECHLINE_BUILD_TOKEN) {
      throw Error('Pipeline/build writer is active or left a stale lock; inspect it before proceeding.');
    }
  }
}

export function withGenerationLock(root, action) {
  const lock = localFile(root, '.cache/pipeline-writer.lock');
  fs.mkdirSync(path.dirname(lock), {recursive:true});
  localFile(root, '.cache/pipeline-writer.lock');
  const token = randomUUID();
  const descriptor = fs.openSync(lock, 'wx');
  let closed = false;
  try {
    fs.writeFileSync(descriptor, JSON.stringify({pid:process.pid, kind:'build', token, started_at:new Date().toISOString()}));
    fs.fsyncSync(descriptor);
    fs.closeSync(descriptor);
    closed = true;
    if (fs.existsSync(localFile(root, '.cache/pipeline-transaction.json'))) throw Error('Interrupted generation requires recovery before building.');
    return action({...process.env, TECHLINE_BUILD_TOKEN:token});
  } finally {
    if (!closed) fs.closeSync(descriptor);
    // No age-based lock stealing. A killed process leaves this file for review.
    localFile(root, '.cache/pipeline-writer.lock');
    fs.unlinkSync(lock);
  }
}
