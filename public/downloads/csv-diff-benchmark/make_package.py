#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公開用データ一式をまとめる。truth は JSON だと大きすぎるので CSV にする。"""
import csv
import json
import os
import shutil

OUT = "package/csv-diff-benchmark"
SCRIPTS = ["gen_corpus.py", "gen_holdout_v2.py", "run_python_methods.py",
           "run_shell_methods.py", "run_calc_methods.py", "score.py", "sanity.py",
           "probe_threshold.py", "probe_tolerance.py", "run_encoding_test.py",
           "run_date_test.py", "make_package.py"]
DATA = ["main_a.csv", "main_b.csv", "holdout2_a.csv", "holdout2_b.csv",
        "date_input.csv", "date_roundtrip.csv", "threshold_input.csv",
        "tolerance_input.csv"]
RESULTS = ["summary_main.csv", "summary_main.json", "summary_holdout2.csv",
           "summary_holdout2.json", "diag_calc_main.json", "diag_calc_holdout2.json",
           "threshold_result.json", "tolerance_result.json", "date_result.json",
           "encoding_result.json", "results_shell_meta_main.json"]


def truth_to_csv(prefix):
    with open(f"{prefix}_truth.json", encoding="utf-8") as f:
        truth = json.load(f)
    path = os.path.join(OUT, f"{prefix}_truth.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "category", "column", "value_a", "value_b", "expect_diff", "note"])
        for t in truth:
            w.writerow([t["id"], t["category"], t["column"], t["value_a"], t["value_b"],
                        t["expect_diff"], t["note"]])
    return path


if __name__ == "__main__":
    if os.path.exists("package"):
        shutil.rmtree("package")
    os.makedirs(OUT)
    for f in SCRIPTS + DATA + RESULTS:
        if os.path.exists(f):
            shutil.copy(f, OUT)
        else:
            print("(無い)", f)
    for p in ["main", "holdout2"]:
        truth_to_csv(p)
    total = 0
    for root, _, files in os.walk(OUT):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    print(f"ファイル数 {sum(len(f) for _, _, f in os.walk(OUT))}  合計 {total/1024/1024:.1f} MB")
