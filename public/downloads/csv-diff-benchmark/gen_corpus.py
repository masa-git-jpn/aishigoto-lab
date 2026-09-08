#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV差分ベンチマーク: コーパス生成（列ベース設計）

file_a.csv / file_b.csv を作る。id で行が対応する2つのCSV。
各行は id・登録日・顧客名・金額（AB共通、飾り）に加えて、
「差分の種類ごとに専用の列」を1本ずつ持つ。列を分けているのは、
実務のCSVでは列ごとに書式が揃っている（1列の中に数値っぽい値と
文字っぽい値が混在することは普通ない）ため。1列にすると
pandasや表計算ソフトの列単位の型推定が働かず、検証したい
「型推定による取りこぼし」自体が起きなくなってしまう。

列と、その列に仕込む差分:
    確認用番号      : 常に一致（same。誤検出＝偽陽性の測定用）
    対照用コード    : 常に別物（control_diff。検出できて当然の対照群）
    照合番号        : 16桁番号の末尾1桁だけ違う（digit16_last。本命の仮説）
    商品コード      : 先頭ゼロの消失（leading_zero）
    得意先コード    : 前後/全角半角スペースの有無（space_diff）
    型番            : 半角英数字 vs 全角英数字（width_diff）
    承認者ID        : 英字の大文字/小文字違い（case_diff）
    備考            : セル内改行の有無・改行コード違い（newline_in_cell）

same 以外の列は、value_a と value_b が生の文字列として必ず異なることを
構築時にassertで保証している。つまり「正解」は常に「異なる」
（same 列だけ「同じ」）。truth.json に列ごとの正解を1行1レコードで記録する。

使い方:
    python3 gen_corpus.py --n 10000 --seed 20260908    --out-prefix main
    python3 gen_corpus.py --n 2000  --seed 999999999   --out-prefix holdout
