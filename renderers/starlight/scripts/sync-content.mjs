// Copy the shared content (ROOT/content) into the Starlight project.
// - Markdown pages        -> src/content/docs/   (verbatim, except `order` -> `sidebar.order`)
// - SVG illustrations     -> src/content/docs/assets/ (same relative paths as in ROOT/content)
// - WebGL/wasm demos      -> public/demos/<name>/ (served as static files, loaded in an iframe)
// - images of assets/     -> also public/assets/ (the generated reference pages show the
//                            figures of types.yaml at /assets/<src>)
// Pages written only for this prototype would live in src/content/docs too and are never
// touched by this script.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const project = path.resolve(here, '..');
const src = path.resolve(process.env.CGP_CONTENT_DIR ?? path.join(project, '..', '..', 'content'));
const docs = path.join(project, 'src', 'content', 'docs');
const demos = path.join(project, 'public', 'demos');

// The shared front matter field `order: N` (page order inside its section) becomes the
// Starlight field `sidebar: { order: N }`.
function withSidebarOrder(text) {
	const m = text.match(/^---\n([\s\S]*?)\n---/);
	const order = m && m[1].match(/^order:\s*(\d+)\s*$/m);
	if (!order || /^sidebar:/m.test(m[1])) return text;
	return text.replace(/^---\n/, `---\nsidebar:\n  order: ${order[1]}\n`);
}

let n = 0;
function walk(dir, rel = '') {
	for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
		const r = path.join(rel, ent.name);
		const abs = path.join(dir, ent.name);
		if (ent.isDirectory()) {
			if (rel === 'assets' && fs.existsSync(path.join(abs, 'index.html'))) {
				fs.cpSync(abs, path.join(demos, ent.name.replace(/-demo$/, '')), { recursive: true });
				n++;
				continue;
			}
			walk(abs, r);
		} else if (/\.(md|svg|png|jpe?g|webp|gif)$/i.test(ent.name)) {
			const out = path.join(docs, r);
			fs.mkdirSync(path.dirname(out), { recursive: true });
			if (ent.name.endsWith('.md')) fs.writeFileSync(out, withSidebarOrder(fs.readFileSync(abs, 'utf8')));
			else {
				fs.copyFileSync(abs, out);
				if (r.startsWith('assets' + path.sep)) {
					const pub = path.join(project, 'public', r);
					fs.mkdirSync(path.dirname(pub), { recursive: true });
					fs.copyFileSync(abs, pub);
				}
			}
			n++;
		} else if (/\.(obj|mtl|zip)$/i.test(ent.name) && r.startsWith('assets' + path.sep)) {
			// files to download (models, archives): served as they are, not content pages
			const pub = path.join(project, 'public', r);
			fs.mkdirSync(path.dirname(pub), { recursive: true });
			fs.copyFileSync(abs, pub);
			n++;
		}
	}
}
// remove the previous copies first (listed in .gitignore): a page or a demo removed from
// content/ must not stay in the site
for (const r of ['index.md', 'get-started', 'understand', 'how-to', 'examples', 'assets'])
	fs.rmSync(path.join(docs, r), { recursive: true, force: true });
for (const d of [demos, path.join(project, 'public', 'assets')]) fs.rmSync(d, { recursive: true, force: true });
walk(src);
console.log(`[sync-content] ${n} entries copied from ${src}`);

// Astro caches the rendered Markdown (node_modules/.astro/data-store.json) by page content
// only. The inline code links of the pages also depend on build/api.json (content_links, home
// pages) and on the code that turns them into URLs, the how-to index on the front matter of the
// how-to pages: when one of these changes, drop the cache so that every page is rendered again
// (otherwise links to old anchors, or an old list of recipes, stay in the site).
import crypto from 'node:crypto';
const apiJson = path.resolve(process.env.CGP_API_JSON ?? path.join(project, '..', '..', 'build', 'api.json'));
const inputs = [apiJson, path.join(project, 'src', 'lib', 'api.mjs'),
	...fs.readdirSync(path.join(project, 'src', 'plugins')).map((f) => path.join(project, 'src', 'plugins', f)),
	// the index of a section (marker <!-- section-index: how-to -->) depends on the front matter
	// of the pages of the section, not on the content of the index page itself
	path.join(project, 'src', 'lib', 'content-groups.mjs'),
	...fs.readdirSync(path.join(src, 'how-to')).filter((f) => f.endsWith('.md')).sort().map((f) => path.join(src, 'how-to', f))];
const hash = crypto.createHash('sha1');
for (const f of inputs) if (fs.existsSync(f)) hash.update(fs.readFileSync(f));
const key = hash.digest('hex');
const cacheDir = path.join(project, 'node_modules', '.astro');
const keyFile = path.join(cacheDir, 'cgp-render-key.txt');
const old = fs.existsSync(keyFile) ? fs.readFileSync(keyFile, 'utf8') : '';
if (old !== key) {
	fs.rmSync(path.join(cacheDir, 'data-store.json'), { force: true });
	fs.mkdirSync(cacheDir, { recursive: true });
	fs.writeFileSync(keyFile, key);
	console.log('[sync-content] api.json or the link code changed: Markdown render cache cleared');
}
