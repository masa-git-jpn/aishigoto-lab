#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
トークナイザーを全部ローカルファイルから組み立てる。

この環境は huggingface.co と openaipublic.blob.core.windows.net に出られないので、
語彙ファイルは PyPI / npm / GitHub から取得している。
**OpenAI の4種類は、tiktoken パッケージに同梱されている公式のSHA-256と
バイト単位で一致することを確認済み**（download_vocab.py がその照合をする）。

使えるトークナイザー:
  o200k_base   GPT-4o / GPT-4.1 / o系（OpenAI 現行）
  cl100k_base  GPT-4 / GPT-3.5-turbo（OpenAI 一世代前）
  p50k_base    GPT-3（text-davinci-003 など）
  r50k_base    GPT-3 初期 / GPT-2
  gemma        Google が公開している Gemma の SentencePiece モデル
  claude_legacy Claude 1〜2 世代の公開トークナイザー（npm @anthropic-ai/tokenizer）

現行の Claude と Gemini のトークナイザーは公開されていないため測れない。
"""
import base64
import json
import os

import tiktoken

VOCAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab")

# tiktoken 側の定義（pat_str と特殊トークンはパッケージの定義に合わせる）
ENDOFTEXT = "<|endoftext|>"
FIM_PREFIX = "<|fim_prefix|>"
FIM_MIDDLE = "<|fim_middle|>"
FIM_SUFFIX = "<|fim_suffix|>"
ENDOFPROMPT = "<|endofprompt|>"

R50K_PAT = (
    r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}++| ?\p{N}++| ?[^\s\p{L}\p{N}]++|\s++$|\s+(?!\S)|\s"""
)
CL100K_PAT = (
    r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++|\p{N}{1,3}"""
    r"""| ?[^\s\p{L}\p{N}]++[\r\n]*|\s++$|\s*[\r\n]|\s+(?!\S)|\s"""
)
O200K_PAT = "|".join([
    r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
    r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
    r"""\p{N}{1,3}""",
    r""" ?[^\s\p{L}\p{N}]+[\r\n/]*""",
    r"""\s*[\r\n]+""",
    r"""\s+(?!\S)""",
    r"""\s+""",
])


def _load_bpe(path):
    """.tiktoken 形式（base64 rank）を読む。"""
    ranks = {}
    with open(path, "rb") as f:
        for line in f:
            if not line.strip():
                continue
            token, rank = line.split()
            ranks[base64.b64decode(token)] = int(rank)
    return ranks


def load_openai(name):
    path = os.path.join(VOCAB, f"{name}.tiktoken")
    ranks = _load_bpe(path)
    if name == "o200k_base":
        pat, special = O200K_PAT, {ENDOFTEXT: 199999, ENDOFPROMPT: 200018}
    elif name == "cl100k_base":
        pat = CL100K_PAT
        special = {ENDOFTEXT: 100257, FIM_PREFIX: 100258, FIM_MIDDLE: 100259,
                   FIM_SUFFIX: 100260, ENDOFPROMPT: 100276}
    else:
        pat, special = R50K_PAT, {ENDOFTEXT: 50256}
    return tiktoken.Encoding(name=name, pat_str=pat, mergeable_ranks=ranks,
                             special_tokens=special)


class ClaudeLegacy:
    """
    npm の @anthropic-ai/tokenizer に入っている claude.json から組み立てる。

    bpe_ranks は空白区切りのbase64だが、**先頭2要素（"!" と "5"）だけはbase64ではない**
    ヘッダなので読み飛ばす。この読み方が正しいことは、パッケージ同梱のテスト
    （hello world!=3 / ™=1 / ϰ=1 / <EOT>=1）を4件とも再現して確認した。

    本家の countTokens() は encode の前に **NFKC正規化** をかけているので、それも再現する。
    日本語では全角英数が半角に変換されるため、これを省くと数が変わる。
    """

    def __init__(self):
        with open(os.path.join(VOCAB, "claude_legacy.json"), encoding="utf-8") as f:
            d = json.load(f)
        parts = d["bpe_ranks"].split(" ")
        ranks = {base64.b64decode(t): i for i, t in enumerate(parts[2:])}
        self.enc = tiktoken.Encoding(name="claude_legacy", pat_str=d["pat_str"],
                                     mergeable_ranks=ranks,
                                     special_tokens=d["special_tokens"])
        self.name = "claude_legacy"

    def encode(self, text):
        import unicodedata
        return self.enc.encode(unicodedata.normalize("NFKC", text),
                               allowed_special="all")

    @property
    def n_vocab(self):
        return self.enc.n_vocab


def load_claude_legacy():
    return ClaudeLegacy()


class SpmWrapper:
    """SentencePiece を tiktoken と同じ使い勝手にする薄い包み。"""

    def __init__(self, path, name):
        import sentencepiece as spm
        self.sp = spm.SentencePieceProcessor()
        self.sp.Load(path)
        self.name = name

    def encode(self, text):
        return self.sp.EncodeAsIds(text)

    def encode_pieces(self, text):
        return self.sp.EncodeAsPieces(text)

    @property
    def n_vocab(self):
        return self.sp.GetPieceSize()


def load_all():
    tk = {}
    for n in ["o200k_base", "cl100k_base", "p50k_base", "r50k_base"]:
        tk[n] = load_openai(n)
    tk["claude_legacy"] = load_claude_legacy()
    tk["gemma"] = SpmWrapper(os.path.join(VOCAB, "gemma_tokenizer.model"), "gemma")
    return tk


# 記事・表で使う表示名（どのモデルのものか誤解されないよう明示する）
LABEL = {
    "o200k_base": "o200k_base（GPT-4o / GPT-4.1 / o系）",
    "cl100k_base": "cl100k_base（GPT-4 / GPT-3.5-turbo）",
    "p50k_base": "p50k_base（GPT-3 davinci 系）",
    "r50k_base": "r50k_base（GPT-2 / GPT-3 初期）",
    "claude_legacy": "Claude 1〜2 世代（現行Claudeは非公開）",
    "gemma": "Gemma（Google公開。Geminiのものではない）",
}
ORDER = ["r50k_base", "p50k_base", "cl100k_base", "o200k_base", "claude_legacy", "gemma"]


if __name__ == "__main__":
    tk = load_all()
    s = "この請求書の合計金額を確認してください。"
    print(f"サンプル文（{len(s)}文字）: {s}\n")
    for n in ORDER:
        ids = tk[n].encode(s)
        print(f"{LABEL[n]:42s} 語彙 {tk[n].n_vocab:>7,}  {len(ids):>3}トークン  "
              f"1文字あたり {len(ids)/len(s):.2f}")
