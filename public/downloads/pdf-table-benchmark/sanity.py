"""生成したPDFのテキスト層に、正解の全セルが欠けずに載っているかを検査する。
   ここが通らないPDFは「抽出ライブラリの失敗」ではなく「PDFの作りが悪い」ので、
   測定対象から外すか作り直す必要がある。"""
import subprocess, unicodedata, sys
from tables import TABLES

def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return "".join(s.split())          # 空白をすべて除去して比較

ng_total = 0
for t in TABLES:
    for route in ("calc", "html"):
        pdf = f"/root/lab/pdf/pdfs/{t['id']}_{route}.pdf"
        # -layout は列を横に並べるため、折り返したセルの文字が他の列の文字で分断される。
        # 素のモード（ブロック順）と両方を見て、どちらかに含まれていれば「載っている」と判定する。
        raw = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                             capture_output=True, text=True).stdout
        plain = subprocess.run(["pdftotext", pdf, "-"],
                               capture_output=True, text=True).stdout
        flat = norm(raw); flat2 = norm(plain)
        missing = []
        for row in t["rows"]:
            for v in row:
                for piece in str(v).split("\n"):
                    p = norm(piece)
                    if p and p not in flat and p not in flat2:
                        missing.append(piece)
        pages = raw.count("\f")
        mark = "OK " if not missing else "NG "
        if missing:
            ng_total += 1
        print(f'{mark}{t["id"]}_{route:<4} ページ{pages}  欠け{len(missing)}件 '
              f'{("→ " + " / ".join(missing[:4])) if missing else ""}')
print(f"\n欠けのあるPDF: {ng_total} / {len(TABLES)*2}")
