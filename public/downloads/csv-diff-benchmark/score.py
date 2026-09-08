#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全手法の予測を正解（truth.json）と突き合わせ、カテゴリ×手法の表を作る。

same 以外のカテゴリは「本当に違う」行しか無いので、指標は検出率（recall）
= 違うものを違うと言えた割合。
same カテゴリは「本当に同じ」行しか無いので、指標は誤検出率（false positive）
= 同じものを違うと言ってしまった割合。

出力:
  summary_<prefix>.json  手法×カテゴリの生の数字
  summary_<prefix>.csv   同じものをCSVで
  標準出力に読める表
"""
import argparse
import csv
import json
import os

CATEGORY_ORDER = ["same", "control_diff", "digit16_last", "leading_zero",
                  "space_diff", "width_diff", "case_diff", "newline_in_cell"]
CATEGORY_LABEL = {
    "same": "完全一致（誤検出の測定用）",
    "control_diff": "対照群：まったく別の値",
    "digit16_last": "16桁番号の末尾1桁違い",
    "leading_zero": "先頭ゼロの消失",
    "space_diff": "前後/全角半角スペース",
    "width_diff": "全角英数 vs 半角英数",
    "case_diff": "大文字/小文字",
    "newline_in_cell": "セル内改行・改行コード",
}
METHOD_LABEL = {
    "oracle_raw_string": "Python: 生の文字列比較（オラクル）",
    "pandas_default": "Python: pandas そのまま",
    "pandas_dtype_str": "Python: pandas dtype=str",
    "pandas_normalized": "Python: 正規化してから比較",
    "diff": "コマンド: diff",
    "comm": "コマンド: comm",
    "lo_equals__standard": "Calc（標準取込）: = 比較",
    "lo_exact__standard": "Calc（標準取込）: EXACT",
    "lo_countif__standard": "Calc（標準取込）: COUNTIF",
    "lo_vlookup__standard": "Calc（標準取込）: VLOOKUP+EXACT",
    "lo_equals__text": "Calc（テキスト取込）: = 比較",
    "lo_exact__text": "Calc（テキスト取込）: EXACT",
    "lo_countif__text": "Calc（テキスト取込）: COUNTIF",
    "lo_vlookup__text": "Calc（テキスト取込）: VLOOKUP+EXACT",
}
METHOD_ORDER = list(METHOD_LABEL.keys())


def load_all(prefix):
    merged = {}
    for fn in [f"results_python_{prefix}.json", f"results_shell_{prefix}.json",
               f"results_calc_{prefix}.json"]:
        if os.path.exists(fn):
            with open(fn, encoding="utf-8") as f:
                merged.update(json.load(f))
        else:
            print("(見つからないので飛ばす)", fn)
    return merged


def main(prefix):
    with open(f"{prefix}_truth.json", encoding="utf-8") as f:
        truth = json.load(f)
    expect = {(t["category"], t["id"]): t["expect_diff"] for t in truth}

    results = load_all(prefix)
    summary = {}
    for method in METHOD_ORDER:
        if method not in results:
            continue
        summary[method] = {}
        for cat in CATEGORY_ORDER:
            rows = results[method].get(cat)
            if not rows:
                continue
            n = len(rows)
            if cat == "same":
                # 誤検出（同じものを違うと言った）件数
                fp = sum(1 for r in rows if r["pred_diff"])
                summary[method][cat] = {"n": n, "false_positive": fp,
                                        "rate": round(fp / n * 100, 2)}
            else:
                hit = sum(1 for r in rows if r["pred_diff"])
                summary[method][cat] = {"n": n, "detected": hit, "missed": n - hit,
                                        "rate": round(hit / n * 100, 2)}
            # 正解データとの整合性チェック（保険）
            for r in rows[:5]:
                assert (cat, r["id"]) in expect

    with open(f"summary_{prefix}.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    # CSV
    with open(f"summary_{prefix}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["手法"] + [CATEGORY_LABEL[c] for c in CATEGORY_ORDER])
        for method in METHOD_ORDER:
            if method not in summary:
                continue
            row = [METHOD_LABEL[method]]
            for cat in CATEGORY_ORDER:
                s = summary[method].get(cat)
                if not s:
                    row.append("")
                elif cat == "same":
                    row.append(f"誤検出 {s['false_positive']}/{s['n']}")
                else:
                    row.append(f"{s['detected']}/{s['n']}")
            w.writerow(row)

    # 画面表示
    head = f"{'手法':38s}" + "".join(f"{CATEGORY_LABEL[c][:12]:>14s}" for c in CATEGORY_ORDER)
    print(head)
    print("-" * len(head))
    for method in METHOD_ORDER:
        if method not in summary:
            continue
        line = f"{METHOD_LABEL[method]:38s}"
        for cat in CATEGORY_ORDER:
            s = summary[method].get(cat)
            if not s:
                line += f"{'-':>14s}"
            elif cat == "same":
                line += f"{'FP ' + str(s['false_positive']) + '/' + str(s['n']):>14s}"
            else:
                line += f"{str(s['detected']) + '/' + str(s['n']):>14s}"
        print(line)
    print("\nsaved", f"summary_{prefix}.json", f"summary_{prefix}.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()
    main(args.prefix)
