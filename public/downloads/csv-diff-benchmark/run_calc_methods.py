#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表計算ソフト（LibreOffice Calc）側の手法を実行する。

CSVを「普通に開いた」ときに何が起きるかを測るのが目的なので、
セルに値を流し込むのではなく、実際に CSV インポートフィルタでファイルを開く。

インポート2条件:
  standard : 列書式を指定しない（＝ダイアログでそのままOKを押した状態）。
             数字に見えるセルは数値として取り込まれる
  text     : 全列を「テキスト」に強制する（＝取り込み時に列書式を指定した状態）

数式4種（記事の企画どおり）:
  lo_equals   =FA.X2=FB.X2                          素の「=」比較
  lo_exact    =EXACT(FA.X2;FB.X2)                   EXACT
  lo_countif  =COUNTIF(FB.X2;FA.X2)>0               COUNTIF
  lo_vlookup  =EXACT(FA.X2;VLOOKUP(FA.A2;FB...;0))  VLOOKUP で引いてから比較
              （VLOOKUP は1件ごとに全行を線形探索するため、行数の2乗に比例して
                遅くなる。全行だと現実的な時間で終わらないので標本1000行で測る）

XLOOKUP はこの環境の LibreOffice 24.2 には無く（#NAME? になる）測れなかった。
その事実も results に記録する。

出力: results_calc_<prefix>.json
      diag_calc_<prefix>.json  （16桁番号列の値一致/表示文字列一致の内訳）
