#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽出結果(JSON)を正解(truth.json)と突き合わせて、項目ごとの正解数を数える。"""
import json, sys, csv, unicodedata
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
TRUTH = "truth.json"

def norm(s):
    if s is None:
        return ""
    return unicodedata.normalize("NFKC", str(s)).replace(" ", "").replace("　", "")

def score(extract_path, label, csv_out=None):
    global TRUTH
    truth = {t["file"]: t for t in json.loads((ROOT / TRUTH).read_text(encoding="utf-8"))}
    got = {r["file"]: r for r in json.loads(Path(extract_path).read_text(encoding="utf-8"))}
    fields = ["invoice_no", "issue_date", "vendor", "subtotal", "tax", "total"]
    ok = defaultdict(int)
    per_tmpl = defaultdict(lambda: defaultdict(int))
    rows_out = []
    n_rows_exact = 0
    row_tp = row_total_truth = row_total_got = 0
    flagged, wrong_files = set(), set()

    for f, t in truth.items():
        g = got.get(f, {})
        tm = t["template"]
        per_tmpl[tm]["n"] += 1
        rec = {"file": f, "template": tm}
        bad = []
        for k in fields:
            hit = norm(g.get(k)) == norm(t[k])
            ok[k] += hit
            per_tmpl[tm][k] += hit
            rec[k] = "OK" if hit else f"NG(得:{g.get(k)} / 正:{t[k]})"
            if not hit:
                bad.append(k)
        # 明細行：品目・数量・単価・金額の4つが全部一致した行だけを正解とする
        tr = [(norm(r["name"]), r["qty"], r["price"], r["amount"]) for r in t["rows"]]
        gr = [(norm(r["name"]), r["qty"], r["price"], r["amount"]) for r in g.get("rows", [])]
        row_total_truth += len(tr)
        row_total_got += len(gr)
        pool = list(tr)
        tp = 0
        for x in gr:
            if x in pool:
                pool.remove(x); tp += 1
        row_tp += tp
        exact = (len(tr) == len(gr) == tp)
        n_rows_exact += exact
        per_tmpl[tm]["rows_exact"] += exact
        rec["rows"] = f"{tp}/{len(tr)}（抽出{len(gr)}行）"
        if not exact:
            bad.append("rows")
        if bad:
            wrong_files.add(f)
        if g.get("checks"):
            flagged.add(f)
        rec["flagged"] = " / ".join(g.get("checks", []))
        rows_out.append(rec)

    n = len(truth)
    print(f"\n===== {label} =====")
    for k in fields:
        print(f"  {k:12s} {ok[k]:3d}/{n}")
    print(f"  明細が完全一致した請求書   {n_rows_exact:3d}/{n}")
    print(f"  明細行の一致 {row_tp}/{row_total_truth}（抽出した行数 {row_total_got}）")
    print(f"  どこか1つでも間違えた請求書 {len(wrong_files)}/{n}")
    print(f"  検算で要確認になった請求書 {len(flagged)}/{n}")
    print(f"    うち実際に間違っていた   {len(flagged & wrong_files)}")
    print(f"  見逃し（間違いなのに検算を通過） {len(wrong_files - flagged)} → {sorted(wrong_files - flagged)}")
    print("  テンプレート別（完全一致した請求書 / 枚数）")
    for tm in sorted(per_tmpl):
        d = per_tmpl[tm]
        print(f"    {tm}: 明細完全一致 {d['rows_exact']}/{d['n']}  "
              + " ".join(f"{k}={d[k]}" for k in fields))
    if csv_out:
        with open(csv_out, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.DictWriter(fp, fieldnames=list(rows_out[0].keys()))
            w.writeheader(); w.writerows(rows_out)
    return {"label": label, "n": n, "fields": {k: ok[k] for k in fields},
            "rows_exact": n_rows_exact, "row_tp": row_tp,
            "row_truth": row_total_truth, "row_got": row_total_got,
            "wrong": len(wrong_files), "flagged": len(flagged),
            "flagged_and_wrong": len(flagged & wrong_files),
            "missed": sorted(wrong_files - flagged),
            "per_template": {k: dict(v) for k, v in per_tmpl.items()}}

if __name__ == "__main__":
    import os
    TRUTH = os.environ.get("TRUTH", "truth.json")
    PAIRS = json.loads(os.environ.get("PAIRS", "null")) or [
        ["out/extract_poppler.json", "pdftotext(poppler) ルート", "out/detail_poppler.csv"],
        ["out/extract_pdfplumber.json", "pdfplumber ルート", "out/detail_pdfplumber.csv"]]
    SUM = os.environ.get("SUMOUT", "out/summary.json")
    out = []
    for path, label, csvname in PAIRS:
        if Path(path).exists():
            out.append(score(path, label, csvname))
    Path(SUM).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
