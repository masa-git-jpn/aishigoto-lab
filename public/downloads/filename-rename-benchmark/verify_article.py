#!/usr/bin/env python3
"""
記事本文に書いた数字を、結果ファイルと機械的に突合する。
記事6・7で確立したやり方(公開前に必ず実行する)。

1件でも食い違えば非ゼロ終了する。
"""
import json
import sys

ERRORS = []


def check(label, actual, expected):
    if actual != expected:
        ERRORS.append(f"[NG] {label}: 記事の記載={expected!r} / 結果ファイル={actual!r}")
    else:
        print(f"[OK] {label}: {actual!r}")


def main():
    main_j = json.load(open("results/summary_main.json", encoding="utf-8"))
    holdout_j = json.load(open("results/summary_holdout.json", encoding="utf-8"))
    dext = json.load(open("results/double_ext_result.json", encoding="utf-8"))
    seqp = json.load(open("results/seq_padding_result.json", encoding="utf-8"))
    chain = json.load(open("results/chain_rename_result.json", encoding="utf-8"))

    cats = main_j["categories"]
    check("本番: カテゴリ数", len(cats), 9)
    check("本番: A1件数", cats["A1_case"]["n"], 2000)
    check("本番: A2件数", cats["A2_nfc_nfd"]["n"], 2000)
    check("本番: A3件数", cats["A3_fullwidth"]["n"], 2000)
    check("本番: B1件数", cats["B1_reserved"]["n"], 2000)
    check("本番: B1にせもの件数", cats["B1n_reserved_nearmiss"]["n"], 400)
    check("本番: B2件数", cats["B2_trailing"]["n"], 2000)
    check("本番: D0件数", cats["D0_exact_dup"]["n"], 2000)
    check("本番: D1件数", cats["D1_unrelated"]["n"], 2000)
    check("本番: D2件数", cats["D2_nfkc_risk"]["n"], 4)
    total_main = sum(v["n"] for v in cats.values())
    check("本番: 総行数", total_main, 14404)

    det = main_j["detected"]
    # M1: 素朴な文字列比較 -> D0以外は全滅
    check("M1: A1検出数", det["M1_naive_str"].get("A1_case", 0), 0)
    check("M1: D0検出数", det["M1_naive_str"].get("D0_exact_dup", 0), 2000)
    # M2: lower
    check("M2: A1検出数", det["M2_lower"].get("A1_case", 0), 2000)
    check("M2: A2検出数", det["M2_lower"].get("A2_nfc_nfd", 0), 0)
    # M3: NFC
    check("M3: A2検出数", det["M3_nfc"].get("A2_nfc_nfd", 0), 2000)
    check("M3: A1検出数", det["M3_nfc"].get("A1_case", 0), 0)
    # M4: lower+NFC
    check("M4: A1検出数", det["M4_lower_nfc"].get("A1_case", 0), 2000)
    check("M4: A2検出数", det["M4_lower_nfc"].get("A2_nfc_nfd", 0), 2000)
    check("M4: A3検出数", det["M4_lower_nfc"].get("A3_fullwidth", 0), 0)
    # M5: NFKC+casefold
    check("M5: A3検出数", det["M5_nfkc_casefold"].get("A3_fullwidth", 0), 2000)
    check("M5: B1検出数", det["M5_nfkc_casefold"].get("B1_reserved", 0), 0)
    # M6: pathvalidate
    check("M6: B1検出数", det["M6_pathvalidate"].get("B1_reserved", 0), 2000)
    check("M6: B2検出数", det["M6_pathvalidate"].get("B2_trailing", 0), 2000)
    check("M6: D0検出数(重複判定をしないので0のはず)", det["M6_pathvalidate"].get("D0_exact_dup", 0), 0)
    # M7: フル装備は全部満点
    for c in ["A1_case", "A2_nfc_nfd", "A3_fullwidth", "B1_reserved", "B2_trailing", "D0_exact_dup"]:
        check(f"M7: {c}検出数", det["M7_full"].get(c, 0), 2000)

    fp = main_j["false_positive_counts"]
    check("誤検出: D1/B1にせもの/M1〜M4/M6での誤検出件数キー数", len(fp), 2)
    check("誤検出: M5のD2誤検出件数", fp.get("M5_nfkc_casefold", 0), 4)
    check("誤検出: M7のD2誤検出件数", fp.get("M7_full", 0), 4)

    # ホールドアウト(本番と同じ構造で件数だけ違う)
    hcats = holdout_j["categories"]
    check("ホールドアウト: A1件数", hcats["A1_case"]["n"], 500)
    check("ホールドアウト: D2件数", hcats["D2_nfkc_risk"]["n"], 3)
    hdet = holdout_j["detected"]
    check("ホールドアウト: M1のA1検出数", hdet["M1_naive_str"].get("A1_case", 0), 0)
    check("ホールドアウト: M7のB1検出数", hdet["M7_full"].get("B1_reserved", 0), 500)
    hfp = holdout_j["false_positive_counts"]
    check("ホールドアウト: M5誤検出件数", hfp.get("M5_nfkc_casefold", 0), 3)

    # 二重拡張子
    check("二重拡張子: 母数", dext["n"], 5000)
    check("二重拡張子: バグ版の発生件数", dext["buggy_double_ext_count"], 2201)
    check("二重拡張子: バグ版の後工程突合失敗件数", dext["buggy_lookup_fail"], 2201)
    check("二重拡張子: 修正版の発生件数", dext["safe_double_ext_count"], 0)
    check("二重拡張子: 修正版の後工程突合失敗件数", dext["safe_lookup_fail"], 0)
    check("二重拡張子: 再適用しても増殖しない", dext["reapply_grows_further"], 0)

    # 連番の桁揃え
    check("連番: 対象フォルダ数", seqp["folders_tested"], 30)
    check("連番: 総ファイル数", seqp["total_files"], 3160)
    check("連番: 取り違え件数", seqp["total_mismatched_files"], 3080)
    check("連番: 全単射(名前の重複なし)", seqp["all_renames_bijective_no_name_collision"], True)
    check("連番: 7手法で検出できた件数", seqp["total_flagged_by_any_of_7_methods"], 0)

    # 連鎖リネーム(実ファイル)
    check("連鎖: 試行数", chain["trials"], 56)
    check("連鎖: 関与した総ファイル数", chain["total_files_involved"], 432)
    check("連鎖: 辞書順実行での消失件数", chain["total_lost_naive_order"], 50)
    check("連鎖: 番号順実行での消失件数", chain["total_lost_safe_order"], 0)
    check("連鎖: 消失が起きたバッチ数", chain["batches_with_any_loss"], 25)

    print()
    if ERRORS:
        print(f"{len(ERRORS)}件の食い違いがあります:")
        for e in ERRORS:
            print(" ", e)
        sys.exit(1)
    print("すべての数値が一致しました。")


if __name__ == "__main__":
    main()
