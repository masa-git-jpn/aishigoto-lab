"""
Excel数式ベンチマーク検証ハーネス
- LibreOffice Calc (UNO bridge) で数式を実際に計算させる
- 期待値は Python で独立に計算した oracle と突合する
"""
import subprocess, time, os, sys, json, uno
from com.sun.star.beans import PropertyValue
from com.sun.star.sheet.AddressConvention import XL_A1

PORT = 2002
PROFILE = "/tmp/loprof_bench"

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
        self.ctx = ctx
        self.desktop = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        p = PropertyValue(); p.Name = "Hidden"; p.Value = True
        self.doc = self.desktop.loadComponentFromURL(
            "private:factory/scalc", "_blank", 0, (p,))
        self.parser = self.doc.createInstance("com.sun.star.sheet.FormulaParser")
        self.parser.setPropertyValue("FormulaConvention", XL_A1)

    def fresh_sheet(self, name="T"):
        sheets = self.doc.Sheets
        while sheets.Count > 1:
            sheets.removeByName(sheets.getByIndex(1).Name)
        sh = sheets.getByIndex(0)
        # 既存データを全消去
        rng = sh.getCellRangeByName("A1:AZ2000")
        rng.clearContents(1023)
        return sh

    def fill(self, sh, data, origin=(0, 0)):
        """data: 2次元リスト。None は空セル。"""
        r0, c0 = origin
        for r, row in enumerate(data):
            for c, v in enumerate(row):
                if v is None:
                    continue
                cell = sh.getCellByPosition(c0 + c, r0 + r)
                if isinstance(v, bool):
                    cell.setValue(1 if v else 0)
                elif isinstance(v, (int, float)):
                    cell.setValue(float(v))
                else:
                    cell.setString(str(v))

    def eval_formula(self, sh, formula, at=(0, 20)):
        """数式を1セルに書き込んで計算し、(表示文字列, 数値, エラーコード) を返す"""
        r, c = at
        cell = sh.getCellByPosition(c, r)
        cell.setString("")
        try:
            tokens = self.parser.parseFormula(formula, cell.CellAddress)
            cell.setTokens(tokens)
        except Exception as e:
            return ("__PARSE_ERROR__", None, -1, str(e))
        self.doc.calculateAll()
        return (cell.getString(), cell.getValue(), cell.getError(), None)

    def close(self):
        try: self.doc.close(False)
        except Exception: pass
        try: self.desktop.terminate()
        except Exception: pass
        try: self.proc.wait(timeout=15)
        except Exception: self.proc.kill()


def normalize(v):
    """比較用の正規化。数値は誤差許容、文字列は空白差を吸収。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    s = str(v).strip().replace("　", " ")
    try:
        return round(float(s.replace(",", "")), 6)
    except ValueError:
        return s


def judge(expected, got_str, got_val, got_err):
    """正誤判定。戻り値: (verdict, detail)"""
    if got_err != 0:
        return ("ERROR", f"計算エラー(code={got_err}) 表示={got_str!r}")
    e = normalize(expected)
    if isinstance(e, float):
        try:
            g = round(float(got_val), 6)
        except Exception:
            return ("WRONG", f"数値を期待したが {got_str!r}")
        return ("CORRECT", "") if abs(g - e) < 1e-6 else ("WRONG", f"期待={e} 実際={g}")
    g = normalize(got_str)
    return ("CORRECT", "") if g == e else ("WRONG", f"期待={e!r} 実際={g!r}")
