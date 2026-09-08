#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
副実験2：CSVを表計算ソフトで開いただけで、値が書き換わるか。

日付に見える文字列などを並べた小さなCSVを作り、
  (1) 列書式を指定せずに開く（＝ダイアログでそのままOK）
  (2) 全列テキストとして開く
の2通りで、セルが何になるかを記録する。
さらに (1) のまま CSV として保存し直し、ファイルの中身がどう変わるかも見る。
これは2ファイルの突合ではなく「開いて保存しただけで元の値が消えるか」の確認。

出力: date_result.json / date_roundtrip.csv
"""
import json
import os
import subprocess
import time

import uno
from com.sun.star.beans import PropertyValue

PORT = 2011
PROFILE = "/tmp/loprof_date"
STD = "44,34,76,1"
TEXT = "44,34,76,1," + "/".join(f"{i}/2" for i in range(1, 3))

SAMPLES = [
    ("1-2", "月と日の区切りに見える"),
    ("2-3", "同上"),
    ("3/4", "分数にも日付にも見える"),
    ("2026-1-2", "年月日に見える"),
    ("01-02", "先頭ゼロ付きの日付風"),
    ("0012", "先頭ゼロ付きの番号"),
    ("00123456789", "先頭ゼロ付きの長い番号"),
    ("1E5", "指数表記に見える"),
    ("1234567890123456", "16桁の番号"),
    ("9999999999999999", "16桁の番号（大きいほう）"),
    ("+81 90", "電話番号の一部"),
    ("(123)", "括弧つき"),
    ("１２３", "全角数字"),
    ("TRUE", "真偽値に見える"),
    ("NA", "欠損値に見える"),
    ("１-２", "全角の日付風"),
]


def mkprop(n, v):
    p = PropertyValue()
    p.Name = n
    p.Value = v
    return p


def main():
    with open("date_input.csv", "w", encoding="utf-8", newline="") as f:
        f.write("元の値,説明\n")
        for v, note in SAMPLES:
            f.write(f'"{v}","{note}"\n')

    os.makedirs(PROFILE, exist_ok=True)
    proc = subprocess.Popen(
        ["soffice", "--headless", "--norestore", "--nologo", "--nodefault",
         f"-env:UserInstallation=file://{PROFILE}",
         f"--accept=socket,host=127.0.0.1,port={PORT};urp;"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    ctx = None
    for _ in range(60):
        try:
            ctx = resolver.resolve(
                f"uno:socket,host=127.0.0.1,port={PORT};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    def load(options):
        return desktop.loadComponentFromURL(
            "file://" + os.path.abspath("date_input.csv"), "_blank", 0,
            (mkprop("Hidden", True),
             mkprop("FilterName", "Text - txt - csv (StarCalc)"),
             mkprop("FilterOptions", options)))

    out = []
    doc_std = load(STD)
    doc_txt = load(TEXT)
    sh_std = doc_std.Sheets.getByIndex(0)
    sh_txt = doc_txt.Sheets.getByIndex(0)
    for i, (v, note) in enumerate(SAMPLES):
        r = i + 1
        cs = sh_std.getCellByPosition(0, r)
        ct = sh_txt.getCellByPosition(0, r)
        out.append({
            "original": v, "note": note,
            "standard_display": cs.getString(),
            "standard_value": cs.getValue(),
            "standard_type": str(cs.getType().value),
            "standard_changed": cs.getString() != v,
            "text_display": ct.getString(),
            "text_type": str(ct.getType().value),
            "text_changed": ct.getString() != v,
        })

    # 標準取込のまま CSV に保存し直す（開いて保存しただけ、の再現）
    doc_std.storeToURL("file://" + os.path.abspath("date_roundtrip.csv"),
                       (mkprop("FilterName", "Text - txt - csv (StarCalc)"),
                        mkprop("FilterOptions", STD)))
    doc_std.close(False)
    doc_txt.close(False)
    try:
        desktop.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    with open("date_roundtrip.csv", encoding="utf-8") as f:
        roundtrip = f.read()

    result = {"cells": out, "roundtrip_csv": roundtrip,
              "changed_count_standard": sum(1 for x in out if x["standard_changed"]),
              "changed_count_text": sum(1 for x in out if x["text_changed"]),
              "total": len(out)}
    with open("date_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print(f"{'元の値':20s}{'標準で開いた結果':24s}{'テキストで開いた結果'}")
    for x in out:
        mark = "★" if x["standard_changed"] else "  "
        print(f"{mark}{x['original']:18s}{x['standard_display']:24s}{x['text_display']}")
    print(f"\n標準取込で書き換わった: {result['changed_count_standard']}/{result['total']}")
    print(f"テキスト取込で書き換わった: {result['changed_count_text']}/{result['total']}")
    print("\n--- 開いて保存し直したCSV ---")
    print(roundtrip)


if __name__ == "__main__":
    main()
