# AI仕事ラボ（aishigoto-lab.com）

生成AIを仕事で使うための検証メディア。実際に動かして測った数字と、そのまま動くコードだけを載せています。

## 構成

| | |
|---|---|
| フレームワーク | Astro 5（全ページ静的生成） |
| ホスティング | Cloudflare Pages（無料枠） |
| 記事の形式 | Markdown（`src/content/articles/`） |
| 運用コスト | 0円（サーバー処理なし。アクセスが増えても費用は増えません） |

## ローカルで動かす

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # dist/ に出力
```

## Cloudflare Pages の設定値

| 項目 | 値 |
|---|---|
| フレームワークプリセット | Astro |
| ビルドコマンド | `npm run build` |
| ビルド出力ディレクトリ | `dist` |
| Node.js バージョン | 20 以上 |

`main` ブランチに push すると自動でビルド・公開されます。

## 記事の追加方法

`src/content/articles/` に Markdown を置くだけです。先頭のフロントマターは次の形式です。

```yaml
---
title: '記事タイトル'
description: '一覧と検索結果に出る説明文'
category: 'lab'          # lab（実測ラボ）| recipe（実務レシピ）| review（ツール検証）
publishedAt: 2026-09-04
verification:            # 検証記事には必須
  method: '何をどうやって確かめたか'
  environment: '実行環境とバージョン、検証日'
  sampleSize: '試行数'
tags: ['Excel', '生成AI']
---
```

`verification` を書くと、記事の冒頭に「この記事の検証方法」ボックスが自動で表示されます。

## 編集方針

1. 「〜と言われています」と書かない。確かめていないことは書かない
2. 記事の数字は必ず実際に実行して取得する
3. できなかったことも書く
4. 再現手順を必ず載せる
5. 誤りが判明したら、いつ・どこを・なぜ訂正したかを記事内に明記する

詳細は `/about/` ページに掲載しています。
