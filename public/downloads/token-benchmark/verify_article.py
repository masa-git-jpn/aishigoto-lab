#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""記事に書いた数字が、実際の結果ファイルと一致するかを機械的に確かめる。"""
import json
import sys

MD = open("japanese-token-count-measured.md", encoding="utf-8").read()
M = json.load(open("results_corpus_main.json", encoding="utf-8"))
H = json.load(open("results_corpus_holdout.json", encoding="utf-8"))
C = json.load(open("results_charclass.json", encoding="utf-8"))
R = json.load(open("results_rewrite.json", encoding="utf-8"))
ORDER = M["order"]

fails = []


def check(label, expected, actual):
    if expected != actual:
        fails.append(f"{label}: 記事={expected} 実測={actual}")
        print(f"  NG   {label}  記事={expected} 実測={actual}")
    else:
        print(f"  OK   {label} = {actual}")


def ja_ratio(d, name):
    ch = sum(c["chars"] for k, c in d["categories"].items() if not k.startswith("対照群"))
    tk = sum(c["tokens"][name] for k, c in d["categories"].items() if not k.startswith("対照群"))
    return tk / ch


def r2(x):
    """記事の表記に合わせた四捨五入（0.715 → 0.72）。"""
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


print("--- 1. 本文の主表（日本語・本番）---")
for name, exp in [("r50k_base", 1.37), ("p50k_base", 1.37), ("cl100k_base", 0.97),
                  ("o200k_base", 0.71), ("claude_legacy", 0.97), ("gemma", 0.58)]:
    check(f"日本語 {name}", exp, r2(ja_ratio(M, name)))

print("--- 2. 対照群の英語 ---")
en = M["categories"]["対照群：英語"]
for name, exp in [("r50k_base", 0.20), ("cl100k_base", 0.20), ("o200k_base", 0.20),
                  ("claude_legacy", 0.20), ("gemma", 0.19)]:
    check(f"英語 {name}", exp, r2(en["ratio"][name]))
cpt = en["chars"] / en["tokens"]["o200k_base"]
check("英語 1トークンあたりの文字数 5.1", 5.1, round(cpt, 1))

print("--- 3. 世代間の倍率 ---")
check("本番 GPT-3世代/現行 = 1.91倍", 1.91,
      round(ja_ratio(M, "r50k_base") / ja_ratio(M, "o200k_base"), 2))
check("ホールドアウト = 2.00倍", 2.0,
      round(ja_ratio(H, "r50k_base") / ja_ratio(H, "o200k_base"), 2))

print("--- 4. 日本語は英語の何倍か ---")
for name, exp in [("r50k_base", 6.9), ("cl100k_base", 5.0), ("o200k_base", 3.6), ("gemma", 3.0)]:
    check(f"{name}", exp, round(ja_ratio(M, name) / en["ratio"][name], 1))

print("--- 5. 文字種ごとの単独コスト ---")
single = C["single_char"]
expect_single = {
    "半角英数": {"r50k_base": 1.00, "cl100k_base": 1.00, "o200k_base": 1.00,
               "claude_legacy": 1.00, "gemma": 1.00},
    "全角英数": {"r50k_base": 3.00, "cl100k_base": 1.84, "o200k_base": 1.55,
               "claude_legacy": 1.00, "gemma": 1.00},
    "ひらがな": {"r50k_base": 1.66, "cl100k_base": 1.45, "o200k_base": 1.15,
              "claude_legacy": 1.50, "gemma": 1.05},
    "カタカナ": {"r50k_base": 1.28, "cl100k_base": 1.46, "o200k_base": 1.14,
              "claude_legacy": 1.58, "gemma": 1.09},
    "漢字（コーパスに出たもの）": {"r50k_base": 2.36, "cl100k_base": 1.61, "o200k_base": 1.06,
                     "claude_legacy": 1.47, "gemma": 1.00},
    "漢字（まれなもの）": {"r50k_base": 2.91, "cl100k_base": 2.52, "o200k_base": 1.86,
                  "claude_legacy": 2.19, "gemma": 1.00},
    "約物・記号": {"r50k_base": 1.88, "cl100k_base": 1.00, "o200k_base": 1.00,
              "claude_legacy": 1.19, "gemma": 1.00},
    "絵文字": {"r50k_base": 2.58, "cl100k_base": 2.58, "o200k_base": 1.50,
            "claude_legacy": 2.33, "gemma": 1.00},
}
for cls, vals in expect_single.items():
    for name, exp in vals.items():
        check(f"単独 {cls}/{name}", exp, r2(single[cls][name]["mean"]))