"""
import argparse
import csv
import json
import random
from collections import Counter

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
CATEGORIES = list(CATEGORY_COLUMN.keys())

_HALF_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
HALF_TO_FULL = {ord(c): chr(ord(c) + 0xFEE0) for c in _HALF_CHARS}

SEI = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤",
       "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水"]
MEI = ["太郎", "次郎", "花子", "美咲", "健一", "陽子", "大輔", "由美", "翔太", "真由美",
       "拓也", "恵子", "隆", "直樹", "香織", "亮", "麻衣", "健太", "彩", "誠"]


def rand_digits(rng, n, first_nonzero=True):
    if first_nonzero:
        return rng.choice("123456789") + "".join(rng.choice("0123456789") for _ in range(n - 1))
    return "".join(rng.choice("0123456789") for _ in range(n))


def rand_alnum_code(rng, letters=2, digits=6):
    lp = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(letters))
    dp = rand_digits(rng, digits, first_nonzero=False)
    return lp + dp


def make_value_pair(rng, category, seen):
    """(value_a, value_b, note) を返す。同一列内で value_a の重複が出ないよう seen で管理。"""
    for _ in range(50):
        if category == "same":
            v = rand_digits(rng, 16)
            if v in seen:
                continue
            return v, v, "常に完全一致（偽陽性＝誤検出の測定用）"

        if category == "control_diff":
            a = rand_digits(rng, 16)
            if a in seen:
                continue
            b = rand_alnum_code(rng, 3, 10)
            return a, b, "対照群：まったく別の値。検出できなければ手法自体が壊れている"

        if category == "digit16_last":
            a = rand_digits(rng, 16)
            if a in seen:
                continue
            last = a[-1]
            new_last = rng.choice([d for d in "0123456789" if d != last])
            b = a[:-1] + new_last
            return a, b, f"16桁番号の末尾1桁のみ違う（{last}→{new_last}）"

        if category == "leading_zero":
            digits = "0" + rand_digits(rng, 9, first_nonzero=True)
            if digits in seen:
                continue
            a = digits
            b = str(int(digits))
            return a, b, "先頭ゼロの消失（テキストのまま vs 数値化されて消失）"

        if category == "space_diff":
            base = rand_alnum_code(rng, 2, 7)
            if base in seen:
                continue
            variant = rng.choice(["trailing_half", "leading_half", "trailing_full", "double_mid"])
            if variant == "trailing_half":
                b, note = base + " ", "末尾に半角スペース1個"
            elif variant == "leading_half":
                b, note = " " + base, "先頭に半角スペース1個"
            elif variant == "trailing_full":
                b, note = base + "　", "末尾に全角スペース1個"
            else:
                mid = len(base) // 2
                b, note = base[:mid] + "  " + base[mid:], "中間に半角スペース2個混入"
            return base, b, note

        if category == "width_diff":
            base = rand_alnum_code(rng, 3, 6)
            if base in seen:
                continue
            return base, base.translate(HALF_TO_FULL), "半角英数字 vs 全角英数字（見た目は同じ文字列）"

        if category == "case_diff":
            letters = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(3))
            digits = rand_digits(rng, 6, first_nonzero=False)
            a = letters + digits
            if a in seen:
                continue
            return a, letters.lower() + digits, "英字部分の大文字/小文字違い"

        if category == "newline_in_cell":
            base = rand_alnum_code(rng, 2, 5)
            if base in seen:
                continue
            variant = rng.choice(["insert_lf", "insert_crlf", "crlf_vs_lf"])
            if variant == "insert_lf":
                a, b, note = base, base[:3] + "\n" + base[3:], "セル内にLF改行が混入"
            elif variant == "insert_crlf":
                a, b, note = base, base[:3] + "\r\n" + base[3:], "セル内にCRLF改行が混入"
            else:
                a = base[:3] + "\r\n" + base[3:]
                b = base[:3] + "\n" + base[3:]
                note = "同じ内容だが改行コードがCRLFとLFで違う"
            return a, b, note

        raise ValueError(category)
    raise RuntimeError(f"衝突が多すぎる: {category}")


def build(n, seed, out_prefix):
    rng = random.Random(seed)
    name_rng = random.Random(seed + 1)

    seen_by_cat = {c: set() for c in CATEGORIES}
    rows_a, rows_b, truth = [], [], []

    for i in range(n):
        rid = i + 1
        kojin = SEI[name_rng.randrange(len(SEI))] + " " + MEI[name_rng.randrange(len(MEI))]
        kingaku = name_rng.randrange(1000, 999999)
        m = name_rng.randrange(1, 13)
        d = name_rng.randrange(1, 29)
        touroku_bi = f"2026-{m:02d}-{d:02d}"

        row_a = {"id": rid, "登録日": touroku_bi, "顧客名": kojin, "金額": kingaku}
        row_b = {"id": rid, "登録日": touroku_bi, "顧客名": kojin, "金額": kingaku}

        for category in CATEGORIES:
            col = CATEGORY_COLUMN[category]
            va, vb, note = make_value_pair(rng, category, seen_by_cat[category])
            seen_by_cat[category].add(va)
            if category == "same":
                assert va == vb
            else:
                assert va != vb, (category, va, vb)
            row_a[col] = va
            row_b[col] = vb
            truth.append({
                "id": rid, "category": category, "column": col,
                "value_a": va, "value_b": vb,
                "expect_diff": va != vb, "note": note,
            })

        rows_a.append(row_a)
        rows_b.append(row_b)

    fieldnames = ["id", "登録日", "顧客名", "金額"] + [CATEGORY_COLUMN[c] for c in CATEGORIES]
    with open(f"{out_prefix}_a.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_a)
    with open(f"{out_prefix}_b.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_b)
    with open(f"{out_prefix}_truth.json", "w", encoding="utf-8") as f:
        json.dump(truth, f, ensure_ascii=False, indent=1)

    print(out_prefix, "行数:", n, "true件数(=n*8):", len(truth))
    print(Counter(t["category"] for t in truth))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()
    build(args.n, args.seed, args.out_prefix)
