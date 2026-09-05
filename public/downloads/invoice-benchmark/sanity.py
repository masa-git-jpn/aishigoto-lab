#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測定の前提チェック：正解の文字が本当にPDFのテキスト層に載っているか。
載っていなければ抽出側の責任ではないので、その分は測定から外す必要がある。"""
import json, unicodedata
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).parent
truth = json.loads((ROOT / "truth.json").read_text(encoding="utf-8"))

def norm(s):
    return unicodedata.normalize("NFKC", s).replace(" ", "").replace("　", "")

miss = 0
for t in truth:
    with pdfplumber.open(ROOT / "pdfs" / t["file"]) as pdf:
        text = norm("\n".join((p.extract_text() or "") for p in pdf.pages))
    need = [t["invoice_no"], t["vendor"], f"{t['total']:,}"]
    need += [r["name"] for r in t["rows"]]
    lost = [x for x in need if norm(x) not in text]
    if lost:
        miss += 1
        print("MISSING", t["file"], lost[:4])
print(f"テキスト層に欠けのあるPDF: {miss} / {len(truth)}")
