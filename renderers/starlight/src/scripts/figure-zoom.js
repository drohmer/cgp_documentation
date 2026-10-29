// Figures open full size on click / tap. The figures are 700 px drawings: on a phone their
// text is about 6 px. Each figure image is wrapped in <a class="figure-zoom" href="SVG">
// (src/plugins/cgp-markdown.mjs, reference pages); without JS the link opens the image itself.
// The overlay shows the image at its own size (or larger on a wide screen), scrolls and can be
// pinch-zoomed. Same behavior as renderers/lhtml/theme/js/site.js.
(() => {
  let box = null, lastFocus = null;
  const close = () => {
    if (!box || box.hidden) return;
    box.hidden = true;
    document.documentElement.style.overflow = '';
    if (lastFocus) lastFocus.focus();
  };
  const open = (href, alt) => {
    if (!box) {
      box = document.createElement('div');
      box.className = 'lightbox';
      box.setAttribute('role', 'dialog');
      box.setAttribute('aria-modal', 'true');
      box.setAttribute('aria-label', 'Figure, full size');
      box.innerHTML = '<div class="lightbox-bar"><a class="lightbox-open" target="_blank" rel="noopener">Open the image</a>'
        + '<button type="button" class="lightbox-close">Close</button></div><img alt="">';
      box.addEventListener('click', (ev) => { if (!ev.target.closest('.lightbox-open')) close(); });
      document.body.appendChild(box);
    }
    const img = box.querySelector('img');
    img.style.width = '';
    img.onload = () => {
      const natural = img.naturalWidth || 700, avail = window.innerWidth - 56;
      img.style.width = (natural <= avail ? Math.min(avail, natural * 1.6) : natural) + 'px';
    };
    img.alt = alt || '';
    img.src = href;
    box.querySelector('.lightbox-open').href = href;
    lastFocus = document.activeElement;
    box.hidden = false;
    box.scrollTop = 0; box.scrollLeft = 0;
    document.documentElement.style.overflow = 'hidden';
    box.querySelector('.lightbox-close').focus();
  };
  document.addEventListener('click', (ev) => {
    const a = ev.target instanceof Element ? ev.target.closest('a.figure-zoom') : null;
    if (!a || ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.button !== 0) return;
    ev.preventDefault();
    const img = a.querySelector('img');
    open(a.href, img && img.alt);
  });
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') close(); });
})();
