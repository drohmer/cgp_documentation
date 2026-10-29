"use strict";
// CGP overlay on the docs theme of lhtml-site (setting docs.js of configure.yaml): the
// click-to-load demos, the highlight of a targeted reference entry and the function filter
// of the reference pages. Runs after the site.js of the theme (window.docsTheme).

(function () {
  const {$, $$} = window.docsTheme;

  // ---- demos: loaded on click -----------------------------------------
  $$('figure.demo').forEach(fig => {
    const btn = $('.demo-poster', fig);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const frame = document.createElement('iframe');
      frame.src = fig.dataset.src;
      frame.title = 'Interactive CGP demo';
      frame.setAttribute('allow', 'fullscreen');
      frame.className = 'demo-frame';
      btn.replaceWith(frame);
      fig.classList.add('loaded');
    });
  });

  // ---- reference: the entry targeted by the link is highlighted -------
  // (the theme opens the <details> around it)
  function markTarget() {
    if (!location.hash) return;
    let el = null;
    try { el = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (e) {}
    if (!el) return;
    $$('.fn-entry.is-target, .fn-compact.is-target').forEach(e => e.classList.remove('is-target'));
    const entry = el.closest('.fn-entry, .fn-compact');
    if (entry) entry.classList.add('is-target');
  }
  window.addEventListener('hashchange', markTarget);
  markTarget();

  // ---- reference: filter of the functions -----------------------------
  const filter = $('#fn-filter');
  if (filter) {
    // full entries (.fn-entry), the names of the shared functions (.fn-shared) and the
    // fields and methods of the type (.member-row, also the inherited ones), the functions
    // documented on another page (.fn-compact: name, signatures, description in data-search)
    const entries = $$('.member-row, .fn-entry, .fn-shared, .fn-compact');
    const index = entries.map(e => (e.dataset.name + ' ' + (e.classList.contains('fn-shared') ? ''
      : e.classList.contains('fn-compact') ? e.dataset.search : e.textContent)).toLowerCase());
    const count = $('#fn-filter-count');
    const ops = $('details.fn-operators');
    const run = () => {
      const terms = filter.value.toLowerCase().split(/\s+/).filter(Boolean);
      let shown = 0;
      entries.forEach((e, k) => {
        const ok = terms.every(t => index[k].includes(t));
        e.hidden = !ok;
        if (e.classList.contains('fn-shared')) e.parentElement.hidden = !ok;
        if (ok) shown++;
      });
      $$('.fn-compact-block').forEach(b => { b.hidden = !b.querySelector('.fn-compact:not([hidden])'); });
      $$('.fn-group').forEach(g => { g.hidden = !g.querySelector('.fn-entry:not([hidden]), .fn-compact:not([hidden])'); });
      $$('.member-block').forEach(b => { b.hidden = !b.querySelector('.member-row:not([hidden])'); });
      $$('details.inherited').forEach(d => {
        const any = !!d.querySelector('.member-row:not([hidden])');
        d.hidden = terms.length > 0 && !any;
        if (terms.length && any) d.open = true;
      });
      $$('.fn-shared-block').forEach(b => { b.hidden = !b.querySelector('li:not([hidden])'); });
      if (ops) {
        const any = !!ops.querySelector('.fn-entry:not([hidden]), .fn-compact:not([hidden])');
        if (terms.length) { ops.hidden = !any; if (any) ops.open = true; } else { ops.hidden = false; }
      }
      document.body.classList.toggle('filtering', terms.length > 0);
      if (count) count.textContent = terms.length ? `${shown} / ${entries.length}` : '';
    };
    filter.addEventListener('input', run);
    filter.addEventListener('keydown', ev => { if (ev.key === 'Escape') { filter.value = ''; run(); } });
  }
})();
