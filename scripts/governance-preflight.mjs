import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readSnapshot } from './read-snapshot.mjs';

// A negative legacy-edition guard. It cannot approve drafts or grant any rights.
export function verifyGovernance() {
  if (readSnapshot('content/generated/snapshot.json').mode === 'fixture') return;
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  assert(fs.existsSync(python), 'Live governance verification requires the locked Python environment (uv sync --frozen).');
  const result = JSON.parse(execFileSync(python, ['-m', 'pipeline.publication_gate', '--existing-build'], {
    encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  }));
  assert.equal(result.status, 'passed', 'Local governance refused this generated edition.');
}
