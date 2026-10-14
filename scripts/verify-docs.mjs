import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

const inventory = execFileSync('git',['ls-files','--cached','--others','--exclude-standard','-z'],{encoding:'utf8'}).split('\0').filter(Boolean);
const publicPaths = new Set(inventory.map(name => path.resolve(name)));
const files = inventory.filter(name => name.endsWith('.md'));
let links = 0;
for (const file of files) {
  const text = fs.readFileSync(file,'utf8');
  const targets = [...text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g), ...text.matchAll(/<img\b[^>]*\bsrc="([^"]+)"/g)];
  for (const match of targets) {
    const target = match[1].trim().replace(/^<|>$/g,'').split(/\s+"/)[0].split('#')[0];
    if (!target || /^(?:https?:|mailto:|app:|skill:)/.test(target)) continue;
    const resolved = path.resolve(path.dirname(file),decodeURIComponent(target));
    assert(fs.existsSync(resolved),`Broken documentation link in ${file}: ${target}`);
    assert(publicPaths.has(resolved) || (fs.statSync(resolved).isDirectory() && [...publicPaths].some(name => name.startsWith(resolved+path.sep))),`Documentation link targets an excluded local-only file in ${file}: ${target}`);
    links++;
  }
}
console.log(JSON.stringify({status:'passed',markdownFiles:files.length,localLinks:links,externalAvailabilityChecked:false},null,2));
