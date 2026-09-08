# CSV突合ベンチマーク 生データ

AI仕事ラボ（https://aishigoto-lab.com）の記事で使った検証データ一式です。

- [2つのCSVの差分を14の方法で突合したら、16桁の番号は末尾が違っても「一致」になった](https://aishigoto-lab.com/lab/csv-diff-silent-miss/)

「正解が分かっている2つのCSV」を自作し、14通りの突合方法にかけて、
**本当は違うのに「同じ」と判定された件数**を数えたものです。

## 何を測ったか

`〜_a.csv` と `〜_b.csv` は、`id` で行が対応する2つのCSVです。
差分の種類ごとに専用の列を1本ずつ用意し、その列に意図的な差分を仕込んであります。

| 列名 | 仕込んだ差分 | 正解 |
|---|---|---|
| `確認用番号` | なし（常に完全一致） | 同じ |
| `対照用コード` | まったく別の値 | 違う |
| `照合番号` | 16桁番号の末尾1桁違い | 違う |
| `商品コード` | 先頭ゼロの消失（`0999632506` → `999632506`） | 違う |
| `得意先コード` | 前後の空白、全角スペース、中間の空白 | 違う |
| `型番` | 半角英数 vs 全角英数 | 違う |
| `承認者ID` | 英字の大文字/小文字 | 違う |
| `備考` | セル内改行、改行コード（CRLF/LF） | 違う |

**`確認用番号` 以外の列は、`value_a` と `value_b` が生の文字列として必ず異なります**
（生成時に `assert` で保証しています）。つまり正解は常に「違う」です。
`対照用コード` は対照群で、これを検出できない手法は測定系自体が壊れていると判断します。

正解の全リストは `main_truth.csv` / `holdout2_truth.csv` にあります（1行＝1セルの判定）。

## ファイル

### 検証データ

| ファイル | 内容 |
|---|---|
| `main_a.csv` / `main_b.csv` | 本番用。10,000行 × 8カテゴリ = 80,000件の判定対象 |
| `main_truth.csv` | 本番用の正解。どの行にどの種類を仕込んだか |
| `holdout2_a.csv` / `holdout2_b.csv` | ホールドアウト用。2,000行。集計コードを書き終えた**後で**作った |
| `holdout2_truth.csv` | ホールドアウト用の正解 |

ホールドアウトは、本番より難しいパターンに差し替えてあります（17桁・18桁の番号、
末尾2桁違い、ゼロ幅スペース、ノーブレークスペース、CRのみの改行、部分的な全角混在など）。
**集計コードは1文字も変更せずにこのデータへ当てています。**

### 検証コード

| ファイル | 内容 |
|---|---|
| `gen_corpus.py` | 本番コーパスの生成 |
| `gen_holdout_v2.py` | ホールドアウトの生成（本番とは別スクリプト） |
| `run_python_methods.py` | Python側4手法（生の文字列 / pandas / pandas dtype=str / 正規化） |
| `run_shell_methods.py` | コマンド2手法（diff / comm）。実際に `diff` と `comm` を起動している |
| `run_calc_methods.py` | LibreOffice Calc をUNO経由で操作し、CSVを実際に開いて数式で突合する |
| `score.py` | 手法×カテゴリの集計表を作る |
| `sanity.py` | 「なぜそうなったか」の説明が本当に正しいかを機械的に検算する |
| `probe_threshold.py` | 2^53 をまたぐ番号のペアで挙動を1件ずつ確認する |
| `probe_tolerance.py` | 「=」がどれだけ離れれば「違う」と言うのか、境界を実測する |
| `run_encoding_test.py` | 副実験：文字コードだけが違う2ファイルの突合 |
| `run_date_test.py` | 副実験：開いて保存し直すと値が書き換わるか |

### 結果

| ファイル | 内容 |
|---|---|
| `summary_main.csv` / `.json` | 本番の集計表（手法×カテゴリ） |
| `summary_holdout2.csv` / `.json` | ホールドアウトの集計表 |
| `diag_calc_main.json` | 16桁番号列の内訳（値まで同じ / 表示文字列だけ同じ）と実例 |
| `threshold_result.json` | 2^53 をまたぐペアの実測 |
| `tolerance_result.json` | 「=」の許容差の実測 |
| `encoding_result.json` | 文字コード副実験の結果 |
| `date_result.json` | 開いて保存し直す副実験の結果 |
| `date_roundtrip.csv` | `date_input.csv` を標準設定で開いて保存し直したもの。7/16 の値が書き換わっている |
| `results_shell_meta_main.json` | diff/comm に渡したファイルの物理行数（セル内改行で行がずれた記録） |

手法ごと・行ごとの生の判定（1件ずつのTRUE/FALSE）は合計40MB近くになるため
同梱していません。下の手順で再実行すれば同じものが手元に出ます。

## 再現方法

```bash
sudo apt install libreoffice-calc python3-uno
pip install pandas

# 本番
python3 gen_corpus.py --n 10000 --seed 20260908 --out-prefix main
python3 run_python_methods.py --prefix main
python3 run_shell_methods.py  --prefix main
python3 run_calc_methods.py   --prefix main --n 10000 --vlookup-sample 1000
python3 score.py  --prefix main
python3 sanity.py main

# ホールドアウト（集計コードは変更しない）
python3 gen_holdout_v2.py --n 2000 --seed 31415926 --out-prefix holdout2
python3 run_python_methods.py --prefix holdout2
python3 run_shell_methods.py  --prefix holdout2
python3 run_calc_methods.py   --prefix holdout2 --n 2000 --vlookup-sample 1000
python3 score.py  --prefix holdout2

# 副実験と境界の実測
python3 probe_threshold.py
python3 probe_tolerance.py
python3 run_encoding_test.py
python3 run_date_test.py
```

乱数のシードを固定しているので、同じシードなら同じCSVが再生成されます。

`run_calc_methods.py` は本番（10,000行）で20分ほどかかります。
VLOOKUP は1件ごとに全行を線形探索するため行数の2乗に比例して遅くなり、
全行では現実的な時間で終わらないので先頭1,000行だけで測っています
（集計表の VLOOKUP の行だけ分母が 1000 なのはこのためです）。

## 検証環境

- LibreOffice Calc 24.2.7.2（headless / UNOブリッジ）
- Ubuntu 24.04 / Python 3.11 / pandas 3.0.2
- GNU diffutils（`diff` / `comm`）
- 検証日 2026-09-08

**Excel本体では検証していません。** この環境にExcelが無いためです。
記事中の「表計算ソフト」はすべて LibreOffice Calc を指します。

## CSVの取り込み条件について

`run_calc_methods.py` は同じCSVを2通りの条件で開いています。

- **標準取込**：列書式を何も指定しない（取り込みダイアログでそのままOKを押した状態）。
  数字に見えるセルは数値として取り込まれる
- **テキスト取込**：全列を「テキスト」に指定する

UNOのフィルタオプション文字列では、列書式は `列番号/書式コード` を `/` でつないで
並べます（書式コード2＝テキスト）。カンマ区切りにすると**無視されます**。
最初これに気づかず、標準取込と同じ結果を「テキスト取込」として一度測り直しています。

## ライセンス

このデータは自由に利用・再配布して構いません。
引用の際は出典として記事URLを示していただけると助かります。

誤りを見つけた場合は https://aishigoto-lab.com/contact/ からご指摘ください。
確認のうえ訂正し、いつ・どこを・なぜ訂正したかを記事に明記します。
