#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
副実験1：文字コードが違うだけの2ファイルを突合すると何が起きるか。

中身がまったく同じ（1文字も違わない）CSVを、UTF-8 / UTF-8(BOM付き) / Shift_JIS の
3通りで書き出し、総当たりで突合する。差分は1件も無いのが正解。
つまりここで「違う」と出たら、それは全部が誤検出（偽陽性）。

手法:
  python_no_encoding : open() を指定なしで開いて1行ずつ比較（＝環境既定のUTF-8で読む）
  python_utf8        : 両方 UTF-8 として読む
  pandas_default     : pd.read_csv をそのまま
  cmp_bytes          : cmp コマンドでバイト比較
  diff               : diff コマンド
出力: encoding_result.json
"""
import csv
import itertools
import json
import subprocess

import pandas as pd

ROWS = 500
SRC = "main_a.csv"
ENCODINGS = {
    "utf8": ("utf-8", False),
    "utf8_bom": ("utf-8-sig", False),
    "sjis": ("cp932", True),
}


def make_files():
    with open(SRC, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fields = r.fieldnames
        rows = [next(r) for _ in range(ROWS)]
    # Shift_JIS で表現できない文字（全角英数は表現できるが、念のため）を避けるため
    # 全角の列と改行を含む列は落とし、日本語＋英数字だけにする
    keep = ["id", "登録日", "顧客名", "金額", "確認用番号", "照合番号", "商品コード"]
    made = {}
    for name, (enc, _) in ENCODINGS.items():
        path = f"enc_{name}.csv"
        with open(path, "w", newline="", encoding=enc) as f:
            w = csv.DictWriter(f, fieldnames=keep)
            w.writeheader()
            for row in rows:
                w.writerow({k: row[k] for k in keep})
        made[name] = path
    return made, keep


def py_compare(path1, path2, encoding=None):
    """1行ずつ文字列比較。読めなければ例外の内容を返す。"""
    try:
        kw = {"encoding": encoding} if encoding else {}
        with open(path1, newline="", **kw) as f1, open(path2, newline="", **kw) as f2:
            a = list(csv.reader(f1))
            b = list(csv.reader(f2))
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    if len(a) != len(b):
        return {"row_count_a": len(a), "row_count_b": len(b), "mismatch": "行数が違う"}
    diff_rows = sum(1 for x, y in zip(a, b) if x != y)
    return {"rows": len(a), "diff_rows": diff_rows}


def pandas_compare(path1, path2):
    try:
        d1 = pd.read_csv(path1, dtype=str, keep_default_na=False)
        d2 = pd.read_csv(path2, dtype=str, keep_default_na=False)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    if list(d1.columns) != list(d2.columns):
        return {"columns_a": list(d1.columns)[:3], "columns_b": list(d2.columns)[:3],
                "mismatch": "列名が違う"}
    diff_rows = int((d1 != d2).any(axis=1).sum())
    return {"rows": len(d1), "diff_rows": diff_rows}


def cmd(args):
    cp = subprocess.run(args, capture_output=True, text=True, errors="replace")
    return {"returncode": cp.returncode,
            "stdout_head": cp.stdout[:200], "stderr_head": cp.stderr[:200]}


if __name__ == "__main__":
    files, keep = make_files()
    out = {"columns": keep, "rows": ROWS, "pairs": {}}
    for x, y in itertools.combinations(files, 2):
        p1, p2 = files[x], files[y]
        out["pairs"][f"{x}_vs_{y}"] = {
            "python_no_encoding": py_compare(p1, p2, None),
            "python_utf8": py_compare(p1, p2, "utf-8"),
            "pandas_default": pandas_compare(p1, p2),
            "cmp_bytes": cmd(["cmp", p1, p2]),
            "diff": cmd(["diff", "-q", p1, p2]),
        }
    # 同じファイル同士（対照）
    out["pairs"]["utf8_vs_utf8_control"] = {
        "python_utf8": py_compare(files["utf8"], files["utf8"], "utf-8"),
        "cmp_bytes": cmd(["cmp", files["utf8"], files["utf8"]]),
    }
    with open("encoding_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
