// Click-to-load for the WebGL/wasm demos (<!-- demo: NAME --> in the Markdown).
document.addEventListener('click', function (ev) {
	var btn = ev.target instanceof Element ? ev.target.closest('.cgp-demo__poster') : null;
	if (!btn) return;
	var box = btn.parentElement;
	var frame = document.createElement('iframe');
	frame.src = box.getAttribute('data-src');
	frame.title = 'Interactive CGP demo';
	frame.width = '600';
	frame.height = '600';
	frame.setAttribute('allow', 'fullscreen');
	box.replaceChildren(frame);
	box.classList.add('is-loaded');
});
