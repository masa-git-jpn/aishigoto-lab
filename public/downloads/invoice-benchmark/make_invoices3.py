#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第3セット：v2 が一度も見ていない形式の請求書を50枚作る（ホールドアウト）。
v2 のコードはこのファイルを作ったあと一切変更していない。

  K: ラベルが「請求No.」「件名」。合計は「ご請求金額」だけで「合計」の語が無い
  L: 明細の途中に区分ごとの小計行が挟まる
  M: 列の順番が「金額・単価」と逆。見出しに「(円)」が付く
  N: 罫線なし。単位の列が空のことがあり、品目に半角スペース入りの英数字が混じる
  O: 明細が2ページに続き、2ページ目には見出し行が無い。ページ番号 1/2 が入る
"""
import json, random, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from make_invoices import VENDORS, ITEMS, yen, CSS_COMMON, CSS_A, CHROMIUM, build_record

ROOT = Path(__file__).parent
PDF = ROOT / "pdfs3"
WORK = ROOT / "work3"
random.seed(31415)

CSS_NONE = "th{background:none;border:none}td{border:none}table,th,td{border:none}"


def base_rec(i, tmpl):
    r = build_record(i + 200, tmpl)
    r["file"] = f"invoice3_{i+1:02d}_{tmpl}.pdf"
    r["template"] = tmpl
    return r


def render(html, out):
    WORK.mkdir(exist_ok=True)
    h = WORK / (out.stem + ".html")
    h.write_text(html, encoding="utf-8")
    subprocess.run([CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", f"--print-to-pdf={out}", h.as_uri()],
                   check=True, capture_output=True, timeout=120)


def page(inner, css=CSS_A, extra=""):
    return (f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<style>{CSS_COMMON}{css}{extra}</style></head><body>""" + inner + "</body></html>")


def rowhtml(x, order="normal"):
    if order == "normal":
        return (f"<tr><td>{x['name']}</td><td class='num'>{x['qty']}</td><td>{x['unit']}</td>"
                f"<td class='num'>{yen(x['price'])}</td><td class='num'>{yen(x['amount'])}</td></tr>")
    return (f"<tr><td>{x['name']}</td><td class='num'>{x['qty']}</td><td>{x['unit']}</td>"
            f"<td class='num'>{yen(x['amount'])}</td><td class='num'>{yen(x['price'])}</td></tr>")


def head(r, no_label="請求書番号", subject=False):
    s = "<div class='meta'>件名：2026年度 保守運用一式</div>" if subject else ""
    return f"""<h1>請求書</h1>
<div class="meta">{no_label}：{r['invoice_no']}<br>発行日：{r['issue_date_raw']}</div>{s}
<div class="to">株式会社サンプル商会 御中</div>
<div class="from">{r['vendor']}<br>{r['vendor_addr']}</div>"""


def make_K(r):
    rows = "\n".join(rowhtml(x) for x in r["rows"])
    inner = head(r, no_label="請求No.", subject=True) + f"""
<div class="total-box"><b>ご請求金額（税込）　{yen(r['total'])} 円</b></div>
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">単価</th><th class="num">金額</th></tr></thead><tbody>{rows}</tbody></table>
<table class="sum">
<tr><td>小計</td><td class="num">{yen(r['subtotal'])}</td></tr>
<tr><td>消費税(10%)</td><td class="num">{yen(r['tax'])}</td></tr></table>"""
    render(page(inner), PDF / r["file"])


