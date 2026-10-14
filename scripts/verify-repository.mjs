import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
const directory=path.resolve('.cache');
fs.mkdirSync(directory,{recursive:true});
const index=path.join(directory,'public-review-index');
const git=(args,prospective=true)=>{
  const result=spawnSync('git',['-c',`safe.directory=${process.cwd()}`,...args],{encoding:'utf8',env:prospective?{...process.env,GIT_INDEX_FILE:index}:process.env});
  assert.equal(result.status,0,`Git check failed: ${args.join(' ')}\n${result.stderr}`);
  return result.stdout;
};
const originalIndex=git(['diff','--cached','--name-only'],false);
// Rebuild the alternate index: newly ignored private captures must not persist.
const committed=spawnSync('git',['rev-parse','--verify','HEAD'],{stdio:'ignore'}).status===0;
git(['read-tree',committed?'HEAD':'--empty']);
const files=[...new Set([...git(['ls-files','-z']).split('\0'),...git(['ls-files','--cached','--others','--exclude-standard','-z'],false).split('\0')])].filter(Boolean);
const forbidden=/(^|\/)(?:node_modules|\.venv|\.cache|\.astro|dist|\.wrangler|\.lighthouseci|test-results|playwright-report|__pycache__)(\/|$)|(^|\/)\.dev\.vars|\.(?:key|pem|log|zip|webm|mp4)$/;
const keys=[/\bgh[pousr]_[a-zA-Z0-9]{30,}\b/,/\bgithub_pat_[a-zA-Z0-9_]{40,}\b/,/\bAIza[a-zA-Z0-9_-]{30,}\b/,/\bsk-(?:proj-)?[a-zA-Z0-9_-]{25,}\b/,/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/];
let bytes=0;
for(const file of files) {
  assert(!/^docs\/assets\/.*\.(?:png|jpe?g|webp|json)$/i.test(file) || /^docs\/assets\/launch\/[^/]+\.(?:jpg|json)$/.test(file),`Historical capture in public inventory: ${file}`);
  assert(!forbidden.test(file),`Local artifact in prospective commit: ${file}`);
  assert(!/(^|\/)\.env(?:\.|$)/.test(file)||file==='.env.example',`Environment file in prospective commit: ${file}`);
  assert(!/^content\/(generated|archives)\//.test(file),`Generated publisher content in prospective commit: ${file}`);
  const payload=fs.readFileSync(file);bytes+=payload.length;
  assert(payload.length<=1024*1024,`Oversized repository file: ${file}`);
  if(/\.(png|jpg|webp|ico|wasm)$/.test(file)) continue;
  const text=payload.toString('utf8');
  assert(!keys.some(pattern=>pattern.test(text)),`Possible secret in ${file}`);
  assert(!/[A-Z]:[\\/]Users[\\/](?!<)[^\s\\/]+[\\/]/i.test(text),`Personal machine path in ${file}`);
  assert(!/[A-Z]:[\\/]Projects[\\/]ai-tech-intelligence-execution-pack/i.test(text),`Local workspace path in ${file}`);
}
// Populate only the inventory that passed review; never blanket-stage files.
if(files.length) {
  const paths=path.join(directory,'public-review-paths.nul');
  fs.writeFileSync(paths,files.join('\0')+'\0');
  git(['--literal-pathspecs','add','--pathspec-from-file='+paths,'--pathspec-file-nul']);
}
git(['diff','--cached','--check']);
assert.equal(git(['diff','--cached','--name-only'],false),originalIndex,'Real index changed');
console.log(JSON.stringify({status:'passed',prospectiveFiles:files.length,totalBytes:bytes,realIndexUnchanged:true,checks:['whitespace','credentials','private keys','local environment files','generated content','machine paths','artifact exclusions','file size']},null,2));
