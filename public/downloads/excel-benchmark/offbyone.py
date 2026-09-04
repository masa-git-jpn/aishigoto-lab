import json, re, sys
sys.path.insert(0,"/root/lab/bench")
from harness import Calc

T={t["id"]:t for t in json.load(open("tasks_all.json",encoding="utf-8"))}
B=[r for r in json.load(open("results_vague.json",encoding="utf-8"))
   if r["model"]=="haiku" and r["verdict"]!="CORRECT"]

def shift(f, d):
    """絶対参照($付き)は動かさず、相対の単独セル参照の行番号だけをdだけずらす"""
    def rep(m):
        col, row = m.group(1), int(m.group(2))
        return f"{col}{row+d}"
    # 範囲参照(A2:A10)は触らない → 先に退避
    ranges=[]
    def stash(m):
        ranges.append(m.group(0)); return f"@@{len(ranges)-1}@@"
    tmp=re.sub(r'\$?[A-Z]{1,2}\$?\d+:\$?[A-Z]{1,2}\$?\d+', stash, f)
    tmp=re.sub(r'(?<![A-Z0-9$@])([A-Z]{1,2})(\d+)(?![\d(])', rep, tmp)
    for i,r in enumerate(ranges): tmp=tmp.replace(f"@@{i}@@", r)
    return tmp

def judge(exp,got):
    if got is None or got.startswith("#"): return False
    if isinstance(exp,(int,float)) and not isinstance(exp,bool):
        try: return abs(float(str(got).replace(",",""))-float(exp))<1e-6
        except ValueError: return False
    return str(exp).strip()==str(got).strip()

calc=Calc(); out=[]
try:
    for r in B:
        t=T[r["id"]]; base=r["formula"]
        res={"id":r["id"],"orig_ok":False,"shift":None}
        for d in (1,-1):
            f2=shift(base,d)
            if f2==base: continue
            sh=calc.fresh_sheet(); calc.fill(sh,t["data"])
            gs,gv,ge,perr=calc.eval_formula(sh,f2,at=(0,30))
            if perr is None and ge==0 and judge(t["expected"],gs):
                res["shift"]=d; res["fixed"]=f2[:90]; break
        out.append(res)
finally:
    calc.close()

hit=[o for o in out if o["shift"] is not None]
print(f"Haiku 雑条件の誤答 {len(B)}件のうち、")
print(f"参照行を{'+1/-1'}ずらすだけで正解になったもの: {len(hit)}件\n")
for o in hit: print(f"  [{o['id']}] 行を{o['shift']:+d}で正解 → {o['fixed']}")
print("\nずらしても直らなかったもの:", [o["id"] for o in out if o["shift"] is None])
