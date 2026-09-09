# 日本語トークン数ベンチマーク 生データ

AI仕事ラボ（https://aishigoto-lab.com）の記事で使った検証データ一式です。

- [「日本語は1文字1トークン」を6つのトークナイザーで測ったら、当たっていたのは一世代前だけだった](https://aishigoto-lab.com/lab/japanese-token-count-measured/)

## 何を測ったか

業務で出てくる文体の日本語文書を **16ジャンル・40本（9,676文字）書き下ろし**、
6つのトークナイザーで「1文字あたり何トークンになるか」を数えました。

**文章はすべて書き下ろしです。** 既存の文章を引用していないので、全文をそのまま公開できます。
自分の文章で測り直したい場合も、`corpus.py` の形式に合わせて差し替えれば同じコードが動きます。

## 測ったトークナイザー

| 名前 | 何に使われているか | 語彙数 | 入手元 |
|---|---|---|---|
| `o200k_base` | GPT-4o / GPT-4.1 / o系 | 200,019 | tiktoken 形式のBPEファイル |
| `cl100k_base` | GPT-4 / GPT-3.5-turbo | 100,277 | 同上 |
| `p50k_base` | GPT-3（davinci 系） | 50,281 | 同上 |
| `r50k_base` | GPT-2 / GPT-3 初期 | 50,257 | 同上 |
| Claude 1〜2 世代 | 当時公開されていたもの | 64,995 | npm `@anthropic-ai/tokenizer` 0.0.4 |
| Gemma | Googleが公開しているもの | 256,000 | GitHub `google/gemma_pytorch` |

**現行の Claude と Gemini のトークナイザーは公開されていないため測れていません。**
「Claude 1〜2 世代」は当時の公開トークナイザーであって現行Claudeのものではなく、
「Gemma」はGemmaのものであってGeminiのものではありません。

### 語彙ファイルの入手について

検証環境から `openaipublic.blob.core.windows.net` と `huggingface.co` に接続できなかったため、
OpenAIの4ファイルは GitHub 上のミラー（`zurawiki/tiktoken-rs`）から取得しています。

ただし **`tiktoken` パッケージに同梱されている公式のSHA-256と、4ファイルすべてが
バイト単位で一致することを確認済み**です。照合は `verify.py` が行います。

```
cl100k_base.tiktoken  223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7
o200k_base.tiktoken   446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d
p50k_base.tiktoken    94b5ca7dff4d00767bc256fdd1b27e5b17361d7b8a5f968547f9f23eb70d2069
r50k_base.tiktoken    306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930
```

Claude 1〜2 世代の `claude.json` は、`bpe_ranks` の先頭2要素だけがbase64ではないヘッダに
なっています。読み飛ばす実装が正しいことは、**パッケージ同梱のテスト4件
（`hello world!`=3 / `™`=1 / `ϰ`=1 / `<EOT>`=1）をすべて再現して確認**しました。
本家の `countTokens()` は符号化の前に NFKC 正規化をかけるので、それも再現しています。

## ファイル

### 検証データ（全文）

| ファイル | 内容 |
|---|---|
| `corpus.py` | 本番のコーパス。8ジャンル×3本＝24本、5,985文字。英語の対照群2本を含む |
| `corpus_holdout.py` | ホールドアウトのコーパス。8ジャンル×2本＝16本、3,691文字。**測定コードを書き終えた後**に別ジャンルで書き下ろしたもの |

### 検証コード

| ファイル | 内容 |
|---|---|
| `tokenizers_setup.py` | 6つのトークナイザーをローカルファイルから組み立てる |
| `download_vocab.py` | 語彙ファイルを取得し、公式SHA-256と照合する |
| `measure.py` | コーパスを全トークナイザーにかけ、1文字あたりのトークン数を出す |
| `charclass.py` | 文字種で切り分ける（単独1文字／同じ文字種の連なり／全角と半角） |
| `rewrite_test.py` | 意味を変えずに表記を変えた8組の前後を比べる |
| `verify.py` | 測定そのものの検算（SHA-256・符号化と復号の一致・語彙数・対照群・公式テストの再現・集計の突合） |
| `verify_article.py` | 記事に書いた数字が結果ファイルと一致するかの照合 |

### 結果

| ファイル | 内容 |
|---|---|
| `results_corpus_main.json` | 本番の測定結果（文章ごと・カテゴリごと） |
| `results_corpus_holdout.json` | ホールドアウトの測定結果 |
| `results_charclass.json` | 文字種別の内訳。単独1文字のコスト分布、連なりの比率、全角と半角の対比 |
| `results_rewrite.json` | 書き換え8組の全文と前後のトークン数 |

## 再現方法

```bash
pip install tiktoken sentencepiece

python3 download_vocab.py          # 語彙ファイルの取得とSHA-256照合
python3 verify.py                  # 測定そのものの検算
python3 measure.py --prefix main                              # 本番
python3 measure.py --corpus corpus_holdout --prefix holdout   # ホールドアウト
python3 charclass.py               # 文字種の切り分け
python3 rewrite_test.py            # 書き換えの効果
python3 verify_article.py          # 記事の数字との照合
```

`vocab/` の中身は同梱していません（配布元の再配布になるため）。`download_vocab.py` が
取得と照合を行います。ネットワークに出られない環境では、公式の配布元から
同じ4ファイルを置けば同じ結果になります（SHA-256が上と一致することを確認してください）。

## 検証環境

- Python 3.11 / Ubuntu 24.04
- tiktoken 0.14.0
- sentencepiece（`google/gemma_pytorch` のモデルを読むため）
- 検証日 2026-09-09

## ライセンス

このデータとコードは自由に利用・再配布して構いません。
コーパスの文章はすべて書き下ろしで、著作権を主張しません。
引用の際は出典として記事URLを示していただけると助かります。

語彙ファイルそのものは各配布元の条件に従ってください（同梱していません）。

誤りを見つけた場合は https://aishigoto-lab.com/contact/ からご指摘ください。
確認のうえ訂正し、いつ・どこを・なぜ訂正したかを記事に明記します。