"""
import argparse
import json
import os
import subprocess
import time

import uno
from com.sun.star.beans import PropertyValue

CATEGORY_COLUMN = {
    "same": "確認用番号",
    "control_diff": "対照用コード",
    "digit16_last": "照合番号",
    "leading_zero": "商品コード",
    "space_diff": "得意先コード",
    "width_diff": "型番",
    "case_diff": "承認者ID",
    "newline_in_cell": "備考",
}
# CSVの列順（0始まり）: id,登録日,顧客名,金額,確認用番号,対照用コード,照合番号,商品コード,得意先コード,型番,承認者ID,備考
COL_INDEX = {"確認用番号": 4, "対照用コード": 5, "照合番号": 6, "商品コード": 7,
             "得意先コード": 8, "型番": 9, "承認者ID": 10, "備考": 11}
COL_LETTER = {4: "E", 5: "F", 6: "G", 7: "H", 8: "I", 9: "J", 10: "K", 11: "L"}

PORT = 2010
PROFILE = "/tmp/loprof_bench_csvdiff"
STD_OPTIONS = "44,34,76,1"                                   # , " UTF-8 1行目から
# 列書式は「列番号/書式コード」を / でつないで並べる（書式2＝テキスト）。
# カンマ区切りにすると効かないので注意（最初はそれで丸1回ぶん測り直した）。
TEXT_OPTIONS = "44,34,76,1," + "/".join(f"{i}/2" for i in range(1, 13))  # 全12列をテキスト


def mkprop(name, value):
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


class Calc:
    def __init__(self):
        os.makedirs(PROFILE, exist_ok=True)
        self.proc = subprocess.Popen(
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
        if ctx is None:
            raise RuntimeError("LibreOffice への接続に失敗")
        self.desktop = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)

    def load_csv(self, path, options):
        return self.desktop.loadComponentFromURL(
            "file://" + os.path.abspath(path), "_blank", 0,
            (mkprop("Hidden", True),
             mkprop("FilterName", "Text - txt - csv (StarCalc)"),
             mkprop("FilterOptions", options)))

    def close(self):
        try:
            self.desktop.terminate()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=15)
        except Exception:
            self.proc.kill()


def bool_col(rng):
    """数式列の結果を bool のリストにする（TRUE=1.0）"""
    return [x[0] == 1.0 for x in rng.getDataArray()]


def run_mode(calc, prefix, n, options, mode_name, vlookup_sample):
    docA = calc.load_csv(f"{prefix}_a.csv", options)
    docB = calc.load_csv(f"{prefix}_b.csv", options)
    docA.Sheets.importSheet(docB, docB.Sheets.getByIndex(0).Name, 1)
    docA.Sheets.getByIndex(0).Name = "FA"
    docA.Sheets.getByIndex(1).Name = "FB"
    sh = docA.Sheets.getByName("FA")
    last = n + 1  # データ最終行（1行目はヘッダ）

    res = {}
    diag = {}

    for cat, col in CATEGORY_COLUMN.items():
        ci = COL_INDEX[col]
        L = COL_LETTER[ci]
        # 作業列は Z 以降（元データは L 列まで）
        specs = [
            ("lo_equals", "AA", lambda r, L=L: f"=FA.{L}{r}=FB.{L}{r}"),
            ("lo_exact", "AB", lambda r, L=L: f"=EXACT(FA.{L}{r};FB.{L}{r})"),
            ("lo_countif", "AC", lambda r, L=L: f"=COUNTIF(FB.{L}{r};FA.{L}{r})>0"),
        ]
        for name, wcol, f in specs:
            rng = sh.getCellRangeByName(f"{wcol}2:{wcol}{last}")
            rng.setFormulaArray(tuple((f(r),) for r in range(2, last + 1)))
            docA.calculateAll()
            same_flags = bool_col(rng)
            res.setdefault(name, {})[cat] = [
                {"id": i + 1, "pred_diff": not same_flags[i]} for i in range(n)
            ]
            rng.clearContents(1023)

        # VLOOKUP は重いので先頭 vlookup_sample 行だけ
        m = min(vlookup_sample, n)
        rng = sh.getCellRangeByName(f"AD2:AD{m + 1}")
        rng.setFormulaArray(tuple(
            (f"=EXACT(FA.{L}{r};VLOOKUP(FA.A{r};FB.$A$2:$L${last};{ci + 1};0))",)
            for r in range(2, m + 2)))
        t0 = time.time()
        docA.calculateAll()
        el = time.time() - t0
        same_flags = bool_col(rng)
        res.setdefault("lo_vlookup", {})[cat] = [
            {"id": i + 1, "pred_diff": not same_flags[i]} for i in range(m)
        ]
        rng.clearContents(1023)
        print(f"  [{mode_name}] {cat:16s} done (vlookup {m}行 {el:.1f}s)", flush=True)

    # ---- 16桁番号列の診断：値そのものが一致したのか、表示文字列が一致したのか ----
    shB = docA.Sheets.getByName("FB")
    ci = COL_INDEX["照合番号"]
    val_equal = str_equal = both = 0
    examples_val = []
    examples_str_only = []
    for r in range(1, n + 1):
        ca = sh.getCellByPosition(ci, r)
        cb = shB.getCellByPosition(ci, r)
        ve = (ca.getValue() == cb.getValue()) and ca.getValue() != 0
        se = ca.getString() == cb.getString()
        val_equal += ve
        str_equal += se
        both += (ve and se)
        rec = {"row": r + 1,
               "a_string": ca.getString(), "b_string": cb.getString(),
               "a_value": repr(ca.getValue()), "b_value": repr(cb.getValue())}
        if ve and len(examples_val) < 8:
            examples_val.append(rec)
        if se and not ve and len(examples_str_only) < 8:
            examples_str_only.append(rec)
    diag["digit16_value_equal"] = val_equal
    diag["digit16_string_equal"] = str_equal
    diag["digit16_both_equal"] = both
    diag["digit16_examples_value_equal"] = examples_val
    diag["digit16_examples_string_equal_only"] = examples_str_only

    # 比較まわりの設定（記事に環境として書くため）
    for prop in ("CaseSensitive", "IsIterationEnabled", "CalcAsShown", "LookUpLabels"):
        try:
            diag[f"setting_{prop}"] = docA.getPropertyValue(prop)
        except Exception as e:
            diag[f"setting_{prop}"] = f"(取得できず: {e})"

    # XLOOKUP が使えるか（この環境では #NAME? になるはず）
    probe = sh.getCellByPosition(40, 1)
    probe.setFormula(f"=XLOOKUP(FA.A2;FB.$A$2:$A${last};FB.$G$2:$G${last})")
    docA.calculateAll()
    diag["xlookup_error_code"] = probe.getError()
    diag["xlookup_display"] = probe.getString()
    probe.setString("")

    docA.close(False)
    docB.close(False)
    return res, diag


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--vlookup-sample", type=int, default=1000)
    args = ap.parse_args()

    calc = Calc()
    try:
        all_res = {}
        all_diag = {}
        for mode_name, options in [("standard", STD_OPTIONS), ("text", TEXT_OPTIONS)]:
            print(f"=== import mode: {mode_name} ===", flush=True)
            res, diag = run_mode(calc, args.prefix, args.n, options, mode_name,
                                  args.vlookup_sample)
            for method, cats in res.items():
                all_res[f"{method}__{mode_name}"] = cats
            all_diag[mode_name] = diag
    finally:
        calc.close()

    with open(f"results_calc_{args.prefix}.json", "w", encoding="utf-8") as f:
        json.dump(all_res, f, ensure_ascii=False)
    with open(f"diag_calc_{args.prefix}.json", "w", encoding="utf-8") as f:
        json.dump(all_diag, f, ensure_ascii=False, indent=1)
    print("saved results_calc_%s.json" % args.prefix)
