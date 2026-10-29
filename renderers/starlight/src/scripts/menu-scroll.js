// Sidebar: on arrival (wide screens) and when the mobile popover opens, scroll it so that the current page is in view
// (centered). Starlight opens it at the top: on a How-to or Reference page the current entry
// was below the fold (structure review F13). lhtml does the same in theme/js/menu.js.
document.addEventListener('DOMContentLoaded', () => {
  const pane = document.getElementById('starlight__sidebar');
  if (!pane) return;
  const center = () => {
    const a = pane.querySelector('a[aria-current="page"]');
    if (!a) return;
    const r = a.getBoundingClientRect(), s = pane.getBoundingClientRect();
    if (r.top < s.top + 40 || r.bottom > s.bottom - 40)
      pane.scrollTop += r.top - s.top - (s.height - r.height) / 2;
  };
  pane.addEventListener('toggle', (ev) => { if (ev.newState === 'open') requestAnimationFrame(center); });
  // wide screens: the sidebar is always shown; on arrival, bring the current page into view
  // (only if it is not already visible, e.g. after Starlight restored the previous scroll)
  if (pane.getBoundingClientRect().height > 0) requestAnimationFrame(center);
});
