import type { APIRoute } from 'astro';
import { data } from '../lib/data';
import { indexingBlocked } from '../../../../scripts/site-url.mjs';
export const GET: APIRoute = ({site}) => new Response(`User-agent: *\n${indexingBlocked(data.mode, site?.hostname) ? 'Disallow: /' : 'Allow: /\nDisallow: /saved/\nDisallow: /settings/'}\nSitemap: ${new URL('/sitemap-index.xml',site)}\n`,{headers:{'Content-Type':'text/plain'}});
