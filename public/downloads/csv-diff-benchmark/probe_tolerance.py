#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「=」はどれだけ離れていれば「違う」と言うのか、境界を実測する。

基準値をいくつか決め、そこから 1,2,3,... と離した値を並べたCSVを作って取り込み、
「=」と EXACT がどこで FALSE に変わるかを見る。
倍精度で表せない差は自動的に丸められるので、格納値そのものも一緒に記録する。

出力: tolerance_result.json
"""
import json
import os
import subprocess
import time

import uno
from com.sun.star.beans import PropertyValue

PORT = 2013
PROFILE = "/tmp/loprof_tol"
STD = "44,34,76,1"
TWO53 = 9007199254740992

BASES = [
    (1234567890123456, "16桁・2^53よりずっと小さい"),
    (8999999999999998, "16桁・2^53のすぐ下"),
    (9007199254740994, "2^53の直後"),
    (9999410431301254, "16桁の上のほう（実測で見逃された範囲）"),
    (99999999999999998, "17桁"),
]
DELTAS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 128, 256, 512, 1024]


def mkprop(n, v):
    p = PropertyValue()
    p.Name = n
    p.Value = v
    return p


def main():
    rows = []
    for base, note in BASES:
        for d in DELTAS:
            rows.append((base, base + d, d, note))
    with open("tolerance_input.csv", "w", encoding="utf-8", newline="") as f:
        f.write("a,b\n")
        for a, b, _, _ in rows:
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
        "file://" + os.path.abspath("tolerance_input.csv"), "_blank", 0,
        (mkprop("Hidden", True), mkprop("FilterName", "Text - txt - csv (StarCalc)"),
         mkprop("FilterOptions", STD)))
    sh = doc.Sheets.getByIndex(0)
    n = len(rows)

    # 数式は列ごとに分けて入れる（同じセルを使い回すと前の書式が残る）
    eq = sh.getCellRangeByName(f"D2:D{n + 1}")
    ex = sh.getCellRangeByName(f"E2:E{n + 1}")
    eq.setFormulaArray(tuple((f"=A{i}=B{i}",) for i in range(2, n + 2)))
    ex.setFormulaArray(tuple((f"=EXACT(A{i};B{i})",) for i in range(2, n + 2)))
    doc.calculateAll()
    eqv = [x[0] == 1.0 for x in eq.getDataArray()]
    exv = [x[0] == 1.0 for x in ex.getDataArray()]

    out = []
    for i, (a, b, d, note) in enumerate(rows):
        ca = sh.getCellByPosition(0, i + 1)
        cb = sh.getCellByPosition(1, i + 1)
        out.append({
            "base": a, "other": b, "delta_in_csv": d, "note": note,
            "a_stored": ca.getValue(), "b_stored": cb.getValue(),
            "stored_delta": cb.getValue() - ca.getValue(),
            "stored_identical": ca.getValue() == cb.getValue(),
            "equals_says_same": eqv[i],
            "exact_says_same": exv[i],
        })

    doc.close(False)
    try:
        desktop.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    with open("tolerance_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for base, note in BASES:
        sub = [x for x in out if x["base"] == base]
        first_diff_eq = next((x["delta_in_csv"] for x in sub if not x["equals_says_same"]), None)
        first_diff_ex = next((x["delta_in_csv"] for x in sub if not x["exact_says_same"]), None)
        print(f"\n基準 {base}（{note}）")
        print(f"  「=」が『違う』と言い始める差: {first_diff_eq}")
        print(f"  EXACT が『違う』と言い始める差: {first_diff_ex}")
        for x in sub[:8]:
            print(f"    +{x['delta_in_csv']:>4}: 格納差={x['stored_delta']:>8.0f} "
                  f"= → {'同じ' if x['equals_says_same'] else '違う'} / "
                  f"EXACT → {'同じ' if x['exact_says_same'] else '違う'}")


if __name__ == "__main__":
    main()
