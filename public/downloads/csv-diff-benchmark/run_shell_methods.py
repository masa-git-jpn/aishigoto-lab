#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コマンド (diff / comm) で id,value の2列だけを抜き出したファイルを突合する。

抜き出しは csv.writer で正しくクォートして書き出す（本物のCSVエクスポートを模す）。
埋め込み改行（newline_in_cell）はCSV上は正しくクォートされていても、
diff/comm は「物理行」単位でしか見ないため、1つの論理行が複数の物理行に
またがってしまう。これがそのまま診断結果に出る。

diff  : diff -u a b の出力を解析し、変更のあった論理行（の周辺）から
        影響を受けた id を割り出す。埋め込み改行のせいで行がずれた場合は
        その旨を breakage フラグとして記録する。
comm  : 各ファイルを1行1レコードとしてソートし、comm -3 で「片方にしかない行」を
        取り出す。そこに出てくる id を「差分として検出された」とみなす。
"""
import argparse
import csv
import json
import subprocess

CATEGORY_COLUMN = {
    "same": "確認用番号",
    "control_diff": "対照用コード",
    "digit16_last": "照合番号",
    "leading_zero": "商品コード",
    "space_diff": "得意先コード",
    "width_diff": "型番",
    "case_diff": "承認者ID",
    "newline_in_cell": "備考",
}


def extract_pair_csv(prefix, category, side, path):
    col = CATEGORY_COLUMN[category]
    with open(f"{prefix}_{side}.csv", newline="", encoding="utf-8") as fin:
        rows = list(csv.DictReader(fin))
    with open(path, "w", newline="", encoding="utf-8") as fout:
        w = csv.writer(fout)
        for row in rows:
            w.writerow([row["id"], row[col]])
    return len(rows)


def run_diff(prefix, category):
    path_a = f"tmp_{prefix}_{category}_a.csv"
    path_b = f"tmp_{prefix}_{category}_b.csv"
    n = extract_pair_csv(prefix, category, "a", path_a)
    extract_pair_csv(prefix, category, "b", path_b)

    # 実際の物理行数を数える（埋め込み改行があると n より多くなる）
    with open(path_a, encoding="utf-8") as f:
        phys_lines_a = sum(1 for _ in f)
    with open(path_b, encoding="utf-8") as f:
        phys_lines_b = sum(1 for _ in f)
    line_count_broken = (phys_lines_a != n) or (phys_lines_b != n)

    cp = subprocess.run(["diff", "--unified=0", path_a, path_b],
                         capture_output=True, text=True)
    out = cp.stdout

    # ---- unified diff から「変化があった」idを拾う ----
    # 行が壊れていない（1論理行=1物理行）カテゴリでは、各 @@ ハンクの -行 側から
    # 行頭の id を素直に読める。壊れているカテゴリ（newline_in_cell）は、
    # ハンクに含まれる全ての物理行から数字トークンを拾い、id として拾えるものを
    # 「影響を受けた可能性がある id」として広めに数える（＝実務でどれだけ被害が
    # 広がるかを可視化する）。
    detected_ids = set()
    for line in out.splitlines():
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("-") or line.startswith("+"):
            token = line[1:].split(",")[0].strip()
            if token.isdigit():
                detected_ids.add(int(token))

    all_ids = set(range(1, n + 1))
    pred = {rid: (rid in detected_ids) for rid in all_ids}
    return pred, {
        "n_rows": n, "phys_lines_a": phys_lines_a, "phys_lines_b": phys_lines_b,
        "line_count_broken": line_count_broken, "n_detected_ids": len(detected_ids),
    }


def run_comm(prefix, category):
    path_a = f"tmp_{prefix}_{category}_a.csv"
    path_b = f"tmp_{prefix}_{category}_b.csv"
    # run_diff で既に作られている前提だが、独立実行できるよう再生成もしておく
    n = extract_pair_csv(prefix, category, "a", path_a)
    extract_pair_csv(prefix, category, "b", path_b)

    sorted_a = f"tmp_{prefix}_{category}_a.sorted.csv"
    sorted_b = f"tmp_{prefix}_{category}_b.sorted.csv"
    subprocess.run(f"LC_ALL=C sort {path_a} > {sorted_a}", shell=True, check=True)
    subprocess.run(f"LC_ALL=C sort {path_b} > {sorted_b}", shell=True, check=True)

    cp = subprocess.run(["comm", "-3", sorted_a, sorted_b], capture_output=True, text=True)
    detected_ids = set()
    for line in cp.stdout.splitlines():
        content = line.lstrip("\t")
        token = content.split(",")[0].strip()
        if token.isdigit():
            detected_ids.add(int(token))

    all_ids = set(range(1, n + 1))
    pred = {rid: (rid in detected_ids) for rid in all_ids}
    return pred, {"n_rows": n, "n_detected_ids": len(detected_ids)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()

    results = {"diff": {}, "comm": {}}
    meta = {"diff": {}, "comm": {}}
    for category in CATEGORY_COLUMN:
        pred_d, meta_d = run_diff(args.prefix, category)
        pred_c, meta_c = run_comm(args.prefix, category)
        results["diff"][category] = [{"id": rid, "pred_diff": v} for rid, v in sorted(pred_d.items())]
        results["comm"][category] = [{"id": rid, "pred_diff": v} for rid, v in sorted(pred_c.items())]
        meta["diff"][category] = meta_d
        meta["comm"][category] = meta_c
        print(category, "diff:", meta_d, "comm:", meta_c)

    with open(f"results_shell_{args.prefix}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    with open(f"results_shell_meta_{args.prefix}.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("saved", f"results_shell_{args.prefix}.json")
