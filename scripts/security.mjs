import fs from 'node:fs';
import path from 'node:path';
function walk(directory) {return fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry => ['node_modules','.git','.venv','.cache','dist','.astro','test-results','playwright-report'].includes(entry.name) ? [] : entry.isDirectory() ? walk(path.join(directory,entry.name)) : [path.join(directory,entry.name)]);}
const patterns=[/\bghp_[a-zA-Z0-9]{30,}\b/,/\bAIza[a-zA-Z0-9_-]{30,}\b/,/\bsk-(?:proj-)?[a-zA-Z0-9_-]{25,}\b/,/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/];
for(const file of walk('.').filter(file => (path.basename(file) === '.env.example' || !path.basename(file).startsWith('.env')) && !file.endsWith('.lock'))) {
  const text=fs.readFileSync(file,'utf8');
  if(patterns.some(pattern => pattern.test(text))) throw new Error(`Potential credential in ${file}`);
}
const example=fs.readFileSync('.env.example','utf8');
for(const line of example.split('\n')) {
  if(/^(?:[A-Z_]*(?:API_KEY|API_TOKEN)|CLOUDFLARE_ACCOUNT_ID)=\s*\S/.test(line)) throw new Error('Environment example contains a nonempty credential/account value');
}
const directory='apps/web/dist';
if(fs.existsSync(directory)) {
  const headers=fs.readFileSync(path.join(directory,'_headers'),'utf8');
  if(/'unsafe-inline'|'unsafe-eval'/.test(headers) || !headers.includes("frame-ancestors 'none'") || !headers.includes('X-Content-Type-Options: nosniff') || !headers.includes('Strict-Transport-Security: max-age=31536000')) throw Error('Production security headers missing or weakened');
  const names=['GEMINI_API_KEY','GROQ_API_KEY','OPENROUTER_API_KEY','OPENAI_COMPAT_API_KEY','CLOUDFLARE_API_TOKEN','CLOUDFLARE_AI_API_TOKEN'];
  for(const file of walk(directory)) {
    if(/\.(html|js|json)$/.test(file)) {
      const text=fs.readFileSync(file,'utf8');
      if(names.some(name => text.includes(name) || (process.env[name] && text.includes(process.env[name])))) throw new Error(`Credential leakage in ${file}`);
    }
  }
}
console.log('Source and build secret checks passed.');
