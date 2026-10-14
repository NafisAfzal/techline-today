import crypto from 'node:crypto';
import { parse } from 'parse5';

export function inlineCspHashes(html) {
  const scripts = new Set(), styles = new Set();
  const visit = node => {
    const script = node.tagName === 'script' && !node.attrs.some(attribute => attribute.name === 'src');
    if (script || node.tagName === 'style') {
      const text = node.childNodes.filter(child => child.nodeName === '#text').map(child => child.value).join('');
      if (text) (script ? scripts : styles).add("'sha256-" + crypto.createHash('sha256').update(text).digest('base64') + "'");
    }
    for (const child of node.childNodes || []) visit(child);
  };
  visit(parse(html));
  return { scripts, styles };
}

export function previewCsp(policy) {
  return policy.split(';').map(directive => directive.trim()).filter(directive =>
    directive && directive.split(/\s+/, 1)[0].toLowerCase() !== 'upgrade-insecure-requests'
  ).join('; ');
}
