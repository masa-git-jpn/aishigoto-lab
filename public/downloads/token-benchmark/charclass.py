#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「なぜその数字になるのか」を文字種で切り分ける。

カテゴリ別の比率は、その文章に含まれる文字種の混ざり方に左右されるので、
それだけでは原因が分からない。ここでは3つの角度から測る。

  A. 1文字だけを単独で符号化したときのトークン数
     → その文字が「単体でいくらか」。1トークン未満にはならないので最低が1
  B. コーパスに実際に出てきた「同じ文字種が連続する塊」ごとの1文字あたりトークン数
     → カタカナ語や漢字熟語が、まとまりとしてどれだけ圧縮されるか（いちばん実務に近い）
  C. 全角英数と半角英数の同じ内容での比較

出力: results_charclass.json
"""
import json
import re
import unicodedata
from collections import Counter

from corpus import CORPUS
from tokenizers_setup import LABEL, ORDER, load_all

HIRAGANA = [chr(c) for c in range(0x3041, 0x3097)]
KATAKANA = [chr(c) for c in range(0x30A1, 0x30FB)]
ASCII_ALNUM = [chr(c) for c in range(0x30, 0x3A)] + \
              [chr(c) for c in range(0x41, 0x5B)] + [chr(c) for c in range(0x61, 0x7B)]
FULLWIDTH_ALNUM = [chr(ord(c) + 0xFEE0) for c in ASCII_ALNUM]
PUNCT_JA = list("、。「」『』・ー〜（）　！？：；")
EMOJI = list("😀😂👍🙏🎉🔥✅❌📈📉🚀💡")
# まれな漢字（常用漢字表に無いもの中心）。単体コストの対比用
RARE_KANJI = list("薔薇憂鬱贔屓齟齬邂逅慟哭燦爛驟雨黎鵺麒麟纏")


def kanji_from_corpus():
    """コーパスに実際に出てきた漢字を頻度順に集める（人工的な選び方をしないため）。"""
    cnt = Counter()
    for texts in CORPUS.values():
        for t in texts:
            for ch in t:
                if 0x4E00 <= ord(ch) <= 0x9FFF:
                    cnt[ch] += 1
    return [c for c, _ in cnt.most_common()]


def single_char_cost(chars, tk):
    """A. 1文字ずつ単独で符号化する。"""
    out = {}
    for name in ORDER:
        counts = [len(tk[name].encode(c)) for c in chars]
        dist = Counter(counts)
        out[name] = {
            "n_chars": len(chars),
            "mean": round(sum(counts) / len(chars), 3),
            "dist": {str(k): dist[k] for k in sorted(dist)},
        }
    return out


CLASS_PATTERNS = {
    "ひらがな": r"[ぁ-ゖー]{2,}",
    "カタカナ": r"[ァ-ヺー]{2,}",
    "漢字": r"[一-鿿]{2,}",
    "半角英数": r"[A-Za-z0-9]{2,}",
}


def runs_from_corpus(tk):
    """B. 同じ文字種が続く塊を取り出して、まとまりとしての効率を測る。"""
    out = {}
    for cls, pat in CLASS_PATTERNS.items():
        runs = []
        for texts in CORPUS.values():
            for t in texts:
                runs += re.findall(pat, t)
        chars = sum(len(r) for r in runs)
        rec = {"n_runs": len(runs), "chars": chars,
               "mean_len": round(chars / len(runs), 2) if runs else 0,
               "examples": [r for r in sorted(set(runs), key=len, reverse=True)[:6]],
               "ratio": {}}
        for name in ORDER:
            tokens = sum(len(tk[name].encode(r)) for r in runs)
            rec["ratio"][name] = round(tokens / chars, 3)
            rec.setdefault("tokens", {})[name] = tokens
        out[cls] = rec
    return out


FULLWIDTH_SAMPLES = [
    ("ＡＢＣ１２３", "ABC123"),
    ("ＳＫＵ－２０２４－Ａ１００", "SKU-2024-A100"),
    ("２０２６年１０月３日", "2026年10月3日"),
    ("株式会社ＡＢＣ商事", "株式会社ABC商事"),
    ("金額は４８，０００円です", "金額は48,000円です"),
]


def fullwidth_vs_halfwidth(tk):
    """C. 全角と半角。中身は同じでもトークン数が変わるか。"""
    rows = []
    for fw, hw in FULLWIDTH_SAMPLES:
        rec = {"full": fw, "half": hw, "chars_full": len(fw), "chars_half": len(hw),
               "tokens": {}}
        for name in ORDER:
            rec["tokens"][name] = {"full": len(tk[name].encode(fw)),
                                   "half": len(tk[name].encode(hw))}
        rows.append(rec)
    return rows


if __name__ == "__main__":
    tk = load_all()
    kanji = kanji_from_corpus()

    sets = {
        "ひらがな": HIRAGANA,
        "カタカナ": KATAKANA,
        "漢字（コーパスに出たもの）": kanji,
        "漢字（まれなもの）": RARE_KANJI,
        "半角英数": ASCII_ALNUM,
        "全角英数": FULLWIDTH_ALNUM,
        "約物・記号": PUNCT_JA,
        "絵文字": EMOJI,
    }
    single = {k: single_char_cost(v, tk) for k, v in sets.items()}
    runs = runs_from_corpus(tk)
    fw = fullwidth_vs_halfwidth(tk)

    out = {"single_char": single, "runs": runs, "fullwidth": fw,
           "set_sizes": {k: len(v) for k, v in sets.items()},
           "kanji_used": "".join(kanji)}
    with open("results_charclass.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("=== A. 1文字を単独で符号化したときの平均トークン数 ===")
    head = f"{'文字種':24s}{'字数':>5}" + "".join(f"{n.replace('_base',''):>14}" for n in ORDER)
    print(head)
    for k, v in single.items():
        line = f"{k:24s}{v[ORDER[0]]['n_chars']:>5}"
        for n in ORDER:
            line += f"{v[n]['mean']:>14.2f}"
        print(line)

    print("\n=== B. コーパスに出てきた「同じ文字種の連なり」の1文字あたりトークン数 ===")
    print(head.replace("文字種", "連なり"))
    for k, v in runs.items():
        line = f"{k:24s}{v['chars']:>5}"
        for n in ORDER:
            line += f"{v['ratio'][n]:>14.2f}"
        print(line)
        print(f"    例: {' / '.join(v['examples'][:4])}")

    print("\n=== C. 全角 vs 半角（o200k / cl100k / claude_legacy）===")
    for r in fw:
        o = r["tokens"]["o200k_base"]; c = r["tokens"]["cl100k_base"]; cl = r["tokens"]["claude_legacy"]
        print(f"  {r['full']}  →  {r['half']}")
        print(f"    o200k {o['full']:>3} → {o['half']:>3}    "
              f"cl100k {c['full']:>3} → {c['half']:>3}    "
              f"claude {cl['full']:>3} → {cl['half']:>3}")
    print("\n保存: results_charclass.json")
