#!/usr/bin/env python3
"""コーパスCSVに7手法をかけて、カテゴリ×手法の集計表を作る。"""
import argparse
import csv
import json
from collections import defaultdict

from methods import METHODS


def load(path):
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        return list(r)


def truthy(s):
    return s in ("True", "true", "1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()

    rows = load(f"corpus/{args.prefix}.csv")

    # category -> kind, truth(全行で同じはず), total
    cat_meta = {}
    for r in rows:
        cat = r["category"]
        cat_meta.setdefault(cat, {"kind": r["kind"], "truth": truthy(r["truth_danger"]), "n": 0})
        cat_meta[cat]["n"] += 1

    # method x category -> detected count ("危険と判定した"件数)
    table = defaultdict(lambda: defaultdict(int))
    mismatches = defaultdict(list)  # method -> [ (id, category) ... ] 誤検出(false positive)の実例

    for r in rows:
        cat = r["category"]
        kind = r["kind"]
        a, b = r["name_a"], r["name_b"]
        for mname, m in METHODS.items():
            if kind == "pair":
                flagged = m["eq"](a, b)
            else:  # single
                flagged = not m["valid"](b)
            if flagged:
                table[mname][cat] += 1
                if not cat_meta[cat]["truth"]:
                    mismatches[mname].append((r["id"], cat, a, b))

    out = {
        "prefix": args.prefix,
        "categories": {c: {"kind": v["kind"], "truth_danger": v["truth"], "n": v["n"]} for c, v in cat_meta.items()},
        "methods": {m: METHODS[m]["label"] for m in METHODS},
        "detected": {m: dict(table[m]) for m in METHODS},
        "false_positive_examples": {m: v[:5] for m, v in mismatches.items()},
        "false_positive_counts": {m: len(v) for m, v in mismatches.items()},
    }
    with open(f"results/summary_{args.prefix}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 人間が読む用のテキスト表も出す
    cats = list(cat_meta.keys())
    with open(f"results/summary_{args.prefix}.txt", "w", encoding="utf-8") as f:
        header = "method".ljust(20) + "".join(c.ljust(22) for c in cats)
        f.write(header + "\n")
        for mname in METHODS:
            line = mname.ljust(20)
            for c in cats:
                n = cat_meta[c]["n"]
                d = table[mname].get(c, 0)
                line += f"{d}/{n}".ljust(22)
            f.write(line + "\n")

    print(f"wrote results/summary_{args.prefix}.json and .txt")
    print(json.dumps(out["detected"], ensure_ascii=False, indent=2))
    print("false positive counts:", out["false_positive_counts"])


if __name__ == "__main__":
    main()
