// Read the API model (ROOT/build/api.json) at build time and prepare it for the
// reference pages. Used both by astro.config.mjs (sidebar) and by src/pages/reference/*.
import fs from 'node:fs';
import path from 'node:path';

// Resolved from the project root (cwd of npm/astro): import.meta.url is not stable once bundled.
const here = path.join(process.cwd(), 'src', 'lib');
export const API_PATH = path.resolve(process.env.CGP_API_JSON ?? path.join(here, '..', '..', '..', '..', 'build', 'api.json'));

export const CATEGORIES = [
	['construct', 'Construct'],
	['transform', 'Transform'],
	['compute', 'Compute'],
	['draw', 'Draw'],
	['convert', 'Convert'],
	['io', 'I/O'],
	['access', 'Access'],
	['other', 'Other'],
];

let cache;
export function loadApi() {
	if (!cache) {
		const api = JSON.parse(fs.readFileSync(API_PATH, 'utf8'));
		const byId = new Map(api.functions.map((f) => [f.id, f]));
		cache = { api, byId };
	}
	return cache;
}

export const typeSlug = (name) => name.toLowerCase();

export function typeList() {
	const { api } = loadApi();
	return Object.values(api.types);
}

export const isFamily = (t) => Array.isArray(t.family_of) && t.family_of.length > 0;

// Types grouped by `group` (order of first appearance), each family first in its group.
// Groups of the Reference menu and index: each group of types followed by its pages of
// functions (`under` of function_groups.yaml), then Utilities, the pages of no type.
export const UTILITIES = 'Utilities';
export function referenceGroups() {
	const fgs = functionGroups();
	const groups = typeGroups().map((g) => ({ ...g, functions: fgs.filter((f) => f.under === g.label) }));
	const rest = fgs.filter((f) => !groups.some((g) => g.label === f.under));
	if (rest.length) groups.push({ label: UTILITIES, types: [], functions: rest });
	return groups;
}

export function typeGroups() {
	const groups = new Map();
	for (const t of typeList()) {
		const g = t.group || 'Other';
		if (!groups.has(g)) groups.set(g, []);
		groups.get(g).push(t);
	}
	return [...groups].map(([label, types]) => ({
		label,
		types: [...types.filter(isFamily), ...types.filter((t) => !isFamily(t))],
	}));
}

export function typeByName(name) {
	return loadApi().api.types[name] ?? null;
}

// Documented type whose canonical name is `canonical` (numarray_stack<float,4> -> vec4), or null.
// Families (canonical numarray_stack<T,N>) never match a concrete base.
export function typeByCanonical(canonical) {
	const norm = (s) => String(s).replace(/\s+/g, '');
	return typeList().find((t) => !isFamily(t) && norm(t.canonical) === norm(canonical)) ?? null;
}

// Display name of a canonical base: the documented type name if any, else the canonical name.
export const baseLabel = (canonical) => typeByCanonical(canonical)?.name ?? canonical;

export const typeHref = (t) => `/reference/${typeSlug(t.name)}/`;

// Groups of functions on no type page (function_groups of api.json), in the order of the model.
// Number of distinct functions that take the type, return it, or are its operators (a function
// in several lists counts once). Same definition as the lhtml reference index
// (renderers/lhtml/scripts/gen_reference.py, function_count).
export function functionCount(t) {
	return new Set(['takes', 'returns', 'operators'].flatMap((k) => (t[k] ?? []).map((e) => e.id))).size;
}

export function functionGroups() {
	return Object.values(loadApi().api.function_groups ?? {});
}
export const groupHref = (g) => `/reference/functions/${g.name}/`;

