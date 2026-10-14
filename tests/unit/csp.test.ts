import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { inlineCspHashes, previewCsp } from '../../scripts/csp.mjs';

const hash = (text:string) => "'sha256-" + createHash('sha256').update(text).digest('base64') + "'";
describe('browser-compatible inline CSP hashes', () => {
  it('handles mixed-case tags and greater-than characters in quoted attributes', () => {
    const result = inlineCspHashes('<SCRIPT data-label="x > y">window.fixture=1;</SCRIPT><STYLE>.fixture { color: red; }</STYLE>');
    expect([...result.scripts]).toEqual([hash('window.fixture=1;')]);
    expect([...result.styles]).toEqual([hash('.fixture { color: red; }')]);
  });
  it('excludes external scripts even with uppercase and spaced attributes', () => {
    expect(inlineCspHashes('<script SRC = "/fixture.js">ignored()</script>').scripts.size).toBe(0);
  });
  it('does not treat attribute text or inert template content as executable scripts', () => {
    const html = '<div data-text="<script>attribute()</script>">Text</div><template><script>inert()</script></template>';
    expect(inlineCspHashes(html).scripts.size).toBe(0);
  });
  it('hashes the browser-normalized line endings and deduplicates identical scripts', () => {
    const result = inlineCspHashes('<script>\r\nfixture();\r\n</script><script>\nfixture();\n</script>');
    expect([...result.scripts]).toEqual([hash('\nfixture();\n')]);
  });
});
describe('local HTTP preview CSP', () => {
  it('removes all upgrade directives without weakening other directives', () => {
    const input = "default-src 'self'; upgrade-insecure-requests; script-src 'self' 'sha256-fixture'; UPGRADE-INSECURE-REQUESTS; frame-ancestors 'none'; upgrade-insecure-requests;";
    expect(previewCsp(input)).toBe("default-src 'self'; script-src 'self' 'sha256-fixture'; frame-ancestors 'none'");
  });
  it('retains similarly named source URLs and returns an already-local policy intact', () => {
    const input = "script-src 'self' https://example.com/upgrade-insecure-requests.js; object-src 'none'";
    expect(previewCsp(input)).toBe(input);
  });
});
