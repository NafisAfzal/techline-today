import { createRequire } from 'node:module';
import { afterEach, describe, expect, it, vi } from 'vitest';
const webRequire = createRequire(new URL('../../apps/web/package.json', import.meta.url));
const astroRequire = createRequire(webRequire.resolve('astro/package.json'));
type Request = {url:string;method:string;headers:Record<string,string>};
type Response = {status:number;headers:Record<string,string>};
type Policy = {evaluateRequest(request:Request):{response:unknown;revalidation:{synchronous:boolean}};satisfiesWithoutRevalidation(request:Request):boolean;toObject():object;useStaleWhileRevalidate():boolean;revalidatedPolicy(request:Request,response:Response):{modified:boolean;matches:boolean}};
const CachePolicy = astroRequire('http-cache-semantics') as {new(request:Request,response:Response):Policy;fromObject(data:object):Policy};
afterEach(() => vi.useRealTimers());
describe('patched transitive cache policy',()=>{
  const request={url:'https://example.com/private',method:'GET',headers:{host:'example.com'}};
  const attack={...request,headers:{...request.headers,'cache-control':'max-stale=999999'}};
  for(const headers of [{'cache-control':'private, max-age=3600'},{'cache-control':'no-store'},{'cache-control':'no-cache, public'},{'set-cookie':'session=synthetic','cache-control':'max-age=3600'},{'set-cookie':'session=synthetic','cache-control':'immutable'}]) {
    it(`rejects max-stale for ${JSON.stringify(headers)}`,()=>{const policy=new CachePolicy(request,{status:200,headers:headers as Record<string,string>});expect(policy.evaluateRequest(attack).response).toBeUndefined();expect(policy.evaluateRequest(attack).revalidation.synchronous).toBe(true);expect(policy.satisfiesWithoutRevalidation(attack)).toBe(false);});
  }
  it('still serves explicitly public assets',()=>{const policy=new CachePolicy(request,{status:200,headers:{'cache-control':'public, max-age=3600'}});expect(policy.satisfiesWithoutRevalidation(attack)).toBe(true);});
  for (const directive of ['private', 'no-store', 'no-cache', 'proxy-revalidate', 's-maxage=0', 's-maxage=1', 'must-revalidate']) {
    it(`rejects all stale reuse paths after serialization: ${directive}`, () => {
      vi.useFakeTimers();
      const policy = new CachePolicy(request, {status:200,headers:{'cache-control':`${directive}, max-age=1, stale-if-error=3600, stale-while-revalidate=3600`}});
      vi.advanceTimersByTime(120000);
      const restored = CachePolicy.fromObject(policy.toObject());
      expect(restored.evaluateRequest(attack).response).toBeUndefined();
      expect(restored.satisfiesWithoutRevalidation(attack)).toBe(false);
      expect(restored.useStaleWhileRevalidate()).toBe(false);
      expect(restored.revalidatedPolicy(attack,{status:503,headers:{}}).modified).toBe(true);
    });
  }
  it('retains legitimate public stale reuse and respects URL and Vary matching', () => {
    vi.useFakeTimers();
    const policy = new CachePolicy(request,{status:200,headers:{'cache-control':'public, max-age=1, stale-if-error=3600', vary:'accept-language'}});
    vi.advanceTimersByTime(120000);
    expect(policy.satisfiesWithoutRevalidation(attack)).toBe(true);
    expect(policy.satisfiesWithoutRevalidation({...attack,url:'https://example.com/other'})).toBe(false);
    expect(policy.satisfiesWithoutRevalidation({...attack,headers:{...attack.headers,'accept-language':'fr'}})).toBe(false);
    expect(policy.revalidatedPolicy({...attack,url:'https://example.com/other'},{status:503,headers:{}}).modified).toBe(true);
  });
});
