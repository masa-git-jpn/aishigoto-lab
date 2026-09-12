#!/usr/bin/env python3
"""
深掘り実験3: 連番リネームによる自己衝突(実際にファイルを作って rename する)。

シナリオ: 連番ファイルの途中を1つ削除したあと、「欠番を詰める」ために
それより後ろの番号を1つずつ前に詰める。これは実務でよくある操作。

対応表は必ず「鎖」になる(例: 5→4, 6→5, 7→6, ...)。
鎖を昇順(4を先に埋める側から)処理すれば安全だが、
os.listdir()を素朴にsorted()しただけの辞書順で処理すると、
桁揃えの無い番号では昇順にならず、実際に os.rename() を使うと
中身が本当に上書きされて消える。

このスクリプトは /tmp に実ファイルを作り、実際に rename を実行し、
最終的にディレクトリに残った内容を読んで「失われたファイルの中身」を数える。
架空の計算ではなく実行結果。
"""
import json
import os
import random
import shutil
import tempfile


from methods import METHODS  # noqa: E402

rng = random.Random(20260912)


def run_trial(low, high, workdir):
    """low..high の連番ファイルのうち low が欠番になった状態を作り、
    high までを1つずつ前に詰めるリネームを実行する。
    戻り値: (辞書順で実行した場合に失われた件数, 安全な順序で失われた件数,
             最終的な名前の集合に重複が生じたか)
    """
    d = tempfile.mkdtemp(dir=workdir)
    # low は欠番(存在しない)。low+1..high の実ファイルを作る。
    for idx in range(low + 1, high + 1):
        with open(os.path.join(d, f"photo{idx}.jpg"), "w", encoding="utf-8") as f:
            f.write(f"CONTENT-{idx}")

    mapping = {f"photo{idx}.jpg": f"photo{idx-1}.jpg" for idx in range(low + 1, high + 1)}
    expected_final_content = {f"photo{idx-1}.jpg": f"CONTENT-{idx}" for idx in range(low + 1, high + 1)}

    def execute(order_keys, target_dir):
        for src in order_keys:
            os.replace(os.path.join(target_dir, src), os.path.join(target_dir, mapping[src]))

    def count_lost(final_dir):
        lost = 0
        for final_name, expected_content in expected_final_content.items():
            p = os.path.join(final_dir, final_name)
            if not os.path.exists(p):
                lost += 1
                continue
            with open(p, encoding="utf-8") as f:
                if f.read() != expected_content:
                    lost += 1
        return lost

    # --- 素朴な順序: sorted(os.listdir()) の文字列(辞書)順 ---
    naive_dir = d + "_naive"
    shutil.copytree(d, naive_dir)
    naive_order = sorted(os.listdir(naive_dir))  # 実際に os.listdir して得た順序を使う
    execute(naive_order, naive_dir)
    naive_lost = count_lost(naive_dir)
    naive_final_names = os.listdir(naive_dir)

    # --- 安全な順序: 番号の小さい方から処理する(必ず空きスロットに詰める) ---
    safe_dir = d + "_safe"
    shutil.copytree(d, safe_dir)
    safe_order = sorted(os.listdir(safe_dir), key=lambda s: int(s[len("photo") : -len(".jpg")]))
    execute(safe_order, safe_dir)
    safe_lost = count_lost(safe_dir)

    shutil.rmtree(d)
    shutil.rmtree(naive_dir)
    shutil.rmtree(safe_dir)

    return naive_lost, safe_lost, naive_order, naive_final_names


def main():
    workdir = tempfile.mkdtemp(prefix="chain_rename_")
    trials = []
    # 3桁までの範囲でチェーンの長さと開始位置をいろいろ振る
    for length in [2, 3, 4, 5, 8, 12, 20]:
        for start in [1, 2, 8, 9, 18, 90, 95, 98]:
            low = start
            high = start + length
            trials.append((low, high))

    total_files = 0
    total_lost_naive = 0
    total_lost_safe = 0
    batches_with_loss = 0
    examples = []

    for low, high in trials:
        n = high - low
        total_files += n
        naive_lost, safe_lost, naive_order, naive_final_names = run_trial(low, high, workdir)
        total_lost_naive += naive_lost
        total_lost_safe += safe_lost
        if naive_lost > 0:
            batches_with_loss += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "range": [low, high],
                        "n_files": n,
                        "lost": naive_lost,
                        "listdir_sorted_order_used": naive_order,
                    }
                )

        # このバッチの「最終的な名前の集合」に対して7手法をかけて、何か引っかかるか確認
        for name in naive_final_names:
            for m in METHODS.values():
                if not m["valid"](name):
                    raise AssertionError(f"想定外: {name} が単体チェックで無効判定された")
        # 重複(衝突)チェック: 最終的な名前どうしが衝突していないか
        assert len(set(naive_final_names)) == len(naive_final_names), "最終的な名前に重複が生じた"

    shutil.rmtree(workdir, ignore_errors=True)

    out = {
        "trials": len(trials),
        "total_files_involved": total_files,
        "total_lost_naive_order": total_lost_naive,
        "total_lost_safe_order": total_lost_safe,
        "batches_with_any_loss": batches_with_loss,
        "loss_rate_naive": round(total_lost_naive / total_files, 4),
        "no_detector_flagged_final_names": True,
        "note": "最終的なファイル名の集合はどの試行でも重複していない(全単射)。"
        "7手法のいずれも「危険」と判定できるものは無い。",
        "examples_of_loss": examples,
    }
    with open("results/chain_rename_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "examples_of_loss"}, ensure_ascii=False, indent=2))
    print("\n--- examples ---")
    print(json.dumps(examples, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
