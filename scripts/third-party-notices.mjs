import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const requireWeb = createRequire(new URL('../apps/web/package.json', import.meta.url));
const names = ['astro', '@astrojs/react', '@astrojs/internal-helpers', 'react', 'react-dom', 'scheduler', 'tailwindcss', 'pagefind', 'http-cache-semantics'];
const walk = directory => fs.readdirSync(directory, {withFileTypes: true}).flatMap(entry => entry.isDirectory() ? walk(path.join(directory, entry.name)) : [path.join(directory, entry.name)]);
let output = 'Techline Today — third-party software notices\n\nThese notices apply to bundled reader/search/style software and the included cache-policy patch. They do not license project-owned code, news, branding or screenshots. Build/test/native dependencies are not distributed in the static site.\n';
for (const name of names) {
  let directory;
  try { directory = path.dirname(requireWeb.resolve(`${name}/package.json`)); }
  catch {
    const candidate = [path.join('node_modules', name), path.join('node_modules/.pnpm/node_modules', name)].find(item => fs.existsSync(item));
    assert(candidate, `Missing installed package ${name}`);
    directory = fs.realpathSync(candidate);
  }
  const metadata = JSON.parse(fs.readFileSync(path.join(directory, 'package.json'), 'utf8'));
  const licenses = fs.readdirSync(directory).filter(file => /^(?:license|licence|notice|copying)(?:$|[.-])/i.test(file));
  assert(licenses.length > 0, `Missing packaged license for ${name}`);
  output += `\n${'='.repeat(72)}\n${name} ${metadata.version} — ${metadata.license}\n${metadata.homepage || `https://www.npmjs.com/package/${name}`}\n`;
  for (const license of licenses) {
    const target = path.join(directory, license);
    for (const file of fs.statSync(target).isDirectory() ? walk(target) : [target]) {
      output += `\n--- ${name}/${path.relative(directory, file).replaceAll('\\', '/')} ---\n${fs.readFileSync(file, 'utf8').trim()}\n`;
    }
  }
}
const target = 'apps/web/public/third-party-notices.txt';
if (process.argv.includes('--check')) assert.equal(fs.readFileSync(target, 'utf8'), output, 'Software notice inventory changed; run pnpm notices:generate and review it.');
else fs.writeFileSync(target, output);
console.log(`Third-party notices ${process.argv.includes('--check') ? 'verified' : 'generated'} for ${names.length} packages (${Buffer.byteLength(output)} bytes).`);
