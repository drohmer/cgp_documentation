import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

export const collections = {
	docs: defineCollection({
		loader: docsLoader(),
		// `section`, `group` and `order` come from the shared Markdown front matter; `order` is
		// copied to `sidebar.order` by scripts/sync-content.mjs. `local_names` is read by the
		// content check of cgp-docmodel only.
		schema: docsSchema({ extend: z.object({ section: z.string().optional(), group: z.string().optional(), order: z.number().optional(), local_names: z.array(z.string()).optional() }) }),
	}),
};
