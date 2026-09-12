# ファイル名一括リネーム危険検出ベンチマーク 生データ

以下の記事で使った検証データです。

https://aishigoto-lab.com/lab/filename-rename-benchmark/

「大量ファイル名を一括で変える前に、危険な名前が混ざっていないか」を、
7通りの検出方法で測りました。加えて、名前の衝突を伴わない2種類の危険
(連番の桁揃え無し、連鎖リネームによる上書き)は、実際にファイルを作って
`rename` を実行し、結果を確認しています。

## 検証環境

- Python 3.11
- pathvalidate 3.3.1
- Ubuntu 24.04 (ext4・大文字小文字を区別するファイルシステム)
- 検証日 2026-09-12

**Windows・macOS実機では検証していません。** この環境がLinuxのサンドボックスのみ
のためです。大文字小文字の衝突・Unicode正規化の衝突・予約語での作成失敗は、
「計算上こうなるはず」というところまでしか確認できていません。一方、
連番の桁揃えと連鎖リネームの実験は実際にファイルを操作しており、
実機の違いに関係なく成り立つ結果です(リネームの実行順序だけが原因のため)。

## ファイル一覧

### 検証データ・コード

| ファイル | 内容 |
|---|---|
| `gen_corpus.py` | 本番コーパスの生成(14,404件)。カテゴリごとに正解を `assert` で保証している |
| `gen_holdout.py` | ホールドアウトの生成(3,603件)。本番とは別スクリプトで、拡張子だけの大文字小文字違いや二重拡張子つき予約語など新しいパターンを追加してある |
| `methods.py` | 7通りの検出方法の定義(素朴な文字列比較、lower、NFC、lower+NFC、NFKC+casefold、pathvalidate、フル装備) |
| `score.py` | コーパスに7手法をかけて、カテゴリ×手法の集計表を作る |
| `experiment_double_ext.py` | 深掘り実験:拡張子の大文字小文字を区別する `endswith()` チェックが二重拡張子を生むか(5,000件) |
| `experiment_seq_padding.py` | 深掘り実験:連番の桁揃え無しによる取り違え。30フォルダ・3,160件を対象に、素朴な文字列ソートと正しい自然順ソートを比較 |
| `experiment_chain_rename.py` | 深掘り実験:連鎖リネームによる上書き。**実際に一時ディレクトリにファイルを作り、実際に `os.replace()` でリネームを実行し、実際に中身を読んで確認している**(56パターン・432ファイル) |
| `verify_article.py` | 記事本文の数値をすべて結果ファイルと突合するスクリプト。記事6・7で確立したやり方 |
| `corpus/main.csv` | 本番コーパス(14,404行)。列は `id, category, name_a, name_b, kind, truth_danger` |
| `corpus/holdout.csv` | ホールドアウトコーパス(3,603行) |
| `results/summary_main.json` / `.txt` | 本番の集計結果(7手法×9カテゴリ、誤検出件数つき) |
| `results/summary_holdout.json` / `.txt` | ホールドアウトの集計結果 |
| `results/double_ext_result.json` | 二重拡張子実験の結果 |
| `results/seq_padding_result.json` | 連番桁揃え実験の結果(フォルダ単位の内訳つき) |
| `results/chain_rename_result.json` | 連鎖リネーム実験の結果(実際に消えた例つき) |

## コーパスの列について

`corpus/*.csv` は1行が1件の判定対象です。

- `kind` が `pair` の行は、`name_a` と `name_b` の2つの名前を比較する対象です。`truth_danger` が `True` なら「この2つは衝突するべき(同じものとして扱われるべき)」、`False` なら「無関係で衝突してはいけない」ことを表します
- `kind` が `single` の行は、`name_b` 1件だけを単体でチェックする対象です(`name_a` は空)。`truth_danger` が `True` なら「この名前は単体として無効/危険」であることを表します

カテゴリの内訳(本番コーパス、各2,000件。ただし `B1n` は400件、`D2` は4件):

| カテゴリ | 内容 | truth_danger |
|---|---|---|
| `A1_case` | 大文字小文字だけが違う名前のペア | True |
| `A2_nfc_nfd` | Unicode正規化(NFC/NFD)の違い | True |
| `A3_fullwidth` | 全角・半角の混在 | True |
| `B1_reserved` | Windows予約語(CON/PRN/AUX/NUL/COM1-9/LPT1-9) | True |
| `B1n_reserved_nearmiss` | 予約語に似ているが実際は無害な名前(誤検出しないことの確認用) | False |
| `B2_trailing` | 末尾のピリオド・空白 | True |
| `D0_exact_dup` | 対照群:完全に同じ名前(検出できて当然) | True |
| `D1_unrelated` | 対照群:無関係な名前(誤検出してはいけない) | False |
| `D2_nfkc_risk` | 副実験:NFKC正規化だと誤って同一視してしまう、本来は別物のペア | False |

## 再現方法

```
pip install pathvalidate

mkdir -p corpus results

# 本番
python3 gen_corpus.py --seed 20260912 --n 2000 --out corpus/main.csv
python3 score.py --prefix main

# ホールドアウト(score.py・methods.py は変更しない)
python3 gen_holdout.py --seed 31415926 --n 500 --out corpus/holdout.csv
python3 score.py --prefix holdout

# 深掘り実験
python3 experiment_double_ext.py
python3 experiment_seq_padding.py
python3 experiment_chain_rename.py

# 記事の数値と突合
python3 verify_article.py
```

乱数のシードを固定しているので、同じコマンドで同じコーパス・同じ結果が再生成されます。
`experiment_chain_rename.py` は `/tmp` に一時ディレクトリを作って実際にファイルを
読み書きするため、実行には数秒かかります。

## 著作権

主張しません。自由に利用・再配布してください。引用の際に出典として記事URLを
示していただけると助かります。

## 誤りを見つけた場合

https://aishigoto-lab.com/contact/ からご連絡ください。確認のうえ訂正し、
いつ・どこを・なぜ訂正したかを記事に明記します。
