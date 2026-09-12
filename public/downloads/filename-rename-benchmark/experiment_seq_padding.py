#!/usr/bin/env python3
"""
深掘り実験2: 連番の桁揃え無しによる「取り違え」。

写真1.jpg ... 写真K.jpg (桁揃え無し、K=元の撮影順そのまま) を、
「今の並び順のまま」3桁ゼロ埋めに振り直すスクリプトを想定する。

危険なのは、その「今の並び順」を得る方法として
sorted(os.listdir(...)) のような素朴な文字列ソートを使った場合。
文字列としては "10" が "2" より前に来るため、本来の順番とズレる。

このズレは名前の「衝突」ではない(振り直した後の名前は必ず重複しない
全単射になる)ので、このスクリプトで使った7手法のどれをかけても
「危険」を1件も検出できないことを、実際に7手法を再利用して確認する。
"""
import json

from methods import METHODS  # noqa: E402


def natural_key(name):
    import re

    m = re.match(r"^(\D*)(\d+)(\D*)$", name)
    if not m:
        return (name, 0)
    return (m.group(1), int(m.group(2)), m.group(3))


def run_folder(k, seed):
    import random

    rng = random.Random(seed)
    numbers = list(range(1, k + 1))
    rng.shuffle(numbers)  # ディレクトリに現れる生成順(=実際の撮影順)をランダム化
    filenames = [f"写真{n}.jpg" for n in numbers]

    # 「正しい」順序: ファイル名に埋め込まれた数値そのものが元の順番を表す
    correct_order = sorted(filenames, key=natural_key)
    correct_target = {fn: f"写真{i+1:03d}.jpg" for i, fn in enumerate(correct_order)}

    # 「素朴」な順序: 文字列としての辞書順(os.listdir + sorted() をそのまま使うとこうなる)
    naive_order = sorted(filenames)
    naive_target = {fn: f"写真{i+1:03d}.jpg" for i, fn in enumerate(naive_order)}

    mismatches = sum(1 for fn in filenames if correct_target[fn] != naive_target[fn])

    # 全単射チェック: 振り直した後の名前に重複が無いか(無いはず)
    naive_targets_list = list(naive_target.values())
    is_bijective = len(set(naive_targets_list)) == len(naive_targets_list)

    # 7手法をこの「新しい名前の集合」に対してかけて、何件が「危険」と判定されるか
    detected_any = 0
    for i in range(len(naive_targets_list)):
        for j in range(i + 1, len(naive_targets_list)):
            a, b = naive_targets_list[i], naive_targets_list[j]
            for m in METHODS.values():
                if m["eq"](a, b):
                    detected_any += 1
    for name in naive_targets_list:
        for m in METHODS.values():
            if not m["valid"](name):
                detected_any += 1

    return {
        "k": k,
        "mismatches": mismatches,
        "is_bijective": is_bijective,
        "detected_any_danger": detected_any,
    }


def main():
    results = []
    for k in [10, 23, 50, 99, 150, 300]:
        for seed in range(5):
            results.append(run_folder(k, seed=1000 * k + seed))

    total_files = sum(r["k"] for r in results)
    total_mismatch = sum(r["mismatches"] for r in results)
    total_detected = sum(r["detected_any_danger"] for r in results)
    all_bijective = all(r["is_bijective"] for r in results)

    out = {
        "folders_tested": len(results),
        "total_files": total_files,
        "total_mismatched_files": total_mismatch,
        "mismatch_rate": round(total_mismatch / total_files, 4),
        "all_renames_bijective_no_name_collision": all_bijective,
        "total_flagged_by_any_of_7_methods": total_detected,
        "per_folder": results,
    }
    with open("results/seq_padding_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "per_folder"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
