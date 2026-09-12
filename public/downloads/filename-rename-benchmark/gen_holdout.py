#!/usr/bin/env python3
"""
ホールドアウト用コーパス生成(本番とは別スクリプト)。

score.py / methods.py は本番から一切変更しない。
ここでは本番よりも意地悪な派生パターンを追加している。
"""
import argparse
import csv
import random
import unicodedata

rng = random.Random()

RESERVED = (
    ["CON", "PRN", "AUX", "NUL"] + [f"COM{i}" for i in range(1, 10)] + [f"LPT{i}" for i in range(1, 10)]
)
DAKUTEN_CHARS = list("がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽヴ")
WORDS = ["決裁書", "議事メモ", "Photo", "Invoice", "検査記録", "Draft", "納品明細"]


def rint(a, b):
    return rng.randint(a, b)


# A1': 大文字小文字違い。ただし「拡張子だけ」が違うパターンを追加(本番は本体側中心だった)
def gen_a1(n):
    rows = []
    for i in range(n):
        stem = f"{rng.choice(WORDS)}_{rint(1,9999)}"
        e = rng.choice(["pdf", "PDF", "xlsx", "Docx"])
        a = f"{stem}.{e.lower()}"
        b = f"{stem}.{e.upper() if rng.random()<0.5 else e}"
        if a == b:
            b = f"{stem}.{e.swapcase()}"
        assert a.lower() == b.lower()
        if a != b:
            rows.append(("A1_case", a, b, "pair", True))
    return rows


# A2': NFD側にさらに濁点を2つ以上重ねた語や、半濁点混在を追加
def gen_a2(n):
    rows = []
    for i in range(n):
        w = rng.choice(WORDS)
        dak1 = rng.choice(DAKUTEN_CHARS)
        dak2 = rng.choice(DAKUTEN_CHARS)
        stem = f"{w}{dak1}{dak2}_{rint(1,999)}"
        a_nfc = unicodedata.normalize("NFC", f"{stem}.docx")
        b_nfd = unicodedata.normalize("NFD", a_nfc)
        if a_nfc != b_nfd:
            rows.append(("A2_nfc_nfd", a_nfc, b_nfd, "pair", True))
    return rows


# A3': 全角半角混在 + 記号(＿ vs _、－ vs -)も追加
def gen_a3(n):
    rows = []
    fw = str.maketrans(
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-",
        "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ＿－",
    )
    for i in range(n):
        stem = f"{rng.choice(WORDS)}-{rint(1,999)}_v2"
        a = f"{stem}.xlsx"
        b = a.translate(fw)
        if a != b:
            rows.append(("A3_fullwidth", a, b, "pair", True))
    return rows


# B1': 予約語 + 二重拡張子("com1.tar.gz"のような、拡張子が複数あるケース)
def gen_b1(n):
    rows = []
    for i in range(n):
        word = rng.choice(RESERVED)
        style = rng.choice([str.upper, str.lower, str.title])
        w = style(word)
        ext_choice = rng.choice(["tar.gz", "pdf", "", "xlsx.bak"])
        name = f"{w}.{ext_choice}" if ext_choice else w
        rows.append(("B1_reserved", "", name, "single", True))
    return rows


def gen_b1_nearmiss(n):
    rows = []
    near = ["CONFIG", "COMBO", "COMMAND", "AUXILIARY", "NULLPTR", "LPT10", "COM99"]
    for i in range(n):
        w = rng.choice(near)
        name = f"{rng.choice([str.upper, str.lower, str.title])(w)}_{rint(1,999)}.dat"
        rows.append(("B1n_reserved_nearmiss", "", name, "single", False))
    return rows


# B2': 末尾ピリオド/スペースの複合(スペース+ピリオド、ピリオド+スペース)
def gen_b2(n):
    rows = []
    for i in range(n):
        stem = f"{rng.choice(WORDS)}_{rint(1,999)}"
        pattern = rng.choice([" .", ". ", "..", "  "])
        name = f"{stem}.pdf{pattern}"
        assert name[-1] in (" ", ".")
        rows.append(("B2_trailing", "", name, "single", True))
    return rows


def gen_d0(n):
    rows = []
    for i in range(n):
        a = f"{rng.choice(WORDS)}_{rint(1,999)}.pdf"
        rows.append(("D0_exact_dup", a, a, "pair", True))
    return rows


def gen_d1(n):
    rows = []
    for i in range(n):
        a = f"{rng.choice(WORDS)}_{rint(1,999)}.pdf"
        b = f"{rng.choice(WORDS)}_{rint(1,999)}.xlsx"
        while b == a:
            b = f"{rng.choice(WORDS)}_{rint(1,999)}.xlsx"
        rows.append(("D1_unrelated", a, b, "pair", False))
    return rows


def gen_d2():
    pairs = [
        ("湿度５０％.txt", "湿度50%.txt"),
        ("第Ⅳ四半期.pptx", "第IV四半期.pptx"),
        ("価格㌫表示.csv", "価格パーセント表示.csv"),
    ]
    rows = []
    for a, b in pairs:
        if unicodedata.normalize("NFKC", a) == unicodedata.normalize("NFKC", b):
            rows.append(("D2_nfkc_risk", a, b, "pair", False))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rng.seed(args.seed)

    rows = []
    rows += gen_a1(args.n)
    rows += gen_a2(args.n)
    rows += gen_a3(args.n)
    rows += gen_b1(args.n)
    rows += gen_b1_nearmiss(max(100, args.n // 5))
    rows += gen_b2(args.n)
    rows += gen_d0(args.n)
    rows += gen_d1(args.n)
    rows += gen_d2()

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "category", "name_a", "name_b", "kind", "truth_danger"])
        for i, (cat, a, b, kind, truth) in enumerate(rows):
            w.writerow([i, cat, a, b, kind, truth])
    print(f"generated {len(rows)} rows -> {args.out} (seed={args.seed})")


if __name__ == "__main__":
    main()
