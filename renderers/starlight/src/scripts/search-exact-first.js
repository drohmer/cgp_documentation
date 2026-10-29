// Pagefind lists the sub-results of a page in page order, so on vecN "normalize" comes
// before "norm". Show the sub-result whose title is exactly the query first. Uses CSS
// order only: the Pagefind UI (Svelte) keeps ownership of its DOM nodes.
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('starlight__search');
  if (!root) return;
  const apply = () => {
    const input = root.querySelector('input.pagefind-ui__search-input');
    const q = (input && input.value || '').trim().toLowerCase();
    // Pages: one with a sub-result titled exactly as the query (a function of the reference)
    // comes first. Otherwise a long page using "normal" or "cross-section" outranks the
    // reference page for "norm" or "cross" (Pagefind matches prefixes).
    root.querySelectorAll('.pagefind-ui__results').forEach((list) => {
      list.style.display = 'flex';
      list.style.flexDirection = 'column';
      list.querySelectorAll(':scope > .pagefind-ui__result').forEach((r) => {
        const exact = q && Array.from(r.querySelectorAll('.pagefind-ui__result-nested .pagefind-ui__result-link'))
          .some((a) => a.textContent.trim().toLowerCase() === q);
        r.style.order = exact ? '-1' : '';
      });
    });
    root.querySelectorAll('.pagefind-ui__result-inner').forEach((inner) => {
      inner.style.display = 'flex';
      inner.style.flexDirection = 'column';
      // page title and excerpt stay on top, then the exact sub-result, then the others
      inner.querySelectorAll(':scope > :not(.pagefind-ui__result-nested)').forEach((n) => { n.style.order = '-2'; });
      inner.querySelectorAll(':scope > .pagefind-ui__result-nested').forEach((n) => {
        const title = (n.querySelector('.pagefind-ui__result-link') || {}).textContent || '';
        n.style.order = q && title.trim().toLowerCase() === q ? '-1' : '';
      });
    });
  };
  new MutationObserver(apply).observe(root, { childList: true, subtree: true });
});
