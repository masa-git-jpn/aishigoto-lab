export const SITE = {
  name: 'AI仕事ラボ',
  tagline: '試した結果だけを載せる。',
  description:
    '生成AIを仕事で使うための検証メディア。実際に動かして測った数字と、そのまま動くコードだけを載せています。',
  url: 'https://aishigoto-lab.com',
  author: 'AI仕事ラボ編集部',
  lang: 'ja',
  locale: 'ja_JP',
} as const;

export const CATEGORIES = {
  lab: {
    slug: 'lab',
    name: '実測ラボ',
    description:
      '実際に動かして数えた結果だけを載せる検証記事。手順とデータをすべて公開しているので、同じ結果を再現できます。',
  },
  recipe: {
    slug: 'recipe',
    name: '実務レシピ',
    description:
      'コピーすればそのまま動く手順とコード。すべて実行して結果を確認したものだけを載せています。',
  },
  review: {
    slug: 'review',
    name: 'ツール検証',
    description:
      '実際に触って、限界まで使ってから書くレビュー。できなかったことも書きます。',
  },
} as const;

export type CategoryKey = keyof typeof CATEGORIES;

export const CONTACT = {
  // Cloudflare Email Routing で Gmail に転送する運用（Phase 1で設定）
  email: 'contact@aishigoto-lab.com',
} as const;
