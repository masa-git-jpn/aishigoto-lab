import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    category: z.enum(['lab', 'recipe', 'review']),
    publishedAt: z.coerce.date(),
    updatedAt: z.coerce.date().optional(),
    // 検証記事に必須。どうやって確かめたかを構造化して持つ
    verification: z
      .object({
        method: z.string(),
        environment: z.string(),
        sampleSize: z.string().optional(),
        dataUrl: z.string().optional(),
      })
      .optional(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { articles };
