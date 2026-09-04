# Excel数式ベンチマーク 生データ

AI仕事ラボ（https://aishigoto-lab.com）の以下の記事で使用した検証データ一式です。

- [AIが書いたExcel関数300本を実際に計算させたら、軽量モデルは4本に1本間違えた](https://aishigoto-lab.com/lab/ai-excel-formula-accuracy-300/)
- [「AIへの指示は丁寧なほど正確」は本当か](https://aishigoto-lab.com/lab/ai-excel-prompt-detail-vs-accuracy/)

## ファイル

| ファイル | 内容 |
|---|---|
| `tasks_all.json` | 課題100問。`prompt`（丁寧な指示文）、`data`（シートに入れるデータ）、`expected`（期待値）、`oracle_code`（期待値をPythonで独立に算出するコード） |
| `prompts_vague.json` | 各課題の指示文を雑な言い方に書き換えたもの（元の文も併記） |
| `answers_{opus,sonnet,haiku}.json` | 丁寧な指示で各モデルが書いた数式100本 |
| `vague_answers_{opus,sonnet,haiku}.json` | 雑な指示で各モデルが書いた数式100本 |
| `results.json` | 丁寧条件の判定結果300件 |
| `results_vague.json` | 雑条件の判定結果300件 |
| `harness.py` | LibreOffice Calc を UNO ブリッジ経由で操作し、数式を実際に計算させる検証ハーネス |
| `run_bench.py` / `run_bench_vague.py` | ベンチマーク実行スクリプト |
| `offbyone.py` | 誤答の参照行を±1ずらして正解になるかを機械的に確かめるスクリプト |

## 検証環境

- LibreOffice Calc 24.2.7.2（headless / UNOブリッジ）
- Ubuntu 24.04 / Python 3.11
- 検証日 2026-09-04

## 再現方法

```bash
sudo apt install libreoffice-calc python3-uno
python3 run_bench.py          # 丁寧条件
python3 run_bench_vague.py    # 雑条件
```

## 期待値の作り方について

`expected` は Excel の関数ではなく、`oracle_code` に書いた素の Python で独立に算出しています。
つまり「Excelの考え方で作った答え」と「Excelで計算した答え」を突き合わせているのではなく、
**Excelとは無関係に出した答え**と照合しています。全100問で `oracle_code` の実行結果が `expected`
と一致することを確認済みです。

## ライセンス

このデータは自由に利用・再配布して構いません。引用の際は出典として記事URLを示していただけると助かります。