check("まれな漢字の字数 21", 21, C["set_sizes"]["漢字（まれなもの）"])
check("漢字（出たもの）の字数 466", 466, C["set_sizes"]["漢字（コーパスに出たもの）"])

print("--- 6. 文字種の連なり ---")
expect_runs = {
    "漢字": (1601, {"r50k_base": 2.24, "cl100k_base": 1.38, "o200k_base": 0.87,
                  "claude_legacy": 1.25, "gemma": 0.66}),
    "ひらがな": (1846, {"r50k_base": 1.16, "cl100k_base": 0.82, "o200k_base": 0.62,
                    "claude_legacy": 0.85, "gemma": 0.43}),
    "カタカナ": (645, {"r50k_base": 0.96, "cl100k_base": 0.92, "o200k_base": 0.61,
                   "claude_legacy": 0.96, "gemma": 0.34}),
    "半角英数": (523, {"r50k_base": 0.41, "cl100k_base": 0.38, "o200k_base": 0.38,
                   "claude_legacy": 0.37, "gemma": 0.69}),
}
for cls, (chars, vals) in expect_runs.items():
    check(f"連なり {cls} 字数", chars, C["runs"][cls]["chars"])
    for name, exp in vals.items():
        check(f"連なり {cls}/{name}", exp, r2(C["runs"][cls]["ratio"][name]))

print("--- 7. 全角 vs 半角 ---")
fw = {r["full"]: r for r in C["fullwidth"]}
for full, cl, o2 in [("ＡＢＣ１２３", (9, 2), (5, 2)),
                     ("ＳＫＵ－２０２４－Ａ１００", (15, 6), (11, 6)),
                     ("株式会社ＡＢＣ商事", (13, 8), (6, 4)),
                     ("金額は４８，０００円です", (12, 9), (10, 8)),
                     ("２０２６年１０月３日", (8, 7), (8, 7))]:
    t = fw[full]["tokens"]
    check(f"{full} cl100k", list(cl), [t["cl100k_base"]["full"], t["cl100k_base"]["half"]])
    check(f"{full} o200k", list(o2), [t["o200k_base"]["full"], t["o200k_base"]["half"]])
# Claude旧とGemmaは全角と半角で同じはず
same = all(r["tokens"]["claude_legacy"]["full"] == r["tokens"]["claude_legacy"]["half"]
           for r in C["fullwidth"])
check("claude_legacy は5例すべて全角と半角で同数", True, same)
g_same = sum(1 for r in C["fullwidth"]
             if r["tokens"]["gemma"]["full"] == r["tokens"]["gemma"]["half"])
check("gemma は5例中2例が同数", 2, g_same)

print("--- 8. 書き換え ---")
rw = {r["name"]: r for r in R}
expect_rw = {
    "クッション言葉と定型の挨拶を削る": {"o200k_base": (56, 13, 77), "cl100k_base": (80, 25, 69)},
    "カタカナ語を漢語にする": {"o200k_base": (23, 15, 35), "cl100k_base": (36, 23, 36)},
    "表を罫線からCSVにする": {"o200k_base": (39, 28, 28), "cl100k_base": (56, 30, 46)},
    "丁寧語をやめて体言止めにする": {"o200k_base": (46, 34, 26), "cl100k_base": (65, 47, 28)},
    "全角英数を半角にする": {"o200k_base": (29, 23, 21), "cl100k_base": (38, 27, 29)},
    "漢数字をアラビア数字にする": {"o200k_base": (32, 28, 12), "cl100k_base": (41, 35, 15)},
    "繰り返す長い固有名詞を短縮して定義する": {"o200k_base": (39, 35, 10), "cl100k_base": (62, 49, 21)},
    "全角スペースのインデントをやめる": {"o200k_base": (42, 42, 0), "cl100k_base": (61, 60, 2)},
}
for nm, vals in expect_rw.items():
    for tok, (b, a, pct) in vals.items():
        t = rw[nm]["tokens"][tok]
        check(f"書き換え {nm}/{tok}", [b, a, pct], [t["before"], t["after"], round(t["cut_pct"])])
