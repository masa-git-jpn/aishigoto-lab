#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ホールドアウト用のコーパス生成（本番の集計コードを書き終えたあとに作る）。

gen_corpus.py とは別のスクリプトで、列の構成（＝集計コードから見た形）は同じまま、
中に入れる差分のパターンだけを「見たことのないもの」に差し替える。
run_python_methods.py / run_shell_methods.py / run_calc_methods.py / score.py は
1文字も変更せずにこのデータへ当てる。

本番と違うところ:
  digit16_last     16桁だけでなく 17桁・18桁も混ぜる。末尾1桁ではなく末尾2桁違いも混ぜる
  leading_zero     先頭ゼロ1個だけでなく2個・3個も混ぜる。桁数も変える
  space_diff       タブ文字・ゼロ幅スペース（U+200B）・ノーブレークスペース（U+00A0）を追加
  width_diff       全角化する範囲を一部だけにしたもの（部分的な全角混在）を追加
  case_diff        全部小文字ではなく1文字だけ大小が違うものを追加
  newline_in_cell  CRのみ（旧Mac系）の改行と、末尾に改行が付いたものを追加
  control_diff     長さの違う別値（桁数まで違う）も混ぜる
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

_HALF = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
TO_FULL = {ord(c): chr(ord(c) + 0xFEE0) for c in _HALF}

SEI = ["青木", "石川", "上田", "遠藤", "大野", "岡田", "笠原", "菊池", "工藤", "小島",
       "坂本", "柴田", "杉山", "関口", "外山", "谷口", "千葉", "津田", "寺田", "戸田"]
MEI = ["一郎", "薫", "京子", "圭介", "沙織", "俊介", "静香", "聡", "千尋", "剛",
       "奈々", "信夫", "初音", "文彦", "穂積", "牧子", "美穂", "百合", "洋介", "良太"]


def digits(rng, n, first_nonzero=True):
    if first_nonzero:
        return rng.choice("123456789") + "".join(rng.choice("0123456789") for _ in range(n - 1))
    return "".join(rng.choice("0123456789") for _ in range(n))


def code(rng, letters=2, nums=6):
    return ("".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(letters))
            + digits(rng, nums, first_nonzero=False))


def pair(rng, category, seen):
    for _ in range(60):
        if category == "same":
            v = digits(rng, rng.choice([16, 17, 18]))
            if v in seen:
                continue
            return v, v, "常に完全一致（誤検出の測定用・桁数は16〜18でばらつかせた）"

        if category == "control_diff":
            a = digits(rng, rng.choice([16, 17, 18]))
            if a in seen:
                continue
            b = code(rng, rng.choice([2, 3, 4]), rng.choice([6, 9, 12]))
            return a, b, "対照群：まったく別の値（桁数も違う）"

        if category == "digit16_last":
            ln = rng.choice([16, 17, 18])
            a = digits(rng, ln)
            if a in seen:
                continue
            if rng.random() < 0.5:
                last = a[-1]
                nl = rng.choice([d for d in "0123456789" if d != last])
                b = a[:-1] + nl
                note = f"{ln}桁番号の末尾1桁違い（{last}→{nl}）"
            else:
                tail = a[-2:]
                nt = tail
                while nt == tail:
                    nt = digits(rng, 2, first_nonzero=False)
                b = a[:-2] + nt
                note = f"{ln}桁番号の末尾2桁違い（{tail}→{nt}）"
            return a, b, note

        if category == "leading_zero":
            nz = rng.choice([1, 2, 3])
            body = digits(rng, rng.choice([7, 9, 11]))
            a = "0" * nz + body
            if a in seen:
                continue
            return a, str(int(a)), f"先頭ゼロ{nz}個の消失"

        if category == "space_diff":
            base = code(rng, 2, 7)
            if base in seen:
                continue
            v = rng.choice(["tab", "zwsp", "nbsp", "trail_full", "lead_half"])
            if v == "tab":
                return base, base + "\t", "末尾にタブ文字"
            if v == "zwsp":
                m = len(base) // 2
                return base, base[:m] + "​" + base[m:], "中間にゼロ幅スペース(U+200B)"
            if v == "nbsp":
                return base, " " + base, "先頭にノーブレークスペース(U+00A0)"
            if v == "trail_full":
                return base, base + "　", "末尾に全角スペース"
            return base, " " + base, "先頭に半角スペース"

        if category == "width_diff":
            base = code(rng, 3, 6)
            if base in seen:
                continue
            if rng.random() < 0.5:
                return base, base.translate(TO_FULL), "全体を全角化"
            m = len(base) // 2
            return base, base[:m] + base[m:].translate(TO_FULL), "後半だけ全角化（全角半角の混在）"

        if category == "case_diff":
            letters = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4))
            nums = digits(rng, 6, first_nonzero=False)
            a = letters + nums
            if a in seen:
                continue
            if rng.random() < 0.5:
                return a, letters.lower() + nums, "英字を全部小文字に"
            i = rng.randrange(len(letters))
            b = letters[:i] + letters[i].lower() + letters[i + 1:] + nums
            return a, b, f"英字{i + 1}文字目だけ小文字"

        if category == "newline_in_cell":
            base = code(rng, 2, 5)
            if base in seen:
                continue
            v = rng.choice(["cr_only", "trailing_lf", "insert_crlf", "cr_vs_lf"])
            if v == "cr_only":
                return base, base[:3] + "\r" + base[3:], "セル内にCRのみの改行"
            if v == "trailing_lf":
                return base, base + "\n", "末尾に改行が1個付いている"
            if v == "insert_crlf":
                return base, base[:3] + "\r\n" + base[3:], "セル内にCRLF改行が混入"
            return base[:3] + "\r" + base[3:], base[:3] + "\n" + base[3:], "同じ内容だがCRとLFで違う"

        raise ValueError(category)
    raise RuntimeError(category)


def build(n, seed, out_prefix):
    rng = random.Random(seed)
    nrng = random.Random(seed + 7)
    seen = {c: set() for c in CATEGORIES}
    rows_a, rows_b, truth = [], [], []

    for i in range(n):
        rid = i + 1
        base = {"id": rid,
                "登録日": f"2026-{nrng.randrange(1, 13):02d}-{nrng.randrange(1, 29):02d}",
                "顧客名": SEI[nrng.randrange(len(SEI))] + " " + MEI[nrng.randrange(len(MEI))],
                "金額": nrng.randrange(1000, 999999)}
        ra, rb = dict(base), dict(base)
        for cat in CATEGORIES:
            col = CATEGORY_COLUMN[cat]
            va, vb, note = pair(rng, cat, seen[cat])
            seen[cat].add(va)
            if cat == "same":
                assert va == vb
            else:
                assert va != vb, (cat, va, vb)
            ra[col], rb[col] = va, vb
            truth.append({"id": rid, "category": cat, "column": col, "value_a": va,
                          "value_b": vb, "expect_diff": va != vb, "note": note})
        rows_a.append(ra)
        rows_b.append(rb)

    fields = ["id", "登録日", "顧客名", "金額"] + [CATEGORY_COLUMN[c] for c in CATEGORIES]
    for side, rows in (("a", rows_a), ("b", rows_b)):
        with open(f"{out_prefix}_{side}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    with open(f"{out_prefix}_truth.json", "w", encoding="utf-8") as f:
        json.dump(truth, f, ensure_ascii=False, indent=1)
    print(out_prefix, "行数:", n)
    print(Counter(t["category"] for t in truth))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args()
    build(a.n, a.seed, a.out_prefix)
