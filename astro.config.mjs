import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import rehypeWrapTables from './src/plugins/rehype-wrap-tables.mjs';

export default defineConfig({
  site: 'https://aishigoto-lab.com',
  integrations: [sitemap()],
  markdown: {
    shikiConfig: { theme: 'github-light', wrap: true },
    rehypePlugins: [rehypeWrapTables],
  },
  build: { format: 'directory' },
});
