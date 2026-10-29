// Small remark/rehype plugins so that the shared Markdown (ROOT/content) is used verbatim.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { contentLinks, linkHref } from '../lib/api.mjs';
import { sectionGroups } from '../lib/content-groups.mjs';
import { figureStyle } from '../lib/figure-size.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOCS_DIR = path.resolve(HERE, '..', 'content', 'docs');
const CONTENT_ASSETS = path.resolve(process.env.CGP_CONTENT_DIR ?? path.join(HERE, '..', '..', '..', '..', 'content'), 'assets');

function walk(node, fn, parent = null) {
	fn(node, parent);
	if (node.children) for (const c of [...node.children]) walk(c, fn, node);
}

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');

// [{slug, title, group}] of the pages of a content section that have a demo poster
// (assets/<slug>-demo/poster.png), in the order of the menu (front matter `order`). Same list as
// renderers/lhtml/plugins/cgp_content.py (gallery_pages).
const CONTENT_DIR = path.dirname(CONTENT_ASSETS);
function galleryPages(section) {
	const dir = path.join(CONTENT_DIR, section);
	if (!fs.existsSync(dir)) return [];
	const pages = [];
	for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.md')).sort()) {
		const slug = f.slice(0, -3);
		if (!fs.existsSync(path.join(CONTENT_ASSETS, `${slug}-demo`, 'poster.png'))) continue;
		const fm = (fs.readFileSync(path.join(dir, f), 'utf8').match(/^---\n([\s\S]*?)\n---/) || [])[1] || '';
		const get = (k) => ((fm.match(new RegExp(`^${k}:\\s*(.*?)\\s*$`, 'm')) || [])[1] || '').replace(/^["']|["']$/g, '');
		pages.push({ slug, title: get('title') || slug, group: get('group'), order: Number(get('order')) || 1000 });
	}
	return pages.sort((a, b) => a.order - b.order || a.slug.localeCompare(b.slug));
}

// remark: (1) drop the leading "# Title" (Starlight already renders the front matter title),
// (2) rewrite relative links to .md files into site URLs (../reference/vec3.md -> /reference/vec3/),
// (3) replace the marker <!-- demo: NAME --> by a click-to-load poster for public/demos/NAME/.
// (4) replace the marker <!-- gallery: SECTION --> by the posters of the demos of the section.
// (5) the marker <!-- code-image: PATH | caption --> and the code block after it: side by side with
//     the image content/assets/PATH (the code block stays a code block, for Expressive Code).
export function remarkCgp() {
	return (tree, file) => {
		const first = tree.children.find((n) => n.type !== 'yaml' && n.type !== 'toml');
		if (first && first.type === 'heading' && first.depth === 1) tree.children.splice(tree.children.indexOf(first), 1);

		const filePath = file.path || file.history?.[0];
		// (5) code-image: before the walk, which replaces the html nodes
		for (let i = 0; i < tree.children.length - 1; i++) {
			const node = tree.children[i], next = tree.children[i + 1];
			const m = node.type === 'html' && /^<!--\s*code-image:\s*([^|>]+?)\s*(?:\|\s*(.*?))?\s*-->$/.exec(node.value.trim());
			if (!m || next.type !== 'code') continue;
			const caption = m[2] || '';
			node.value = '<div class="cgp-codeimg"><div class="cgp-codeimg__code">';
			tree.children.splice(i + 2, 0, {
				type: 'html',
				value: `</div><figure class="cgp-codeimg__image not-content" data-pagefind-ignore>` +
					`<img src="/assets/${esc(m[1])}" alt="${esc(caption)}" loading="lazy">` +
					(caption ? `<figcaption>${esc(caption)}</figcaption>` : '') + `</figure></div>`,
			});
		}
		walk(tree, (node) => {
			if (node.type === 'link' && filePath && /^(?![a-z]+:|\/|#)[^#?]*\.mdx?(#.*)?$/i.test(node.url)) {
				const [target, hash] = node.url.split('#');
				const abs = path.resolve(path.dirname(filePath), target);
				let slug = path.relative(DOCS_DIR, abs).split(path.sep).join('/').replace(/\.mdx?$/i, '');
				slug = slug.replace(/(^|\/)index$/, '').toLowerCase();
				node.url = '/' + (slug ? slug + '/' : '') + (hash ? '#' + hash : '');
			}
			// relative link to a file of the content assets (download of an image): site URL
			if (node.type === 'link' && filePath && /^(\.\.\/)*assets\/[^#?]+$/.test(node.url)) {
				const abs = path.resolve(path.dirname(filePath), node.url);
				node.url = '/' + path.relative(DOCS_DIR, abs).split(path.sep).join('/');
			}
			if (node.type === 'html') {
				const g = /^<!--\s*gallery:\s*([\w-]+)\s*-->$/.exec(node.value.trim());
				if (g) {
					node.value = `<div class="cgp-gallery not-content" data-pagefind-ignore>` +
						galleryPages(g[1]).map((p) =>
							`<a class="cgp-gallery__card" href="/${g[1]}/${p.slug}/">` +
							`<img src="/demos/${esc(p.slug)}/poster.png" alt="" loading="lazy">` +
							`<span class="cgp-gallery__title">${esc(p.title)}</span>` +
							`<span class="cgp-gallery__group">${esc(p.group)}</span></a>`).join('') +
						`</div>`;
				}
				const m = /^<!--\s*demo:\s*([\w-]+)\s*-->$/.exec(node.value.trim());
				if (m) {
					const name = m[1];
					// poster.png and size of the demo, read in the shared content (ROOT/content/assets/NAME-demo/)
					const folder = path.join(CONTENT_ASSETS, `${name}-demo`);
					const shot = fs.existsSync(path.join(folder, 'poster.png'));
					const size = fs.existsSync(folder)
						? fs.readdirSync(folder).filter((f) => f.startsWith('project.'))
							.reduce((s, f) => s + fs.statSync(path.join(folder, f)).size, 0) / 1e6
						: 1.4;
					const base = `/demos/${esc(name)}`;
					node.value =
						`<div class="cgp-demo not-content${shot ? ' has-shot' : ''}" data-src="${base}/index.html"` +
						(shot ? ` style="--shot: url('${base}/poster.png')"` : '') + `>` +
						`<button type="button" class="cgp-demo__poster" aria-label="Load the interactive ${esc(name)} demo">` +
						`<span class="cgp-demo__play" aria-hidden="true"></span>` +
						`<span class="cgp-demo__label">Interactive demo: ${esc(name)}</span>` +
						`<span class="cgp-demo__hint">Click to load (WebGL, about ${size.toFixed(1)} MB)</span>` +
						`</button></div>` +
						// same caption as lhtml (structure review F11): the demo alone, full window
						`<p class="cgp-demo__caption not-content" data-pagefind-ignore>Interactive CGP demo (${esc(name)}). ` +
						`<a href="${base}/index.html" target="_blank" rel="noopener">Open in a new tab</a>.</p>`;
				}
			}
		});
	};
}

// remark: the marker <!-- section-index: how-to --> of a content page (content/how-to.md) is
// replaced by the list of the pages of the section, by group (same groups and order as the
// sidebar), each with its title and description from the front matter: the index cannot drift
// from the pages. Same output as renderers/lhtml/build.py (section_index).
export function remarkSectionIndex() {
	const text = (value) => ({ type: 'text', value });
	return (tree) => {
		tree.children = tree.children.flatMap((node) => {
			const m = node.type === 'html' && /^<!--\s*section-index:\s*([\w-]+)\s*-->$/.exec(node.value.trim());
			if (!m) return [node];
			const groups = sectionGroups(m[1]) ?? [];
			return groups.flatMap((g) => [
				{ type: 'heading', depth: 2, children: [text(g.label)] },
				{
					type: 'list', ordered: false, spread: false,
					children: g.pages.map((p) => ({
						type: 'listItem', spread: false,
						children: [{
							type: 'paragraph',
							children: [
								{ type: 'link', url: `/${p.slug}/`, children: [text(p.title)] },
								...(p.description ? [text(`: ${p.description}`)] : []),
							],
						}],
					})),
				},
			]);
		});
	};
}

// remark: inline code naming a CGP type, function or member -> link to its reference page.
// The resolution is done once by cgp-docmodel (api.json `content_links`: exact span text ->
// target); nothing is guessed here. Not inside headings or links (code blocks are `code`
// nodes, never `inlineCode`). Only the first span of a given target per section (h1/h2) is
// linked: a guide citing `mesh_drawable` five times in a section gets one link.
export function remarkCodeLinks() {
	const links = contentLinks();
	return (tree) => {
		const seen = new Set();
		const visit = (node) => {
			if (!node.children) return;
			node.children = node.children.map((c) => {
				if (c.type === 'heading') {
					if (c.depth <= 2) seen.clear();
					return c;
				}
				if (c.type === 'link' || c.type === 'linkReference') return c;
				if (c.type === 'inlineCode') {
					const target = links[c.value.trim()];
					const url = target && linkHref(target);
					if (!url || seen.has(url)) return c;
					seen.add(url);
					return { type: 'link', url, data: { hProperties: { className: ['code-ref'] } }, children: [c] };
				}
				visit(c);
				return c;
			});
		};
		visit(tree);
	};
}

// rehype: a paragraph that only contains an image becomes <figure> + <figcaption>(alt).
// The image is wrapped in a link to the same file in public/assets/ (copied there by
// scripts/sync-content.mjs): a click opens it full size (src/scripts/figure-zoom.js), the
// figures being unreadable on a phone otherwise. Astro rewrites the img src (/_astro/...),
// not this link.
export function rehypeFigure() {
	const publicHref = (src) => {
		const m = /(?:^|\/)assets\/(.+)$/.exec(String(src || '').split('?')[0]);
		return m && !/^[a-z]+:/i.test(String(src)) ? '/assets/' + m[1] : null;
	};
	const hint = { type: 'element', tagName: 'span', properties: { className: ['figure-hint'], dataPagefindIgnore: '' }, children: [{ type: 'text', value: ' Tap to enlarge.' }] };
	return (tree) => {
		walk(tree, (node) => {
			if (node.type !== 'element' || node.tagName !== 'p') return;
			const kids = node.children.filter((c) => !(c.type === 'text' && !c.value.trim()));
			if (kids.length !== 1 || kids[0].type !== 'element' || kids[0].tagName !== 'img') return;
			const img = kids[0];
			const alt = img.properties?.alt;
			node.tagName = 'figure';
			const href = publicHref(img.properties?.src);
			// --fig-w (inherited by the img): the figure is shown at most at its intrinsic width.
			// On the figure, not the img: Astro rebuilds the img of a local image.
			const style = href ? figureStyle(href.replace(/^\/assets\//, '')) : undefined;
			node.properties = { className: ['cgp-figure'], ...(style ? { style } : {}) };
			const link = href
				? { type: 'element', tagName: 'a', properties: { className: ['figure-zoom'], href, ariaLabel: 'Open the figure full size' }, children: [img] }
				: img;
			node.children = [
				link,
				...(alt ? [{ type: 'element', tagName: 'figcaption', properties: {}, children: [{ type: 'text', value: String(alt) }, ...(href ? [structuredClone(hint)] : [])] }] : []),
			];
		});
	};
}
