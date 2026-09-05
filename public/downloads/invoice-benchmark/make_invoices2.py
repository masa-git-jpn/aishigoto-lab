#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第2セット：スクリプトを書くときに想定しなかった形式の請求書を50枚作る。
（このファイルは extract_invoices.py を書き終えたあとに作った。抽出側は一切直していない）

  F: 明細のヘッダ語が「摘要」だけ、数量・単価の列が無く金額だけ  x10
  G: 品目がセル内で2行に折り返す（格子罫線あり）                x10
  H: 8%と10%の税率が混在。小計・消費税が2行ずつある            x10
  I: スキャンした紙をそのままPDFにしたもの（テキスト層が無い）  x10
  J: 和暦の日付、英語ラベル(Invoice No.)、金額に ¥ 記号         x10
"""
import json, random, subprocess, shutil, sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from make_invoices import (VENDORS, ITEMS, yen, CSS_COMMON, CSS_A, CHROMIUM,
                           build_record)

ROOT = Path(__file__).parent
PDF = ROOT / "pdfs2"
WORK = ROOT / "work2"
random.seed(778899)

WAREKI = lambda d: f"令和{d.year - 2018}年{d.month}月{d.day}日"


def base_rec(i, tmpl):
    r = build_record(i + 100, tmpl)          # 番号がぶつからないようにずらす
    r["file"] = f"invoice2_{i+1:02d}_{tmpl}.pdf"
    r["template"] = tmpl
    return r


def head_html(r, extra=""):
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<style>{CSS_COMMON}{CSS_A}{extra}</style></head><body>
<h1>請求書</h1>
<div class="meta">請求書番号：{r['invoice_no']}<br>発行日：{r['issue_date_raw']}</div>
<div class="to">株式会社サンプル商会 御中</div>
<div class="from">{r['vendor']}<br>{r['vendor_addr']}</div>"""


def tail_html(r, sum_rows=None):
    sum_rows = sum_rows or f"""
<tr><td>小計</td><td class="num">{yen(r['subtotal'])}</td></tr>
<tr><td>消費税(10%)</td><td class="num">{yen(r['tax'])}</td></tr>
<tr><td><b>合計</b></td><td class="num"><b>{yen(r['total'])}</b></td></tr>"""
    return f"""<table class="sum">{sum_rows}</table>
<p style="margin-top:16pt;font-size:9.5pt">お振込先：サンプル銀行 本店営業部 普通 1234567</p>
</body></html>"""


