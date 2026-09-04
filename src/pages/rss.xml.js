import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import { SITE, CATEGORIES } from '../consts';

export async function GET(context) {
  const items = (await getCollection('articles', ({ data }) => !data.draft)).sort(
    (a, b) => b.data.publishedAt.getTime() - a.data.publishedAt.getTime()
  );
  return rss({
    title: `${SITE.name}｜${SITE.tagline}`,
    description: SITE.description,
    site: context.site,
    customData: '<language>ja</language>',
    items: items.map((a) => ({
      title: a.data.title,
      description: a.data.description,
      pubDate: a.data.publishedAt,
      link: `/${CATEGORIES[a.data.category].slug}/${a.id}/`,
    })),
  });
}
