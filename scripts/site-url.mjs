/** Validate the public origin before generating canonical URLs or deploying. */
export function indexingBlocked(mode, hostname, noindex = process.env.SITE_NOINDEX) {
  return mode !== 'live' || /(?:^|\.)example\.(?:com|org|net)$/.test(hostname || '') || noindex === 'true';
}

export function siteUrl(value, {production = false} = {}) {
  const input = value || 'https://example.com';
  if (/[\s\\]/.test(input) || [...input].some(character => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127)) throw Error('SITE_URL contains unsafe characters');
  let url;
  try {url = new URL(input);} catch {throw Error('SITE_URL is not a valid HTTPS origin');}
  const labels = url.hostname.split('.');
  if (url.protocol !== 'https:' || url.username || url.password || url.port
      || url.pathname !== '/' || url.search || url.hash
      || labels.length < 2 || !/^[a-z]{2,63}$/.test(labels.at(-1))
      || labels.some(label => !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label))
      || /\.(?:local|localhost|internal|invalid|test)$/.test(url.hostname)) {
    throw Error('SITE_URL must be a credential-free public HTTPS origin');
  }
  if (production && /(?:^|\.)example\.(?:com|org|net)$/.test(url.hostname)) {
    throw Error('Production requires a real HTTPS SITE_URL');
  }
  return url;
}