for tok, exp in [("o200k_base", 28.8), ("cl100k_base", 32.6)]:
    b = sum(r["tokens"][tok]["before"] for r in R)
    a = sum(r["tokens"][tok]["after"] for r in R)
    check(f"合計削減率 {tok}", exp, round((b - a) / b * 100, 1))
# Gemmaで逆に増えた施策
g_ind = rw["全角スペースのインデントをやめる"]["tokens"]["gemma"]["cut_pct"]
g_num = rw["漢数字をアラビア数字にする"]["tokens"]["gemma"]["cut_pct"]
check("Gemma 字下げで6%増", -6.0, round(g_ind, 0))
check("Gemma 漢数字で8%増", -8.0, round(g_num, 0))

print("--- 9. ホールドアウト ---")
for name, exp in [("r50k_base", 1.54), ("cl100k_base", 1.08), ("o200k_base", 0.77),
                  ("claude_legacy", 1.08), ("gemma", 0.56)]:
    check(f"ホールドアウト {name}", exp, r2(ja_ratio(H, name)))
check("ホールドアウトの文字数", 3691,
      sum(c["chars"] for k, c in H["categories"].items() if not k.startswith("対照群")))
check("日本語の合計文字数", 9676,
      sum(c["chars"] for k, c in M["categories"].items() if not k.startswith("対照群"))
      + sum(c["chars"] for k, c in H["categories"].items() if not k.startswith("対照群")))
check("日本語の本数", 40,
      sum(1 for r in M["rows"] if not r["category"].startswith("対照群"))
      + sum(1 for r in H["rows"] if not r["category"].startswith("対照群")))

print("--- 10. 16ジャンルでの幅 ---")
allper = {}
for src, tag in [(M, "本番"), (H, "HO")]:
    for cat, c in src["categories"].items():
        if cat.startswith("対照群"):
            continue
        allper[f"{tag}/{cat}"] = c["ratio"]
check("ジャンル数", 16, len(allper))
for name, lo, hi, over in [("r50k_base", 0.93, 1.77, 15), ("cl100k_base", 0.67, 1.18, 11),
                           ("o200k_base", 0.54, 0.85, 0), ("gemma", 0.44, 0.78, 0)]:
    vals = [v[name] for v in allper.values()]
    check(f"{name} 最小", lo, r2(min(vals)))
    check(f"{name} 最大", hi, r2(max(vals)))
    check(f"{name} 1.0以上のジャンル数", over, sum(1 for v in vals if v >= 1.0))
check("o200k の最大は議事録・箇条書き", "本番/議事録・箇条書き",
      max(allper, key=lambda k: allper[k]["o200k_base"]))

print("--- 11. 本文に数字が載っているか ---")
for needle in ["1.37", "0.97", "0.71", "0.58", "1.91", "2.00", "6.9", "5.0", "3.6",
               "5.1", "1.55", "1.86", "0.87", "0.61", "9 → 2", "77%", "28.8%", "32.6%",
               "0.54 〜 0.85", "9,676", "3,691", "16ジャンル"]:
    if needle not in MD:
        fails.append(f"本文に見つからない: {needle}")
        print(f"  NG   本文に {needle} が無い")
    else:
        print(f"  OK   本文に {needle} がある")

print("--- 12. 強調が壊れていないか（記事6で見つけた不具合の再発防止）---")
check("本文に ** が残っていない", 0, MD.split("---", 2)[2].count("**"))

print()
if fails:
    print("!!! 不一致 !!!")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("すべて一致しました。")
