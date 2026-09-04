"""
PDFから表を取り出す5つの手法を、同じPDFに対して実際に走らせて精度と時間を測る。

正解（ground truth）はこちらで作った表そのもの。
PDFのテキスト層に全セルが載っていることは sanity.py で確認済みなので、
ここで測るのは純粋に「抽出できるか」だけになる。
"""
import json, time, subprocess, warnings, sys, os, re
warnings.filterwarnings("ignore")
from tables import TABLES

PDFS = "/root/lab/pdf/pdfs"


def nz(s):
    """比較用の正規化：空白を全部落とすだけ。全角→半角の変換はしない
       （全角のまま取れているかも測定対象のため）"""
    if s is None:
        return ""
    return "".join(str(s).split()).replace("　", "")


# ------------------------------------------------------------ 抽出手法
def m_pdfplumber(path):
    import pdfplumber
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for tb in page.extract_tables() or []:
                out.append([[c for c in row] for row in tb])
    return out


def m_pdfplumber_text(path):
    """pdfplumber の既定は「罫線から表を見つける」。
       文字の並びから列を推測する設定に変えると、罫線が無い表でも取れるはず。
       これが実際に効くのかを確かめるために比較対象に入れる。"""
    import pdfplumber
    settings = {"vertical_strategy": "text", "horizontal_strategy": "text"}
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for tb in page.extract_tables(settings) or []:
                out.append([[c for c in row] for row in tb])
    return out


def m_camelot_lattice(path):
    import camelot
    ts = camelot.read_pdf(path, pages="all", flavor="lattice")
    return [t.df.values.tolist() for t in ts]


def m_camelot_stream(path):
    import camelot
    ts = camelot.read_pdf(path, pages="all", flavor="stream")
    return [t.df.values.tolist() for t in ts]


def m_tabula(path):
    import tabula
    dfs = tabula.read_pdf(path, pages="all", multiple_tables=True,
                          lattice=False, stream=True, silent=True)
    out = []
    for df in dfs:
        rows = [list(df.columns)] + df.values.tolist()
        out.append(rows)
    return out


def m_pymupdf(path):
    import pymupdf
    out = []
    doc = pymupdf.open(path)
    for page in doc:
        for tb in page.find_tables().tables:
            out.append(tb.extract())
    doc.close()
    return out


def m_pdftotext(path):
    """表抽出ライブラリではなく、テキストを取り出して2個以上の空白で列に割る方法。
       ライブラリを入れずに済ませたい人が実際によくやるやり方なので、比較対象に入れる。"""
    raw = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True).stdout
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        rows.append(re.split(r"\s{2,}", line.strip()))
    return [rows] if rows else []


METHODS = [
    ("pdfplumber", m_pdfplumber),
    ("pdfplumber(text戦略)", m_pdfplumber_text),
    ("camelot-lattice", m_camelot_lattice),
    ("camelot-stream", m_camelot_stream),
    ("tabula-py", m_tabula),
    ("PyMuPDF", m_pymupdf),
    ("pdftotext+分割", m_pdftotext),
]


# ------------------------------------------------------------ 採点
def count_lookalike(got_tables):
    """見た目は同じだが文字コードが違う漢字（康熙部首など）の個数を数える"""
    import unicodedata
    n = 0
    for tb in got_tables:
        for r in tb:
            for c in r:
                for ch in str(c or ""):
                    if ch.isspace():
                        continue
                    u = unicodedata.normalize("NFKC", ch)
                    if len(u) == 1 and u != ch and ord(u) > 0x3000:
                        n += 1
    return n


def score(truth_rows, got_tables):
    got_rows = [r for tb in got_tables for r in tb]

    # ① セル単位：空でないセルの多重集合として比較（拾えた文字の割合）
    from collections import Counter
    tc = Counter(nz(c) for row in truth_rows for c in row if nz(c))
    gc = Counter(nz(c) for row in got_rows for c in row if nz(c))
    inter = sum((tc & gc).values())
    prec = inter / max(sum(gc.values()), 1)
    rec = inter / max(sum(tc.values()), 1)
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    # ② 行単位：正解の各行が、抽出結果のどこかに「そのままの並びで」現れるか
    got_sig = Counter(tuple(nz(c) for c in r) for r in got_rows)
    hit = 0
    for r in truth_rows:
        sig = tuple(nz(c) for c in r)
        if got_sig.get(sig, 0) > 0:
            got_sig[sig] -= 1
            hit += 1
    row_acc = hit / len(truth_rows)

    return {"cell_f1": round(f1, 4), "cell_recall": round(rec, 4),
            "cell_precision": round(prec, 4),
            "row_exact": round(row_acc, 4), "rows_hit": hit,
            "rows_total": len(truth_rows), "tables_found": len(got_tables)}


def main():
    results = []
    for t in TABLES:
        for route in ("calc", "html"):
            path = f"{PDFS}/{t['id']}_{route}.pdf"
            for name, fn in METHODS:
                rec = {"table": t["id"], "feature": t["feature"],
                       "route": route, "method": name}
                t0 = time.perf_counter()
                try:
                    got = fn(path)
                    rec["error"] = None
                except Exception as e:
                    got = []
                    rec["error"] = f"{type(e).__name__}: {e}"[:160]
                rec["sec"] = round(time.perf_counter() - t0, 3)
                rec["lookalike_chars"] = count_lookalike(got)
                rec.update(score(t["rows"], got))
                results.append(rec)
            print(f"  {t['id']}_{route} 完了", flush=True)

    json.dump(results, open("/root/lab/pdf/results.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 集計
    import statistics as st
    print("\n=== 手法別の平均（24PDF）===")
    print(f"{'手法':<22}{'セルF1':>9}{'行一致':>9}{'平均秒':>9}{'表0件':>7}{'化け文字':>9}")
    for name, _ in METHODS:
        rs = [r for r in results if r["method"] == name]
        print(f"{name:<22}{st.mean(r['cell_f1'] for r in rs):>9.3f}"
              f"{st.mean(r['row_exact'] for r in rs):>9.3f}"
              f"{st.mean(r['sec'] for r in rs):>9.3f}"
              f"{sum(1 for r in rs if r['tables_found'] == 0):>7}"
              f"{sum(r['lookalike_chars'] for r in rs):>9}")


if __name__ == "__main__":
    main()
