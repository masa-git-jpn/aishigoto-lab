#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測定そのものが正しいかを機械的に確かめる。数え間違いを記事に載せないための検算。

1. 語彙ファイルが本物か（tiktokenパッケージ同梱の公式SHA-256と一致するか）
2. 符号化して復号すると元の文字列に戻るか（取りこぼしがないか）
3. 語彙サイズが公表値と一致するか
4. 対照群の英語が既知の水準（1トークンあたり約4文字）に収まっているか
5. Claude旧版の再構成が、公式パッケージのテスト4件を再現するか
6. カテゴリ合計が、文章ごとの合計と一致するか
"""
import hashlib
import json
import os
import sys
import unicodedata

from corpus import CONTROL_EN, CORPUS
from tokenizers_setup import ORDER, load_all

OFFICIAL_SHA256 = {
    "cl100k_base.tiktoken": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
    "o200k_base.tiktoken": "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d",
    "p50k_base.tiktoken": "94b5ca7dff4d00767bc256fdd1b27e5b17361d7b8a5f968547f9f23eb70d2069",
    "r50k_base.tiktoken": "306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930",
}
# 公表されている語彙サイズ
EXPECTED_VOCAB = {"o200k_base": 200019, "cl100k_base": 100277,
                  "p50k_base": 50281, "r50k_base": 50257, "gemma": 256000}

fails = []


def ok(label, cond, detail=""):
    print(("  OK   " if cond else "  NG   ") + label + (f"  {detail}" if detail else ""))
    if not cond:
        fails.append(label + " " + detail)


print("=== 1. 語彙ファイルが本物か（公式SHA-256との照合）===")
for fn, exp in OFFICIAL_SHA256.items():
    p = os.path.join("vocab", fn)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    ok(f"{fn}", h == exp, h[:16] + "…")

print("\n=== 2. 符号化→復号で元に戻るか ===")
tk = load_all()
samples = [t for texts in CORPUS.values() for t in texts] + CONTROL_EN
for name in ["o200k_base", "cl100k_base", "p50k_base", "r50k_base"]:
    bad = [s[:20] for s in samples if tk[name].decode(tk[name].encode(s)) != s]
    ok(f"{name} 全{len(samples)}本が完全に復元", not bad, f"崩れた例={bad[:1]}")
# Claude旧版はNFKC正規化をかけてから符号化するので、戻り先は正規化後の文字列
bad = [s[:20] for s in samples
       if tk["claude_legacy"].enc.decode(tk["claude_legacy"].encode(s))
       != unicodedata.normalize("NFKC", s)]
ok("claude_legacy 全本が正規化後の文字列に復元", not bad, f"崩れた例={bad[:1]}")

print("\n=== 3. 語彙サイズが公表値と一致するか ===")
for name, exp in EXPECTED_VOCAB.items():
    ok(f"{name} = {exp:,}", tk[name].n_vocab == exp, f"実測={tk[name].n_vocab:,}")

print("\n=== 4. 対照群の英語が既知の水準か（1トークン=約4文字）===")
for name in ORDER:
    chars = sum(len(t) for t in CONTROL_EN)
    tokens = sum(len(tk[name].encode(t)) for t in CONTROL_EN)
    cpt = chars / tokens
    ok(f"{name} 1トークンあたり {cpt:.2f} 文字", 3.5 <= cpt <= 6.0, f"比率={tokens/chars:.3f}")

print("\n=== 5. Claude旧版の再構成が公式テストを再現するか ===")
for text, exp in [("hello world!", 3), ("™", 1), ("ϰ", 1), ("<EOT>", 1)]:
    got = len(tk["claude_legacy"].encode(text))
    ok(f"countTokens({text!r}) = {exp}", got == exp, f"実測={got}")

print("\n=== 6. 集計が合っているか ===")
if os.path.exists("results_corpus_main.json"):
    d = json.load(open("results_corpus_main.json", encoding="utf-8"))
    for name in ORDER:
        per_text = sum(r["tokens"][name] for r in d["rows"])
        per_cat = sum(c["tokens"][name] for c in d["categories"].values())
        ok(f"{name} 文章ごとの合計 == カテゴリごとの合計", per_text == per_cat,
           f"{per_text} vs {per_cat}")
    # 数え直し（別経路）
    tk2 = load_all()
    recount = sum(len(tk2["o200k_base"].encode(t)) for t in samples)
    stored = sum(r["tokens"]["o200k_base"] for r in d["rows"])
    ok("o200k を読み込み直して数え直しても同じ", recount == stored, f"{recount} vs {stored}")
else:
    print("  (results_corpus_main.json が無いので飛ばす)")

print()
if fails:
    print("!!! 問題あり !!!")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("すべて通りました。")