// "Operations shared by all vectors (...)" -> "all vectors"; fallback: the member list.
export function familyNoun(fam) {
	const m = /shared by (all [a-z ]+?)\b(?:\s*\(|,|\.|$)/i.exec(fam.short ?? '');
	return m ? m[1] : (fam.family_of ?? []).join(', ');
}

// ---- free functions: home page, overload groups, compact entries -----------------------
// Anchor of a function = its model id (api.json `id`), the same on every page and on both
// renderers: /reference/<home>/#<id>. Each function is listed in full on its `home` page only
// (computed by cgp-docmodel); the other type pages show it as a compact line linking there.

// URL of the home page of a function, with its anchor (null when the model gives no home).
export function homeHref(f) {
	const h = f.home;
	if (!h) return null;
	if (h.type) {
		const t = typeByName(h.type);
		return t ? `${typeHref(t)}#${f.id}` : null;
	}
	return `/reference/functions/${h.group}/#${f.id}`;
}

const isOp = (n) => n.startsWith('operator');
// by name, then the overloads in source order (the order chosen by the author: int, float, vec2...)
const byNameSig = (a, b) => isOp(a.name) - isOp(b.name) || a.name.localeCompare(b.name)
	|| String(a.file).localeCompare(String(b.file)) || (a.line ?? 0) - (b.line ?? 0) || a.signature.localeCompare(b.signature);

// Descriptions of overloads: when they all end with the same clause ("; warns if the uniform is
// not found..."), the clause is written once: { own: [per overload], common } (common may be null).
export function splitDescriptions(descs) {
	if (descs.length < 2 || descs.some((d) => !d)) return { own: descs, common: null };
	let tail = descs[0];
	for (const d of descs) while (!d.endsWith(tail)) tail = tail.slice(1);
	const cut = tail.search(/[;.] /);
	if (cut < 0) return { own: descs, common: null };
	const common = tail.slice(cut + 2).trim();
	if (common.length < 12) return { own: descs, common: null };
	const own = descs.map((d) => d.slice(0, d.length - tail.length + cut).trim() + '.');
	return { own, common: common[0].toUpperCase() + common.slice(1) };
}

// Overloads of the same name, in the order of the list: [{ name, anchor, fns: [f...] }].
export function overloadGroups(fns) {
	const groups = new Map();
	for (const f of fns) {
		if (!groups.has(f.name)) groups.set(f.name, []);
		groups.get(f.name).push(f);
	}
	return [...groups].map(([name, list]) => ({ name, anchor: list[0].anchor ?? list[0].id, fns: list }));
}

// Compact lines (functions documented on another page), one per name and home page:
// [{ name, href, home, count, description }].
export function compactItems(fns) {
	const items = new Map();
	for (const f of fns) {
		const home = !f.home ? '' : f.home.type ?? loadApi().api.function_groups?.[f.home.group]?.title ?? f.home.group;
		const k = `${f.name}\u0000${home}`;
		if (!items.has(k)) items.set(k, { name: f.name, href: homeHref(f), home, homeIsGroup: !!(f.home && !f.home.type), fns: [] });
		items.get(k).fns.push(f);
	}
	return [...items.values()].map((it) => {
		const descs = [...new Set(it.fns.map((f) => f.description ?? ''))];
		return { ...it, count: it.fns.length, description: descs.length === 1 ? descs[0] : null };
	});
}

// Entries of `list` (takes / returns / operators of a type, or functions of a group) resolved
// against the model, split into the functions documented in full here and the others.
// `isHome(f)` tells whether this page and section is the home of f; `used` keeps one full
// entry per function and page (a function both taking and returning the type).
export function resolveEntries(list, isHome = () => true, used = new Set()) {
	const { byId } = loadApi();
	const full = [], compact = [];
	for (const e of list ?? []) {
		const f0 = byId.get(e.id);
		if (!f0) continue;
		const f = { ...f0, generic: e.generic, via: e.via ?? null, shared: e.shared ?? null, anchor: f0.id };
		if ((isHome(f) || !f.home) && !used.has(f.id)) { used.add(f.id); full.push(f); } else compact.push(f);
	}
	full.sort(byNameSig);
	compact.sort(byNameSig);
	return { full, compact };
}

// Category sections: [{ cat, label, groups (overload groups in full), compact, count }].
export function groupByCategory({ full, compact }) {
	const known = new Set(CATEGORIES.map(([c]) => c));
	const catOf = (f) => (known.has(f.category) ? f.category : 'other');
	return CATEGORIES.map(([cat, label]) => {
		const fs = full.filter((f) => catOf(f) === cat);
		const cs = compact.filter((f) => catOf(f) === cat);
		return { cat, label, groups: overloadGroups(fs), compact: compactItems(cs), count: fs.length + cs.length };
	}).filter((g) => g.count);
}

// Functions of the page of type `t` (shared == null): full on their home section, compact elsewhere.
export function pageEntries(t) {
	const used = new Set();
	const sec = (rel) => resolveEntries((t[rel] ?? []).filter((e) => !e.shared),
		(f) => f.home && f.home.type === t.name && f.home.rel === rel, used);
	return { takes: sec('takes'), returns: sec('returns'), operators: sec('operators') };
}

// Entries of `t` already listed on a family page, one block per family:
// { family, count, items: [{ name, href, signature }] } (one item per distinct name, linked
// to the home anchor of its first overload).
export function sharedBlocks(t) {
	const { byId } = loadApi();
	const fams = new Map();
	for (const e of [...(t.takes ?? []), ...(t.returns ?? []), ...(t.operators ?? [])]) {
		if (!e.shared) continue;
		if (!fams.has(e.shared)) fams.set(e.shared, { entries: [], via: new Set() });
		fams.get(e.shared).entries.push(e);
		if (e.via) fams.get(e.shared).via.add(e.via);
	}
	return [...fams].map(([name, { entries, via }]) => {
		const fam = typeByName(name);
		const href = fam ? typeHref(fam) : null;
		const byName = new Map();
		const ids = new Set();
		const fns = entries.map((e) => byId.get(e.id)).filter((f) => f && !ids.has(f.id) && ids.add(f.id)).sort(byNameSig);
		for (const f of fns) {
			if (byName.has(f.name)) continue;
			byName.set(f.name, { name: f.name, signature: f.signature, href: homeHref(f) ?? href });
		}
		return { family: name, fam, href, noun: fam ? familyNoun(fam) : name, count: ids.size, via: [...via], items: [...byName.values()] };
	});
}

// ---- schema 1.5: methods, guides, links of the content pages ----------------------------

// A signature without the owner prefix: "void mesh::fill_empty_field()" -> "void fill_empty_field()".
export const shortSig = (sig, owner) => (owner ? String(sig).split(`${owner}::`).join('') : String(sig));

// A method or a field shown like a free function (FnEntry): the anchor is the id of the model
// (method id, field-<name>), the same on both renderers.
export function memberEntry(m) {
	return {
		...m,
		anchor: m.id,
		signature: shortSig(m.signature, m.owner),
		variants: (m.variants ?? []).map((v) => ({ ...v, signature: shortSig(v.signature, m.owner) })),
	};
}

// Methods grouped by name, in the order of the first declaration of each name (overloads in
// source order): [[entry, ...], ...], one FnEntry each, like the overloads of free functions.
// Same grouping as renderers/lhtml/scripts/gen_reference.py (method_groups).
export function methodGroups(methods) {
	const groups = new Map();
	for (const m of methods) {
		if (!groups.has(m.name)) groups.set(m.name, []);
		groups.get(m.name).push(memberEntry(m));
	}
	return [...groups.values()];
}

export const SECTION_LABELS = [
	['get-started', 'Get started'],
	['understand', 'Understand'],
	['how-to', 'How-to'],
	['examples', 'Examples'],
];

// content page "how-to/draw-a-mesh.md" -> "/how-to/draw-a-mesh/"
export const guideHref = (p) => '/' + p.replace(/\.md$/, '').replace(/(^|\/)index$/, '').toLowerCase() + '/';

// Guides of a type (api.json `guides`), one entry per section that has some.
export function guideSections(t) {
	const guides = t.guides ?? [];
	return SECTION_LABELS.map(([sec, label]) => ({
		sec,
		label,
		items: guides.filter((g) => g.section === sec).map((g) => ({ ...g, href: guideHref(g.path) })),
	})).filter((s) => s.items.length);
}

// URL of a target of api.json `content_links` (computed by cgp-docmodel: no name resolution here).
// Functions and members are anchored by their model id on their home page.
export function linkHref(target) {
	const href = target.type
		? (typeByName(target.type) ? typeHref(typeByName(target.type)) : null)
		: `/reference/functions/${target.group}/`;
	if (!href) return null;
	return target.id ? `${href}#${target.id}` : href;
}

export function contentLinks() {
	return loadApi().api.content_links ?? {};
}
