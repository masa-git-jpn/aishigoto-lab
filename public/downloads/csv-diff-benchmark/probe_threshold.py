#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
なぜ「=」は 2^53 より上でだけ見逃すのか。推測で書かないために直接測る。

2^53 (9007199254740992) をまたぐ番号のペアを用意し、CSVから普通に取り込んだうえで
  =A=B          素の比較
  =EXACT(A;B)   文字列としての比較
  =A-B          引き算（Calcは結果をまるめることがある）
  =RAWSUBTRACT(A;B)  まるめをしない引き算（LibreOffice独自関数）
  =TEXT(A;"0")  15桁に丸めずに書き出せるか
を全部見る。出力: threshold_result.json
"""
import json
import os
import subprocess
import time

import uno
from com.sun.star.beans import PropertyValue

PORT = 2012
PROFILE = "/tmp/loprof_thr"
STD = "44,34,76,1"

TWO53 = 9007199254740992

# (a, b, 説明)
PAIRS = [
    (1234567890123456, 1234567890123457, "16桁・2^53よりずっと小さい・末尾1違い"),
    (8999999999999998, 8999999999999999, "16桁・2^53のすぐ下・末尾1違い"),
    (TWO53 - 2, TWO53 - 1, "2^53 の直前・末尾1違い"),
    (TWO53, TWO53 + 1, "2^53 ちょうどとその次"),
    (TWO53 + 2, TWO53 + 3, "2^53 の直後・末尾1違い"),
    (9007441326742424, 9007441326742425, "実測で見逃された最小値・末尾1違い"),
    (9999410431301255, 9999410431301256, "実測で見逃された最大値・末尾1違い"),
    (9999999999999998, 9999999999999999, "16桁の上限付近・末尾1違い"),
    (99999999999999998, 99999999999999999, "17桁・末尾1違い"),
    (123456789012345, 123456789012346, "15桁・末尾1違い（比較用）"),
]


def mkprop(n, v):
    p = PropertyValue()
    p.Name = n
    p.Value = v
    return p


def main():
    with open("threshold_input.csv", "w", encoding="utf-8", newline="") as f:
        f.write("a,b\n")
        for a, b, _ in PAIRS:
            f.write(f"{a},{b}\n")

    os.makedirs(PROFILE, exist_ok=True)
    proc = subprocess.Popen(
        ["soffice", "--headless", "--norestore", "--nologo", "--nodefault",
         f"-env:UserInstallation=file://{PROFILE}",
         f"--accept=socket,host=127.0.0.1,port={PORT};urp;"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    local = uno.getComponentContext()
    r = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    ctx = None
    for _ in range(60):
        try:
            ctx = r.resolve(f"uno:socket,host=127.0.0.1,port={PORT};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL(
        "file://" + os.path.abspath("threshold_input.csv"), "_blank", 0,
        (mkprop("Hidden", True), mkprop("FilterName", "Text - txt - csv (StarCalc)"),
         mkprop("FilterOptions", STD)))
    sh = doc.Sheets.getByIndex(0)

    out = []
    for i, (a, b, note) in enumerate(PAIRS):
        row = i + 2  # 1行目はヘッダ
        formulas = {
            "equals": f"=A{row}=B{row}",
            "exact": f"=EXACT(A{row};B{row})",
            "subtract": f"=A{row}-B{row}",
            "rawsubtract": f"=RAWSUBTRACT(A{row};B{row})",
            "text_a": f'=TEXT(A{row};"0")',
            "text_b": f'=TEXT(B{row};"0")',
            "greater": f"=B{row}>A{row}",
        }
        rec = {"a_in_csv": a, "b_in_csv": b, "note": note,
               "over_2_53": a > TWO53,
               "a_stored": sh.getCellByPosition(0, row - 1).getValue(),
               "b_stored": sh.getCellByPosition(1, row - 1).getValue(),
               "a_display": sh.getCellByPosition(0, row - 1).getString(),
               "b_display": sh.getCellByPosition(1, row - 1).getString()}
        for name, f in formulas.items():
            cell = sh.getCellByPosition(5, row - 1)
            cell.setFormula(f)
            doc.calculateAll()
            rec[name] = cell.getString()
            cell.setString("")
        rec["stored_identical"] = rec["a_stored"] == rec["b_stored"]
        out.append(rec)

    doc.close(False)
    try:
        desktop.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    with open("threshold_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"{'CSVのA':>18} {'CSVのB':>18} {'格納同一':>8} {'=':>6} {'EXACT':>6} "
          f"{'A-B':>6} {'RAW差':>7}  説明")
    for x in out:
        print(f"{x['a_in_csv']:>18} {x['b_in_csv']:>18} "
              f"{str(x['stored_identical']):>8} {x['equals']:>6} {x['exact']:>6} "
              f"{x['subtract']:>6} {x['rawsubtract']:>7}  {x['note']}")


if __name__ == "__main__":
    main()
