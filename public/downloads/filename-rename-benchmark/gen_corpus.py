#!/usr/bin/env python3
"""
記事8本目「ファイル名を一括で変える前に、危険な名前が混ざっていないか測った」
本番コーパス生成。

正解が分かる (name_a, name_b) のペア、または単体の候補名 (name_b) を、
カテゴリごとに大量に作る。すべて生成時に assert で正解を保証する。
"""
import argparse
import csv
import random
import unicodedata

# ---- 実務っぽい語彙プール -------------------------------------------------
JP_WORDS = [
    "議事録", "見積書", "請求書", "契約書", "報告書", "会議資料", "提案書",
    "仕様書", "作業手順", "検収書", "納品書", "稟議書", "経費精算", "議案",
    "スキャン", "写真", "バックアップ", "台帳", "名簿", "議事", "決裁",
]
EN_WORDS = [
    "Invoice", "Report", "Draft", "Final", "Summary", "Photo", "Scan",
    "Backup", "Minutes", "Proposal", "Contract", "Receipt", "Memo",
]
EXTS = ["pdf", "xlsx", "docx", "csv", "jpg", "png", "zip"]
DEPTS = ["営業一課", "営業二課", "経理部", "総務部", "開発部", "品質管理"]

# NFDで書くと2コードポイントになる濁点・半濁点つき仮名(NFC側の代表例)
DAKUTEN_CHARS = list(
    "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽヴガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ"
)

# Windows予約語(拡張子の有無・大小文字を問わず、ベース名が完全一致すると危険)
RESERVED = (
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{i}" for i in range(1, 10)]
    + [f"LPT{i}" for i in range(1, 10)]
)

rng = random.Random()


def rint(a, b):
    return rng.randint(a, b)


def base_stem(use_en=None):
    """実務っぽいファイル名の「本体」部分(拡張子抜き)を1つ作る"""
    if use_en is None:
        use_en = rng.random() < 0.35
    if use_en:
        w = rng.choice(EN_WORDS)
        n = rint(1, 999)
        if rng.random() < 0.5:
            return f"{w}_{2026}{rint(1,12):02d}{rint(1,28):02d}_{n:03d}"
        return f"{w}-{n}"
    w = rng.choice(JP_WORDS)
    d = rng.choice(DEPTS)
    n = rint(1, 999)
    return f"{d}_{w}_{n}"


def ext():
    return rng.choice(EXTS)


