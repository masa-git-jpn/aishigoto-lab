# 請求書PDF → Excel 一括変換ベンチマーク 生データ

記事「[請求書PDF150枚をExcelにした。精度を上げるより、間違いに気づく仕掛けのほうが効いた](https://aishigoto-lab.com/recipe/invoice-pdf-to-excel-recipe/)」で使ったデータと
スクリプトの全部です。自由に使ってください（CC0）。

## 何を測ったか

正解が確定している請求書PDFを **150枚**（15の書式 × 各10枚）作り、
2つのバージョンの抽出スクリプトを当てて、項目ごとに正解と突き合わせました。

| セット | 中身 | 位置づけ |
|---|---|---|
| 第1セット（A〜E） | 格子罫線／横罫線のみ／罫線なし／xlsx由来／全角数字・△・20行 | v1 を書くときに想定した書式 |
| 第2セット（F〜J） | 列が足りない／セル内改行／8%10%混在／スキャン画像／英語・和暦 | v1 を書いたあとに作った書式 |
| 第3セット（K〜O） | ラベル違い／途中の小計行／列順が逆／空セル／2ページ目に見出し無し | **v2 を書いたあとに作った書式（ホールドアウト）** |

## 結果（要約）

`summary_all.csv` に全部入っています。数字は「50枚中」です。

| 版 | 第1セット | 第2セット | 第3セット | 合計 | 見逃し |
|---|---|---|---|---|---|
| v1 | 50 | 0 | 20 | 70 / 150 | 10枚 |
| v2 | 50 | 40 | 30 | 120 / 150 | 0枚 |

- 「合計」＝ヘッダ6項目と明細行がすべて正しかった請求書の数
- 「見逃し」＝実際は間違っているのに、スクリプトの検算を通過してしまった請求書の数

## ファイル

| ファイル | 中身 |
|---|---|
| `extract_invoices.py` | v1。フォルダ内のPDFをExcel1つにまとめる |
| `extract_invoices_v2.py` | v2。第2セットで壊れた箇所を直したもの（記事で配っているのはこれ） |
| `make_invoices.py` | 第1セット50枚を生成する |
| `make_invoices2.py` | 第2セット50枚を生成する |
| `make_invoices3.py` | 第3セット50枚を生成する |
| `truth.json` / `truth2.json` / `truth3.json` | 正解データ。紙面に印刷されている値をそのまま持っています |
| `sanity.py` | 測定前の検査。正解の文字がPDFのテキスト層に載っているかを確認する |
| `score.py` | 抽出結果を正解と突き合わせて数える |
| `summary_all.csv` / `.json` | 6回分（2版 × 3セット）の集計 |
| `detail_v*_set*.csv` | 請求書1枚ごとの結果。どこがどう間違ったかが書いてあります |
| `sample_output_v2_set3.xlsx` | v2 の出力そのもの（一覧・明細・要確認の3シート） |
| `test-invoices.zip` | 測定に使った150枚のPDFそのもの |

## 再現手順

```bash
pip install pdfplumber openpyxl
sudo apt install poppler-utils libreoffice     # pdftotext と xlsx→PDF 変換

# PDFを作る（Chromium のパスは make_invoices.py の CHROMIUM を環境に合わせて変更）
python3 make_invoices.py
python3 make_invoices2.py
python3 make_invoices3.py

# 測定前の検査
python3 sanity.py

# 抽出してExcelにする
python3 extract_invoices_v2.py ./pdfs3 -o v2_set3.xlsx --json extract_v2_set3.json

# 採点
TRUTH=truth3.json PAIRS='[["extract_v2_set3.json","v2/set3","detail.csv"]]' python3 score.py
```

## 検証環境

- Ubuntu 24.04 / Python 3.11.15
- pdfplumber 0.11.9 / openpyxl 3.1.5 / poppler-utils 24.02.0
- PDF生成：Chromium 141（HTML→印刷）、LibreOffice 24.2（xlsx→PDF）
- 検証日：2026-09-05

## 注意

PDFはすべて検証用に自作したものです。実在の企業・取引とは関係ありません。
会社名・住所・金額はすべて架空です。

誤りを見つけたら https://aishigoto-lab.com/contact/ から教えてください。
