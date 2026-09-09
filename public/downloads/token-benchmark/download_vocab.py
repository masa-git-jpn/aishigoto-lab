#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
語彙ファイルを取得して、本物かどうかを照合する。

この検証環境からは配布元（openaipublic / huggingface.co）に接続できなかったため、
OpenAIの4ファイルは GitHub のミラーから取得している。
**ただし取得後に、tiktoken パッケージ同梱の公式SHA-256と照合している。**
一致すれば、配布元のファイルとバイト単位で同一であることが保証される。
一致しなければ、その場で止める。

接続できる環境であれば、配布元から直接取ってきて vocab/ に置いても構わない
（SHA-256が同じであれば結果は変わらない）。
"""
import hashlib
import os
import sys
import urllib.request

VOCAB = "vocab"

# tiktoken パッケージ（tiktoken_ext/openai_public.py）に書かれている公式のSHA-256。
# 手で写したものではなく、インストール済みのパッケージから読み出して照合もできる。
OPENAI = {
    "cl100k_base.tiktoken": (
        "https://raw.githubusercontent.com/zurawiki/tiktoken-rs/main/tiktoken-rs/assets/cl100k_base.tiktoken",
        "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"),
    "o200k_base.tiktoken": (
        "https://raw.githubusercontent.com/zurawiki/tiktoken-rs/main/tiktoken-rs/assets/o200k_base.tiktoken",
        "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"),
    "p50k_base.tiktoken": (
        "https://raw.githubusercontent.com/zurawiki/tiktoken-rs/main/tiktoken-rs/assets/p50k_base.tiktoken",
        "94b5ca7dff4d00767bc256fdd1b27e5b17361d7b8a5f968547f9f23eb70d2069"),
    "r50k_base.tiktoken": (
        "https://raw.githubusercontent.com/zurawiki/tiktoken-rs/main/tiktoken-rs/assets/r50k_base.tiktoken",
        "306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930"),
}

GEMMA = ("gemma_tokenizer.model",
         "https://raw.githubusercontent.com/google/gemma_pytorch/main/tokenizer/tokenizer.model")

CLAUDE_NPM = "https://registry.npmjs.org/@anthropic-ai/tokenizer/-/tokenizer-0.0.4.tgz"


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def fetch(url, path):
    print(f"  取得中 {os.path.basename(path)} …", end="", flush=True)
    with urllib.request.urlopen(url, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())
    print(f" {os.path.getsize(path):,} バイト")


def official_hashes_from_package():
    """インストール済みの tiktoken から公式ハッシュを読み出す（写し間違い防止）。"""
    try:
        import inspect
        import re
        import tiktoken_ext.openai_public as p
        src = inspect.getsource(p)
        return set(re.findall(r'hash="([0-9a-f]{64})"', src))
    except Exception:
        return None


if __name__ == "__main__":
    os.makedirs(VOCAB, exist_ok=True)
    ng = []

    pkg_hashes = official_hashes_from_package()
    if pkg_hashes:
        for fn, (_, h) in OPENAI.items():
            if h not in pkg_hashes:
                ng.append(f"{fn}: このスクリプトのハッシュが tiktoken パッケージの定義に無い")
        print("tiktoken パッケージ同梱のハッシュと突き合わせ: "
              f"{'OK' if not ng else 'NG'}")
    else:
        print("(tiktoken が入っていないのでパッケージ側との突き合わせは省略)")

    print("\nOpenAI の語彙ファイル")
    for fn, (url, expect) in OPENAI.items():
        path = os.path.join(VOCAB, fn)
        if not os.path.exists(path):
            fetch(url, path)
        got = sha256(path)
        if got == expect:
            print(f"  OK   {fn}  SHA-256 一致")
        else:
            print(f"  NG   {fn}  期待={expect[:16]}… 実際={got[:16]}…")
            ng.append(fn)

    print("\nGemma の SentencePiece モデル")
    gpath = os.path.join(VOCAB, GEMMA[0])
    if not os.path.exists(gpath):
        fetch(GEMMA[1], gpath)
    print(f"  取得済み {os.path.getsize(gpath):,} バイト  SHA-256 {sha256(gpath)[:16]}…")
    print("  （配布元に公式のハッシュが示されていないため、照合はできない。"
          "語彙数が公表値の256,000であることを verify.py で確認している）")

    print("\nClaude 1〜2 世代（npm パッケージから claude.json を取り出す）")
    cpath = os.path.join(VOCAB, "claude_legacy.json")
    if not os.path.exists(cpath):
        import io
        import tarfile
        print("  取得中 tokenizer-0.0.4.tgz …", end="", flush=True)
        with urllib.request.urlopen(CLAUDE_NPM, timeout=180) as r:
            buf = io.BytesIO(r.read())
        print(f" {buf.getbuffer().nbytes:,} バイト")
        with tarfile.open(fileobj=buf, mode="r:gz") as tf:
            m = tf.extractfile("package/claude.json")
            open(cpath, "wb").write(m.read())
    print(f"  取得済み {os.path.getsize(cpath):,} バイト  SHA-256 {sha256(cpath)[:16]}…")
    print("  （正しく読めているかは、パッケージ同梱のテスト4件の再現で確認する→ verify.py）")

    print()
    if ng:
        print("!!! 照合に失敗したファイルがあります。使わないでください !!!")
        for x in ng:
            print("  -", x)
        sys.exit(1)
    print("すべて照合できました。")