# ---------------------------------------------------------------------------
# A1: 大文字小文字だけが違う名前 (ASCII, ペア, truth=collide)
# ---------------------------------------------------------------------------
def gen_a1(n):
    rows = []
    for i in range(n):
        stem = base_stem(use_en=True)
        e = ext()
        a = f"{stem}.{e}"
        # 名前のどこか1箇所以上の英字の大小をランダムに反転させる
        chars = list(a)
        idx_letters = [j for j, c in enumerate(chars) if c.isalpha() and ord(c) < 128]
        flip_n = max(1, len(idx_letters) // 3)
        for j in rng.sample(idx_letters, min(flip_n, len(idx_letters))):
            c = chars[j]
            chars[j] = c.lower() if c.isupper() else c.upper()
        b = "".join(chars)
        assert a != b, "大文字小文字を反転させたのに文字列が変わっていない"
        assert a.lower() == b.lower(), "小文字化すれば一致するはずが一致しない"
        rows.append(("A1_case", a, b, "pair", True))
    return rows


# ---------------------------------------------------------------------------
# A2: Unicode正規化の違い (NFC vs NFD, ペア, truth=collide)
# ---------------------------------------------------------------------------
def gen_a2(n):
    rows = []
    for i in range(n):
        w = rng.choice(JP_WORDS + EN_WORDS)
        dak = rng.choice(DAKUTEN_CHARS)
        stem = f"{w}{dak}{rint(1,999)}"
        e = ext()
        a_nfc = unicodedata.normalize("NFC", f"{stem}.{e}")
        b_nfd = unicodedata.normalize("NFD", a_nfc)
        assert a_nfc != b_nfd, "NFCとNFDで生バイト列が同じになってしまった(濁点が無い語を引いた?)"
        assert unicodedata.normalize("NFC", b_nfd) == a_nfc, "NFD側をNFCに戻してもa_nfcと一致しない"
        rows.append(("A2_nfc_nfd", a_nfc, b_nfd, "pair", True))
    return rows


# ---------------------------------------------------------------------------
# A3: 全角・半角の混在 (視覚的に同じだが別コードポイント, ペア, truth=collide)
# ---------------------------------------------------------------------------
FULLWIDTH_MAP = str.maketrans(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
)


def gen_a3(n):
    rows = []
    for i in range(n):
        stem = base_stem(use_en=True)
        e = ext()
        a_half = f"{stem}.{e}"
        b_full = a_half.translate(FULLWIDTH_MAP)
        assert a_half != b_full, "全角化しても文字列が変わっていない(英数字を含まない語を引いた?)"
        assert unicodedata.normalize("NFKC", b_full) == a_half, "NFKCで戻しても半角側と一致しない"
        rows.append(("A3_fullwidth", a_half, b_full, "pair", True))
    return rows


# ---------------------------------------------------------------------------
# B1: Windows予約語 (単体, truth=invalid)
# ---------------------------------------------------------------------------
def gen_b1(n):
    rows = []
    # 予約語そのもの(拡張子あり/なし、大小文字違い)を必ずカバーしつつnまで埋める
    for i in range(n):
        word = rng.choice(RESERVED)
        # 大文字/小文字/先頭のみ大文字、をランダムに
        style = rng.choice(["upper", "lower", "title"])
        w = {"upper": word.upper(), "lower": word.lower(), "title": word.title()}[style]
        if rng.random() < 0.7:
            name = f"{w}.{ext()}"
        else:
            name = w  # 拡張子なし
        rows.append(("B1_reserved", "", name, "single", True))
    return rows


# 予約語との「にせもの」(基底名が完全一致ではない = 危険ではない) の対照サンプル
def gen_b1_nearmiss(n):
    rows = []
    near = ["CONTROL", "COMMENT", "COMPANY", "PRINTER", "NULLABLE", "CONCAT", "LPT1A", "COM10"]
    for i in range(n):
        w = rng.choice(near)
        style = rng.choice([str.upper, str.lower, str.title])
        name = f"{style(w)}_{rint(1,999)}.{ext()}"
        rows.append(("B1n_reserved_nearmiss", "", name, "single", False))
    return rows


# ---------------------------------------------------------------------------
# B2: 末尾のピリオド・空白 (単体, truth=invalid)
# ---------------------------------------------------------------------------
def gen_b2(n):
    rows = []
    for i in range(n):
        stem = base_stem()
        pattern = rng.choice(["dot_noext", "trailing_space_after_ext", "dot_after_ext"])
        if pattern == "dot_noext":
            name = f"{stem}."  # 拡張子を付け忘れた略語などを想定、末尾がピリオド
        elif pattern == "trailing_space_after_ext":
            name = f"{stem}.{ext()} "  # コピペ由来の末尾スペース
        else:
            name = f"{stem}.{ext()}."  # 二重ピリオドの末尾
        assert name[-1] in (" ", "."), "末尾がスペース/ピリオドになっていない"
        rows.append(("B2_trailing", "", name, "single", True))
    return rows


# ---------------------------------------------------------------------------
# D0: 対照群 - 完全に同じ名前 (ペア, truth=collide) : 検出できて当然
# ---------------------------------------------------------------------------
def gen_d0(n):
    rows = []
    for i in range(n):
        stem = base_stem()
        a = f"{stem}.{ext()}"
        rows.append(("D0_exact_dup", a, a, "pair", True))
    return rows


# ---------------------------------------------------------------------------
# D1: 対照群 - 無関係などう見ても違う名前 (ペア, truth=NOT collide) : 誤検出してはいけない
# ---------------------------------------------------------------------------
def gen_d1(n):
    rows = []
    for i in range(n):
        a = f"{base_stem()}.{ext()}"
        b = f"{base_stem()}.{ext()}"
        while b == a:
            b = f"{base_stem()}.{ext()}"
        rows.append(("D1_unrelated", a, b, "pair", False))
    return rows


# ---------------------------------------------------------------------------
# D2: 副実験 - NFKCなら「同じ」になってしまうが、本来は別物であってほしいペア
#      (truth=NOT collide のはずだが、NFKC系の手法は誤って同一視するリスクを測る)
# ---------------------------------------------------------------------------
NFKC_RISK_PAIRS = [
    ("面積_10㎡.txt", "面積_10m2.txt"),   # ㎡ -> m2 に開かれる
    ("係数Ⅲ.csv", "係数III.csv"),         # ローマ数字 -> ラテン文字列
    ("㈱山田商事.pdf", "(株)山田商事.pdf"),  # 組文字が展開される
    ("No.１２.xlsx", "No.12.xlsx"),        # 全角数字が半角化(A3と同じ効果だが意図的に別ファイルとして用意した想定)
]


def gen_d2():
    rows = []
    for a, b in NFKC_RISK_PAIRS:
        assert a != b
        assert unicodedata.normalize("NFKC", a) == unicodedata.normalize("NFKC", b), (
            f"NFKCで一致しない組み合わせが混ざっている: {a!r} {b!r}"
        )
        rows.append(("D2_nfkc_risk", a, b, "pair", False))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=2000, help="カテゴリごとの件数(D2以外)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng.seed(args.seed)

    rows = []
    rows += gen_a1(args.n)
    rows += gen_a2(args.n)
    rows += gen_a3(args.n)
    rows += gen_b1(args.n)
    rows += gen_b1_nearmiss(max(200, args.n // 5))
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
