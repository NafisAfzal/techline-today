import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import { siteUrl } from './site-url.mjs';
import { verifyProvenance } from './build-provenance.mjs';
import { verifyContentRights } from './content-rights.mjs';
const root=path.resolve('apps/web/dist');
const snapshot=JSON.parse(fs.readFileSync('content/generated/snapshot.json','utf8'));
verifyProvenance(root);
function walk(directory) {return fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(directory,entry.name)):[path.join(directory,entry.name)]);}
const files=walk(root);
const totalBytes=files.reduce((sum,file)=>sum+fs.statSync(file).size,0);
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
if(files.length>18000) throw Error('Asset count exceeds configured budget');
if(files.some(file=>fs.statSync(file).size>25*1024*1024)) throw Error('Asset exceeds free-plan size budget');
const preview = process.argv.includes('--preview');
if(process.argv.includes('--production') || preview) {
  const site=siteUrl(process.env.SITE_URL, {production:true});
  if(snapshot.mode!=='live') throw Error('Production requires live data');
  verifyContentRights(root);
  if(totalBytes>25*1024*1024) throw Error('Release bundle exceeds the 25 MiB rollback-storage budget; review shared Actions storage before publication');
  const blocked = /<meta[^>]*name="robots"[^>]*content="[^"]*noindex/.test(html);
  const robots = fs.readFileSync(path.join(root,'robots.txt'),'utf8');
  if (preview ? !blocked || !/^Disallow: \/$/m.test(robots) : blocked || !/^Allow: \/$/m.test(robots)) throw Error('Built indexing policy differs from the selected preview/production target');
  const canonical=html.match(/<link[^>]*rel="canonical"[^>]*href="([^"]+)"/);
  if(!canonical || canonical[1]!==new URL('/',site).href) throw Error('Built canonical URL differs from SITE_URL; rebuild with the deployment URL');
  for(const file of files.filter(file=>file.endsWith('.json'))) {
    if(/"is_demo"\s*:\s*true/.test(fs.readFileSync(file,'utf8'))) throw Error('Synthetic data detected in production assets');
  }
}
const refs=[...new Set([...html.matchAll(/(?:src|component-url|renderer-url)="(\/_astro\/[^"?]+\.js)"/g)].map(match=>match[1]))];
const dependencies=new Set(refs);
const walkImports=(ref)=>{
  const source=fs.readFileSync(path.join(root,ref),'utf8');
  for(const match of source.matchAll(/(?:from\s*|import\s*)["']([^"']+\.js)["']/g)) {
    const next=path.posix.normalize(path.posix.join(path.posix.dirname(ref),match[1]));
    if(next.startsWith('/_astro/') && !dependencies.has(next)) {dependencies.add(next);walkImports(next);}
  }
};
refs.forEach(walkImports);
const javascript=[...dependencies].map(ref=>fs.readFileSync(path.join(root,ref))).reduce((sum,bytes)=>sum+gzipSync(bytes).length,0);
if(javascript>100000) throw Error('Feed initial JavaScript exceeds 100 KB gzip budget');
const cssFiles=files.filter(file=>file.endsWith('.css') && file.includes(`${path.sep}_astro${path.sep}`));
const css=cssFiles.reduce((sum,file)=>sum+fs.statSync(file).size,0);
const cssGzip=cssFiles.reduce((sum,file)=>sum+gzipSync(fs.readFileSync(file)).length,0);
if(css>40000) throw Error('Application CSS exceeds 40 KB budget');
console.log(JSON.stringify({assets:files.length,totalBytes,stories:snapshot.stories.length,initialReferencedJsGzipBytes:javascript,applicationCssBytes:css,applicationCssGzipBytes:cssGzip,mode:snapshot.mode},null,2));
