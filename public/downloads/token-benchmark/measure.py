#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コーパスを6つのトークナイザーにかけて、1文字あたりのトークン数を数える。

出力: results_corpus_<prefix>.json
"""
import argparse
import importlib
import json

from tokenizers_setup import LABEL, ORDER, load_all


def measure(texts, tk):
    rows = []
    for cat, idx, text in texts:
        chars = len(text)
        rec = {"category": cat, "index": idx, "chars": chars, "tokens": {}, "ratio": {}}
        for name in ORDER:
            n = len(tk[name].encode(text))
            rec["tokens"][name] = n
            rec["ratio"][name] = round(n / chars, 4)
        rows.append(rec)
    return rows


def aggregate(rows):
    """カテゴリごとに合計してから比率を出す（文章ごとの比率を平均しない）。"""
    cats = {}
    for r in rows:
        c = cats.setdefault(r["category"], {"chars": 0, "texts": 0,
                                            "tokens": {n: 0 for n in ORDER}})
        c["chars"] += r["chars"]
        c["texts"] += 1
        for n in ORDER:
            c["tokens"][n] += r["tokens"][n]
    for c in cats.values():
        c["ratio"] = {n: round(c["tokens"][n] / c["chars"], 4) for n in ORDER}
    return cats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus", help="コーパスのモジュール名")
    ap.add_argument("--prefix", default="main")
    args = ap.parse_args()

    mod = importlib.import_module(args.corpus)
    tk = load_all()
    rows = measure(list(mod.all_texts()), tk)
    cats = aggregate(rows)

    out = {"rows": rows, "categories": cats,
           "vocab_size": {n: tk[n].n_vocab for n in ORDER},
           "labels": LABEL, "order": ORDER}
    with open(f"results_corpus_{args.prefix}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    head = f"{'カテゴリ':26s}{'文字数':>7}" + "".join(f"{n.replace('_base',''):>14}" for n in ORDER)
    print(head)
    print("-" * len(head))
    for cat, c in cats.items():
        line = f"{cat:26s}{c['chars']:>7,}"
        for n in ORDER:
            line += f"{c['ratio'][n]:>14.2f}"
        print(line)

    ja = {"chars": 0, "tokens": {n: 0 for n in ORDER}}
    for cat, c in cats.items():
        if cat.startswith("対照群"):
            continue
        ja["chars"] += c["chars"]
        for n in ORDER:
            ja["tokens"][n] += c["tokens"][n]
    line = f"{'日本語ぜんぶ':26s}{ja['chars']:>7,}"
    for n in ORDER:
        line += f"{ja['tokens'][n] / ja['chars']:>14.2f}"
    print("-" * len(head))
    print(line)
    print(f"\n保存: results_corpus_{args.prefix}.json")
