// Pagefind supplies highlight markup. Keep the parsed fragment inert and return
// only text; React renders that string as escaped children, never as HTML.
export function searchExcerptText(markup: string): string {
  const template = document.createElement('template');
  template.innerHTML = markup;
  for (const node of template.content.querySelectorAll('script, style, template')) node.remove();
  return template.content.textContent || '';
}
