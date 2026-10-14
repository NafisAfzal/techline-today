import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createGzip } from 'node:zlib';
import { previewCsp } from './csp.mjs';
const root = path.resolve('apps/web/dist');
if (!fs.existsSync(root)) throw new Error('Build the site before previewing.');
const rules = []; let current;
for (const line of fs.readFileSync(path.join(root,'_headers'),'utf8').split('\n')) {
  if (line.startsWith('/')) { current={pattern:line,headers:{}};rules.push(current); }
  else if (current && line.startsWith('  ')) { const index=line.indexOf(':'); current.headers[line.slice(2,index)] = line.slice(index+1).trim(); }
}
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.xml':'application/xml','.svg':'image/svg+xml','.wasm':'application/wasm','.txt':'text/plain'};
const server = http.createServer((request,response) => {
  let pathname;
  try {pathname=decodeURIComponent(new URL(request.url,'http://localhost').pathname);} catch {response.writeHead(400);response.end();return;}
  let target = path.resolve(root, '.' + pathname);
  if (target !== root && !target.startsWith(root+path.sep)) {response.writeHead(403);response.end();return;}
  if (fs.existsSync(target) && fs.statSync(target).isDirectory()) target=path.join(target,'index.html');
  let status=200;
  if (!fs.existsSync(target)) {target=path.join(root,pathname.startsWith('/bn/')?'bn/404.html':'404.html'); status=404;}
  const headers={'Content-Type':types[path.extname(target)] || 'application/octet-stream'};
  for (const rule of rules) if (rule.pattern === '/*' || pathname.startsWith(rule.pattern.replace('*',''))) Object.assign(headers,rule.headers);
  // HSTS/upgrading apply to HTTPS deployment; local HTTP must remain available to Playwright and developers.
  if (headers['Content-Security-Policy']) headers['Content-Security-Policy']=previewCsp(headers['Content-Security-Policy']);
  const acceptsGzip=(request.headers['accept-encoding'] || '').split(',').some(value=>value.trim().split(';')[0]==='gzip' && !/;\s*q=0(?:\.0*)?\s*$/.test(value));
  const compress=acceptsGzip && ['.html','.js','.css','.json','.xml','.svg','.wasm','.txt'].includes(path.extname(target));
  if (compress) {headers['Content-Encoding']='gzip';headers.Vary='Accept-Encoding';}
  response.writeHead(status,headers);
  if (request.method === 'HEAD') response.end();
  else if (compress) fs.createReadStream(target).pipe(createGzip()).pipe(response);
  else fs.createReadStream(target).pipe(response);
});
const port = Number(process.env.PORT || 4321);
server.listen(port,'127.0.0.1',() => console.log(`Production preview ready: http://127.0.0.1:${port}`));
