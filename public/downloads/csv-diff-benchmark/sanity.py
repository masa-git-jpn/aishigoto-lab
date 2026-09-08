#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
結果の説明が本当に正しいかを機械的に検算する。
「たぶんこういう理由」で書かないための確認。

1. 16桁で見逃された行は、本当に 2^53 (9007199254740992) より大きいか
2. セル内改行で見逃された数は、CRLF/LFの違いだけの行数と一致するか
3. 空白で正規化比較が検出した数は、中間に空白が入った行数と一致するか
4. 先頭ゼロは、数値化すると本当にAとBが同じ数になるか
"""
import json
from collections import Counter

TWO53 = 9007199254740992


def load(prefix):
    truth = json.load(open(f"{prefix}_truth.json", encoding="utf-8"))
    by = {}
    for t in truth:
        by.setdefault(t["category"], {})[t["id"]] = t
    calc = json.load(open(f"results_calc_{prefix}.json", encoding="utf-8"))
    py = json.load(open(f"results_python_{prefix}.json", encoding="utf-8"))
    return by, calc, py


def main(prefix="main"):
    by, calc, py = load(prefix)
    print(f"===== {prefix} の検算 =====\n")

    # --- 1. 16桁：見逃した行の大きさ ---
    for method in ["lo_equals__standard", "lo_exact__standard"]:
        rows = calc[method]["digit16_last"]
        missed = [r["id"] for r in rows if not r["pred_diff"]]
        vals = [int(by["digit16_last"][i]["value_a"]) for i in missed]
        over = sum(1 for v in vals if v > TWO53)
        print(f"[1] {method}: 見逃し {len(missed)}件")
        print(f"    うち 2^53({TWO53}) より大きい: {over}件 "
              f"({over / len(missed) * 100:.1f}%)")
        print(f"    見逃した値の最小: {min(vals)}  最大: {max(vals)}")
        # 検出できた行の分布と比べる
        detected = [int(by["digit16_last"][r["id"]]["value_a"]) for r in rows if r["pred_diff"]]
        det_over = sum(1 for v in detected if v > TWO53)
        print(f"    参考：検出できた {len(detected)}件のうち 2^53超えは {det_over}件")
        # 母集団に 2^53 超えは何件あるか
        allv = [int(t["value_a"]) for t in by["digit16_last"].values()]
        print(f"    母集団 {len(allv)}件のうち 2^53超えは "
              f"{sum(1 for v in allv if v > TWO53)}件\n")

    # --- 2. セル内改行 ---
    notes = Counter(t["note"] for t in by["newline_in_cell"].values())
    print("[2] セル内改行の内訳:", dict(notes))
    rows = calc["lo_exact__standard"]["newline_in_cell"]
    missed_notes = Counter(by["newline_in_cell"][r["id"]]["note"]
                           for r in rows if not r["pred_diff"])
    print("    Calc EXACT が見逃した行の内訳:", dict(missed_notes))
    rows = py["pandas_normalized"]["newline_in_cell"]
    missed_notes2 = Counter(by["newline_in_cell"][r["id"]]["note"]
                            for r in rows if not r["pred_diff"])
    print("    正規化比較が見逃した行の内訳:", dict(missed_notes2), "\n")

    # --- 3. 空白 ---
    notes = Counter(t["note"] for t in by["space_diff"].values())
    print("[3] 空白の内訳:", dict(notes))
    rows = py["pandas_normalized"]["space_diff"]
    hit_notes = Counter(by["space_diff"][r["id"]]["note"] for r in rows if r["pred_diff"])
    print("    正規化比較でも検出できた行の内訳:", dict(hit_notes), "\n")

    # --- 4. 先頭ゼロ ---
    ts = list(by["leading_zero"].values())
    same_as_number = sum(1 for t in ts if int(t["value_a"]) == int(t["value_b"]))
    print(f"[4] 先頭ゼロ: 数値にすると同じ値になる行 {same_as_number}/{len(ts)}")
    print(f"    例: {ts[0]['value_a']!r} と {ts[0]['value_b']!r} "
          f"→ どちらも {int(ts[0]['value_a'])}\n")

    # --- 5. 対照群がすべての手法で検出できているか（測定系が生きている確認）---
    print("[5] 対照群（まったく別の値）の検出率:")
    ok = True
    for method, cats in list(calc.items()) + list(py.items()):
        rows = cats.get("control_diff")
        if not rows:
            continue
        hit = sum(1 for r in rows if r["pred_diff"])
        if hit != len(rows):
            ok = False
            print(f"    ! {method}: {hit}/{len(rows)} ← 対照群を取りこぼしている")
    print("    すべての手法で全件検出" if ok else "    取りこぼしあり（上記）")

    # --- 6. same 列の誤検出 ---
    print("\n[6] 完全一致列での誤検出:")
    bad = False
    for method, cats in list(calc.items()) + list(py.items()):
        rows = cats.get("same")
        if not rows:
            continue
        fp = sum(1 for r in rows if r["pred_diff"])
        if fp:
            bad = True
            print(f"    ! {method}: {fp}/{len(rows)}")
    print("    どの手法も誤検出ゼロ" if not bad else "")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "main")
