// @ts-check
import fs from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { unified } from '@astrojs/markdown-remark';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { remarkCgp, remarkSectionIndex, remarkCodeLinks, rehypeFigure } from './src/plugins/cgp-markdown.mjs';
import { referenceGroups, typeHref, groupHref } from './src/lib/api.mjs';
import { sectionSidebar } from './src/lib/content-groups.mjs';

const demoLoader = fs.readFileSync(new URL('./src/scripts/demo-loader.js', import.meta.url), 'utf8');
const searchExactFirst = fs.readFileSync(new URL('./src/scripts/search-exact-first.js', import.meta.url), 'utf8');
const figureZoom = fs.readFileSync(new URL('./src/scripts/figure-zoom.js', import.meta.url), 'utf8');
const menuScroll = fs.readFileSync(new URL('./src/scripts/menu-scroll.js', import.meta.url), 'utf8');

export default defineConfig({
	// Astro 7 defaults to the Satteri Markdown processor; math needs the remark/rehype one.
	markdown: {
		processor: unified({ remarkPlugins: [remarkMath, remarkCgp, remarkSectionIndex, remarkCodeLinks], rehypePlugins: [rehypeKatex, rehypeFigure] }),
	},
	integrations: [
		starlight({
			title: 'CGP',
			description: 'Computer Graphics Programming - a lightweight C++ library for 3D graphics with OpenGL.',
			logo: { src: './src/assets/logo.svg', replacesTitle: false },
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/drohmer/cgp-2027' }],
			customCss: [
				'@fontsource-variable/inter',
				'@fontsource-variable/jetbrains-mono',
				'katex/dist/katex.min.css',
				'./src/styles/custom.css',
			],
			head: [demoLoader, searchExactFirst, figureZoom, menuScroll].map((content) => ({ tag: 'script', content })),
			// section label and breadcrumb above the title of every page (src/components/PageTitle.astro)
			components: { PageTitle: './src/components/PageTitle.astro' },
			pagefind: { ranking: { termSimilarity: 10 } },
			sidebar: [
				{ label: 'Get started', items: [{ autogenerate: { directory: 'get-started' } }] },
				{ label: 'Understand', items: [{ autogenerate: { directory: 'understand' } }] },
				// How-to: one sub-group per front matter `group:` (src/lib/content-groups.mjs)
				// the first entry is the index of the section (content/how-to.md, list filled from the front matter)
				{ label: 'How-to', items: [{ slug: 'how-to', label: 'Overview' }, ...sectionSidebar('how-to')] },
				// Examples: one sub-group per front matter `group:`, only when content/examples/ has pages
				...(fs.existsSync(new URL('../../content/examples', import.meta.url))
					&& fs.readdirSync(new URL('../../content/examples', import.meta.url)).some((f) => f.endsWith('.md'))
					? [{ label: 'Examples', items: sectionSidebar('examples') }] : []),
				{
					label: 'Reference',
					items: [
						{ label: 'All types', link: '/reference/' },
						// One sub-group per type group, each family (vecN, matN) first; collapsed (the
						// group of the current page opens), as in lhtml: 60 entries otherwise.
						// then its pages of functions (function_groups.yaml, `under`), in italics; Utilities last
						...referenceGroups().map((g) => ({
							label: g.label,
							collapsed: true,
							items: [
								...g.types.map((t) => ({ label: t.name, link: typeHref(t) })),
								...g.functions.map((f) => ({ label: f.title, link: groupHref(f), attrs: { class: 'sidebar-functions' } })),
							],
						})),
					],
				},
			],
		}),
	],
});
