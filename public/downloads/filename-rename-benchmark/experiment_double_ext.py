#!/usr/bin/env python3
"""
深掘り実験1: 拡張子の大文字小文字を区別する endswith() チェックが
二重拡張子を生むかどうかを、実際に関数を書いて測る。

シナリオ: 「.pdf で終わっていなければ .pdf を足す」という
よくある正規化スクリプトを2通り(バグ版/修正版)で実装し、
実務にありがちな拡張子の大文字小文字ゆれを持つファイル名の集合に適用する。
そのあと、「拡張子を除いた本体名」で元のファイルを引き直す
後工程(発注元マスタとの突合、を想定)が何件壊れるかを数える。
"""
import json
import random

rng = random.Random(20260912)

WORDS = ["請求書", "見積書", "スキャン", "契約書", "検収書", "納品書", "議事録"]


def buggy_normalize(name: str, target: str = ".pdf") -> str:
    if not name.endswith(target):
        return name + target
    return name


def safe_normalize(name: str, target: str = ".pdf") -> str:
    if not name.lower().endswith(target.lower()):
        return name + target
    return name


def make_corpus(n):
    # 実務ではスキャナやカメラアプリの既定設定で拡張子の大文字小文字が混ざる
    ext_variants = [".pdf", ".Pdf", ".PDF", ".pDf"]
    weights = [0.55, 0.10, 0.30, 0.05]  # 現場観測に基づく仮定ではなく、検証用に決め打ち
    rows = []
    for i in range(n):
        stem = f"{rng.choice(WORDS)}_{i:04d}"
        e = rng.choices(ext_variants, weights=weights, k=1)[0]
        rows.append((stem, f"{stem}{e}"))
    return rows


def stem_only(name: str) -> str:
    """後工程: 「拡張子を1つ取り除いた」つもりの単純なsplitext"""
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


def main():
    n = 5000
    corpus = make_corpus(n)  # [(original_stem, filename_with_case_variant_ext), ...]

    buggy_results = [buggy_normalize(fn) for _, fn in corpus]
    safe_results = [safe_normalize(fn) for _, fn in corpus]

    double_ext_count = sum(1 for r in buggy_results if r.lower().endswith(".pdf.pdf"))
    safe_double_ext_count = sum(1 for r in safe_results if r.lower().endswith(".pdf.pdf"))

    # 後工程: 「本体名」で発注元マスタ(original stemの辞書)を引き直す
    master = {stem: True for stem, _ in corpus}
    buggy_lookup_fail = sum(1 for r in buggy_results if stem_only(r) not in master)
    safe_lookup_fail = sum(1 for r in safe_results if stem_only(r) not in master)

    # バグの再現性: 同じ壊れたファイルにもう一度buggy_normalizeをかけても増殖しないか
    reapplied = [buggy_normalize(r) for r in buggy_results]
    reapply_grows = sum(1 for a, b in zip(buggy_results, reapplied) if len(b) > len(a))

    ext_case_breakdown = {}
    for (_, fn), r in zip(corpus, buggy_results):
        e = fn[fn.rfind(".") :]
        ext_case_breakdown.setdefault(e, {"n": 0, "doubled": 0})
        ext_case_breakdown[e]["n"] += 1
        if r.lower().endswith(".pdf.pdf"):
            ext_case_breakdown[e]["doubled"] += 1

    out = {
        "n": n,
        "buggy_double_ext_count": double_ext_count,
        "safe_double_ext_count": safe_double_ext_count,
        "buggy_lookup_fail": buggy_lookup_fail,
        "safe_lookup_fail": safe_lookup_fail,
        "reapply_grows_further": reapply_grows,
        "ext_case_breakdown": ext_case_breakdown,
        "example_buggy": [
            {"original": fn, "after_buggy": r}
            for (_, fn), r in zip(corpus, buggy_results)
            if r.lower().endswith(".pdf.pdf")
        ][:5],
    }
    with open("results/double_ext_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