def render(html, out):
    WORK.mkdir(exist_ok=True)
    h = WORK / (out.stem + ".html")
    h.write_text(html, encoding="utf-8")
    subprocess.run([CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", f"--print-to-pdf={out}", h.as_uri()],
                   check=True, capture_output=True, timeout=120)


def make_F(r):
    """数量・単価の列が無い。ヘッダ語も「摘要」だけ。"""
    rows = "\n".join(
        f"<tr><td>{x['name']}（{x['qty']}{x['unit']}）</td><td class='num'>{yen(x['amount'])}</td></tr>"
        for x in r["rows"])
    r["rows"] = [{"name": f"{x['name']}（{x['qty']}{x['unit']}）", "qty": None,
                  "unit": "", "price": None, "amount": x["amount"]} for x in r["rows"]]
    html = head_html(r) + f"""
<table><thead><tr><th>摘要</th><th class="num">金額</th></tr></thead>
<tbody>{rows}</tbody></table>""" + tail_html(r)
    render(html, PDF / r["file"])


def make_G(r):
    """品目がセル内で2行に折り返す。"""
    long_names = []
    for x in r["rows"]:
        x = dict(x)
        x["disp"] = x["name"] + "　※2026年度契約分／担当：営業第二部　佐藤　（前月分からの繰越を含む）"
        long_names.append(x)
    rows = "\n".join(
        f"<tr><td style='width:38%'>{x['disp']}</td><td class='num'>{x['qty']}</td><td>{x['unit']}</td>"
        f"<td class='num'>{yen(x['price'])}</td><td class='num'>{yen(x['amount'])}</td></tr>"
        for x in long_names)
    r["rows"] = [{"name": x["disp"], "qty": x["qty"], "unit": x["unit"],
                  "price": x["price"], "amount": x["amount"]} for x in long_names]
    html = head_html(r) + f"""
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">単価</th><th class="num">金額</th></tr></thead>
<tbody>{rows}</tbody></table>""" + tail_html(r)
    render(html, PDF / r["file"])


def make_H(r):
    """軽減税率8%と10%が混在。小計・消費税がそれぞれ2行になる。"""
    for i, x in enumerate(r["rows"]):
        x["rate"] = 8 if i % 3 == 0 else 10
    sub8 = sum(x["amount"] for x in r["rows"] if x["rate"] == 8)
    sub10 = sum(x["amount"] for x in r["rows"] if x["rate"] == 10)
    tax8, tax10 = int(sub8 * 0.08), int(sub10 * 0.10)
    r["subtotal"] = sub8 + sub10
    r["tax"] = tax8 + tax10
    r["total"] = r["subtotal"] + r["tax"]
    rows = "\n".join(
        f"<tr><td>{x['name']}</td><td class='num'>{x['qty']}</td><td>{x['unit']}</td>"
        f"<td class='num'>{yen(x['price'])}</td><td class='num'>{yen(x['amount'])}</td>"
        f"<td class='num'>{x['rate']}%</td></tr>" for x in r["rows"])
    sums = f"""
<tr><td>小計(10%対象)</td><td class="num">{yen(sub10)}</td></tr>
<tr><td>消費税(10%)</td><td class="num">{yen(tax10)}</td></tr>
<tr><td>小計(8%対象)</td><td class="num">{yen(sub8)}</td></tr>
<tr><td>消費税(8%)</td><td class="num">{yen(tax8)}</td></tr>
<tr><td><b>合計</b></td><td class="num"><b>{yen(r['total'])}</b></td></tr>"""
    html = head_html(r) + f"""
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">単価</th><th class="num">金額</th><th class="num">税率</th></tr></thead>
<tbody>{rows}</tbody></table>""" + tail_html(r, sums)
    render(html, PDF / r["file"])


def make_I(r):
    """紙をスキャンした想定。テキスト層のない画像だけのPDF。"""
    from PIL import Image
    Image.init()          # JPEGなどのプラグインを読み込ませる
    tmp = WORK / (Path(r["file"]).stem + "_src.pdf")
    rows = "\n".join(
        f"<tr><td>{x['name']}</td><td class='num'>{x['qty']}</td><td>{x['unit']}</td>"
        f"<td class='num'>{yen(x['price'])}</td><td class='num'>{yen(x['amount'])}</td></tr>"
        for x in r["rows"])
    html = head_html(r) + f"""
<table><thead><tr><th>品目</th><th class="num">数量</th><th>単位</th>
<th class="num">単価</th><th class="num">金額</th></tr></thead>
<tbody>{rows}</tbody></table>""" + tail_html(r)
    render(html, tmp)
    subprocess.run(["pdftoppm", "-r", "150", "-gray", "-png", str(tmp),
                    str(WORK / (Path(r['file']).stem))], check=True, timeout=120)
    pngs = sorted(WORK.glob(Path(r["file"]).stem + "-*.png"))
    imgs = [Image.open(p).convert("L").rotate(0.4, expand=True, fillcolor=255) for p in pngs]
    imgs[0].save(PDF / r["file"], save_all=True, append_images=imgs[1:])


def make_J(r):
    """和暦・英語ラベル・¥記号。"""
    from datetime import date as _d
    y, m, dd = (int(v) for v in r["issue_date"].split("-"))
    r["issue_date_raw"] = WAREKI(_d(y, m, dd))
    rows = "\n".join(
        f"<tr><td>{x['name']}</td><td class='num'>{x['qty']}</td><td>{x['unit']}</td>"
        f"<td class='num'>¥{yen(x['price'])}</td><td class='num'>¥{yen(x['amount'])}</td></tr>"
        for x in r["rows"])
    html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<style>{CSS_COMMON}{CSS_A}</style></head><body>
<h1>INVOICE</h1>
<div class="meta">Invoice No. {r['invoice_no']}<br>Date: {r['issue_date_raw']}</div>
<div class="to">株式会社サンプル商会 御中</div>
<div class="from">{r['vendor']}<br>{r['vendor_addr']}</div>
<table><thead><tr><th>Description</th><th class="num">Qty</th><th>Unit</th>
<th class="num">Unit Price</th><th class="num">Amount</th></tr></thead>
<tbody>{rows}</tbody></table>
<table class="sum">
<tr><td>Subtotal</td><td class="num">¥{yen(r['subtotal'])}</td></tr>
<tr><td>Tax (10%)</td><td class="num">¥{yen(r['tax'])}</td></tr>
<tr><td><b>Total</b></td><td class="num"><b>¥{yen(r['total'])}</b></td></tr>
</table></body></html>"""
    render(html, PDF / r["file"])


def main():
    PDF.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    plan = ["F"] * 10 + ["G"] * 10 + ["H"] * 10 + ["I"] * 10 + ["J"] * 10
    fn = {"F": make_F, "G": make_G, "H": make_H, "I": make_I, "J": make_J}
    recs = []
    for i, t in enumerate(plan):
        r = base_rec(i, t)
        fn[t](r)
        recs.append(r)
        print("made", r["file"], flush=True)
    (ROOT / "truth2.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print("total", len(recs))


if __name__ == "__main__":
    main()
