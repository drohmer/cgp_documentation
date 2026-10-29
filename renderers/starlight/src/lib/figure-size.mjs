// Intrinsic width of a figure (SVG of content/assets): the figures are shown at most at this
// width times --cgp-figure-scale (src/styles/custom.css), so that the text of every figure has
// about the same size whatever the width of the file (illustration review C1). Same rule as
// renderers/lhtml/plugins/cgp_content.py (svg_width).
import fs from 'node:fs';
import path from 'node:path';

// Resolved from the project root (cwd of npm/astro), as in api.mjs: import.meta.url is not
// stable once the reference pages are bundled.
const HERE = path.join(process.cwd(), 'src', 'lib');
const CONTENT_ASSETS = path.resolve(process.env.CGP_CONTENT_DIR ?? path.join(HERE, '..', '..', '..', '..', 'content'), 'assets');

// width attribute of the root <svg>, else the width of its viewBox; null if unknown
export function svgWidth(rel) {
	if (!/\.svg$/i.test(String(rel))) return null;
	let head;
	try {
		head = fs.readFileSync(path.join(CONTENT_ASSETS, rel), 'utf8').slice(0, 4000);
	} catch {
		return null;
	}
	const tag = /<svg\b[^>]*>/.exec(head);
	if (!tag) return null;
	const w = /\swidth="([\d.]+)(?:px)?"/.exec(tag[0]);
	if (w) return parseFloat(w[1]);
	const vb = /viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)/.exec(tag[0]);
	return vb ? parseFloat(vb[1]) : null;
}

// inline style of the <img> of a figure: "--fig-w:470px", or undefined
export function figureStyle(rel) {
	const w = svgWidth(rel);
	return w ? `--fig-w:${w}px` : undefined;
}