def make_L(r):
    half = max(1, len(r["rows"]) // 2)
    a, b = r["rows"][:half], r["rows"][half:]
    sa, sb = sum(x["amount"] for x in a), sum(x["amount"] for x in b)
    rows = ("<tr><td colspan=5><b>【保守】</b></td></tr>"
            + "\n".join(rowhtml(x) for x in a)
            + f"<tr><td>保守 小計</td><td></td><td></td><td></td><td class='num'>{yen(sa)}</td></tr>"
            + "<tr><td colspan=5><b>【物品】</b></td></tr>"
            + "\n".join(rowhtml(x) for x in b)
            + f"<tr><td>物品 小計</td><td></td><td></td><td></td><td class='num'>{yen(sb)}</td></tr>")
    inner = head(r) + f"""
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">単価</th><th class="num">金額</th></tr></thead><tbody>{rows}</tbody></table>
<table class="sum">
<tr><td>小計</td><td class="num">{yen(r['subtotal'])}</td></tr>
<tr><td>消費税(10%)</td><td class="num">{yen(r['tax'])}</td></tr>
<tr><td><b>合計</b></td><td class="num"><b>{yen(r['total'])}</b></td></tr></table>"""
    render(page(inner), PDF / r["file"])


def make_M(r):
    rows = "\n".join(rowhtml(x, order="rev") for x in r["rows"])
    inner = head(r) + f"""
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">金額(円)</th><th class="num">単価(円)</th></tr></thead><tbody>{rows}</tbody></table>
<table class="sum">
<tr><td>小計</td><td class="num">{yen(r['subtotal'])}</td></tr>
<tr><td>消費税(10%)</td><td class="num">{yen(r['tax'])}</td></tr>
<tr><td><b>合計</b></td><td class="num"><b>{yen(r['total'])}</b></td></tr></table>"""
    render(page(inner), PDF / r["file"])


CODES = ["MX 200 SP", "AB-12 CT", "RX 7 PRO", "TS 400 EX"]

def make_N(r):
    for i, x in enumerate(r["rows"]):
        x["name"] = f"{x['name']} {random.choice(CODES)}"
        if i % 2 == 0:
            x["unit"] = ""
    rows = "\n".join(rowhtml(x) for x in r["rows"])
    inner = head(r) + f"""
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">単価</th><th class="num">金額</th></tr></thead><tbody>{rows}</tbody></table>
<table class="sum">
<tr><td>小計</td><td class="num">{yen(r['subtotal'])}</td></tr>
<tr><td>消費税(10%)</td><td class="num">{yen(r['tax'])}</td></tr>
<tr><td><b>合計</b></td><td class="num"><b>{yen(r['total'])}</b></td></tr></table>"""
    render(page(inner, css=CSS_NONE), PDF / r["file"])


def make_O(r):
    # 明細を必ず2ページに分ける。2ページ目に見出しは無い
    extra = [dict(random.choice(ITEMS)and {"name": n, "unit": u, "qty": random.randint(1, 9),
                                           "price": 4800, "amount": 0})
             for n, u in random.sample(ITEMS, 8)]
    for x in extra:
        x["amount"] = x["qty"] * x["price"]
    r["rows"] = r["rows"] + extra
    r["subtotal"] = sum(x["amount"] for x in r["rows"])
    r["tax"] = int(r["subtotal"] * 0.1)
    r["total"] = r["subtotal"] + r["tax"]
    n1 = 5
    p1 = "\n".join(rowhtml(x) for x in r["rows"][:n1])
    p2 = "\n".join(rowhtml(x) for x in r["rows"][n1:])
    inner = head(r) + f"""
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">単価</th><th class="num">金額</th></tr></thead><tbody>{p1}</tbody></table>
<p style="text-align:right;font-size:9pt">1 / 2</p>
<div style="page-break-before:always"></div>
<table><tbody>{p2}</tbody></table>
<table class="sum">
<tr><td>小計</td><td class="num">{yen(r['subtotal'])}</td></tr>
<tr><td>消費税(10%)</td><td class="num">{yen(r['tax'])}</td></tr>
<tr><td><b>合計</b></td><td class="num"><b>{yen(r['total'])}</b></td></tr></table>
<p style="text-align:right;font-size:9pt">2 / 2</p>"""
    render(page(inner), PDF / r["file"])


def main():
    PDF.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    plan = ["K"] * 10 + ["L"] * 10 + ["M"] * 10 + ["N"] * 10 + ["O"] * 10
    fn = {"K": make_K, "L": make_L, "M": make_M, "N": make_N, "O": make_O}
    recs = []
    for i, t in enumerate(plan):
        r = base_rec(i, t)
        fn[t](r)
        recs.append(r)
        print("made", r["file"], flush=True)
    (ROOT / "truth3.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print("total", len(recs))


if __name__ == "__main__":
    main()
