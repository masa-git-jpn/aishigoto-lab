#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python側の3手法を実行する。
  oracle          : csv モジュールで生の文字列のまま1行ずつ比較（正解データ検算用のオラクル）
  pandas_default  : pandas.read_csv をオプション無しで読み、id で merge して列ごとに突合
  pandas_str      : pandas.read_csv(dtype=str) で全列を文字列として読み、id で merge して突合
  normalized      : pandas_str の値に正規化（strip / NFKC / casefold / 改行統一）をかけてから突合

結果は results_python_<prefix>.json に {method: {category: [{"id":..,"pred_diff":bool}, ...]}} で保存。
"""
import argparse
import csv
import json
import unicodedata

import pandas as pd

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


def normalize(s):
    if s is None:
        return None
    s = str(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = unicodedata.normalize("NFKC", s)
    s = s.strip()
    return s.casefold()


def method_oracle(prefix):
    """csvモジュールで生の文字列を1行ずつ突合する。newline='' で開き、埋め込み改行を保持する。"""
    with open(f"{prefix}_a.csv", newline="", encoding="utf-8") as fa, \
         open(f"{prefix}_b.csv", newline="", encoding="utf-8") as fb:
        ra = {row["id"]: row for row in csv.DictReader(fa)}
        rb = {row["id"]: row for row in csv.DictReader(fb)}
    out = {cat: [] for cat in CATEGORY_COLUMN}
    for cat, col in CATEGORY_COLUMN.items():
        for rid in ra:
            va, vb = ra[rid][col], rb[rid][col]
            out[cat].append({"id": int(rid), "pred_diff": va != vb})
    return out


def method_pandas_default(prefix):
    da = pd.read_csv(f"{prefix}_a.csv")
    db = pd.read_csv(f"{prefix}_b.csv")
    m = da.merge(db, on="id", suffixes=("_a", "_b"))
    out = {cat: [] for cat in CATEGORY_COLUMN}
    for cat, col in CATEGORY_COLUMN.items():
        ca, cb = f"{col}_a", f"{col}_b"
        for _, row in m.iterrows():
            va, vb = row[ca], row[cb]
            # NaN同士は「一致」扱い（今回のデータにNaNは無いが念のため）
            diff = not (pd.isna(va) and pd.isna(vb)) and (va != vb)
            out[cat].append({"id": int(row["id"]), "pred_diff": bool(diff)})
    return out


def method_pandas_str(prefix):
    da = pd.read_csv(f"{prefix}_a.csv", dtype=str, keep_default_na=False)
    db = pd.read_csv(f"{prefix}_b.csv", dtype=str, keep_default_na=False)
    m = da.merge(db, on="id", suffixes=("_a", "_b"))
    out = {cat: [] for cat in CATEGORY_COLUMN}
    for cat, col in CATEGORY_COLUMN.items():
        ca, cb = f"{col}_a", f"{col}_b"
        for _, row in m.iterrows():
            out[cat].append({"id": int(row["id"]), "pred_diff": row[ca] != row[cb]})
    return out


def method_normalized(prefix):
    da = pd.read_csv(f"{prefix}_a.csv", dtype=str, keep_default_na=False)
    db = pd.read_csv(f"{prefix}_b.csv", dtype=str, keep_default_na=False)
    m = da.merge(db, on="id", suffixes=("_a", "_b"))
    out = {cat: [] for cat in CATEGORY_COLUMN}
    for cat, col in CATEGORY_COLUMN.items():
        ca, cb = f"{col}_a", f"{col}_b"
        for _, row in m.iterrows():
            diff = normalize(row[ca]) != normalize(row[cb])
            out[cat].append({"id": int(row["id"]), "pred_diff": diff})
    return out


METHODS = {
    "oracle_raw_string": method_oracle,
    "pandas_default": method_pandas_default,
    "pandas_dtype_str": method_pandas_str,
    "pandas_normalized": method_normalized,
}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()

    results = {}
    for name, fn in METHODS.items():
        print("running", name, "...")
        results[name] = fn(args.prefix)

    with open(f"results_python_{args.prefix}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print("saved", f"results_python_{args.prefix}.json")
