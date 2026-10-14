import { describe, expect, it } from 'vitest';
import { siteUrl, indexingBlocked } from '../../scripts/site-url.mjs';

describe('public canonical origin', () => {
  it('isolates fixtures, example origins and explicit staging from indexing', () => {
    expect(indexingBlocked('fixture', 'approved.workers.dev', 'false')).toBe(true);
    expect(indexingBlocked('live', 'news.example.org', 'false')).toBe(true);
    expect(indexingBlocked('live', 'approved.workers.dev', 'true')).toBe(true);
    expect(indexingBlocked('live', 'approved.workers.dev', 'false')).toBe(false);
  });
  it('allows the noindex local default and normalizes a deployment origin', () => {
    expect(siteUrl(undefined).origin).toBe('https://example.com');
    expect(siteUrl('https://Tech-Intelligence.operator.workers.dev:443/', {production:true}).origin).toBe('https://tech-intelligence.operator.workers.dev');
  });
  it.each([
    'http://public.example.com', 'https://user:synthetic@public.example.com',
    'https://127.0.0.1', 'https://localhost', 'https://service.internal',
    'https://public.example.com:8443', 'https://public.example.com/path',
    'https://public.example.com?key=synthetic', 'https://public.example.com#fragment',
    'https://public.example.com\\path', ' https://public.example.com',
    'https://public.example.com\n', 'https://public.example.com\u0000',
    'https://public.example.com\u007f', 'not-an-origin',
  ])('rejects unsafe or non-origin configuration: %s', value => {
    expect(() => siteUrl(value)).toThrow();
  });
  it.each(['https://example.com', 'https://example.org', 'https://demo.example.net'])('blocks reserved examples in production: %s', value => {
    expect(() => siteUrl(value, {production:true})).toThrow();
  });
});
