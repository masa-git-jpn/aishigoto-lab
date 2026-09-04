import json, sys
sys.path.insert(0, "/root/lab/bench")
from harness import Calc

tasks = {t["id"]: t for t in json.load(open("/root/lab/bench/tasks_all.json", encoding="utf-8"))}
models = ["opus", "sonnet", "haiku"]

def judge(exp, got):
    if got is None: return "MISSING", ""
    if got.startswith("#") or got.startswith("Err:"): return "ERROR", f"計算エラー {got}"
    if isinstance(exp,(int,float)) and not isinstance(exp,bool):
        try: g=float(str(got).replace(",",""))
        except ValueError: return "WRONG", f"数値を期待したが {got!r}"
        return ("CORRECT","") if abs(g-float(exp))<1e-6 else ("WRONG", f"期待={exp} 実際={g}")
    e,g=str(exp).strip(), str(got).strip()
    return ("CORRECT","") if e==g else ("WRONG", f"期待={e!r} 実際={g!r}")

calc = Calc(); results=[]
try:
    for m in models:
        ans={a["id"]:a["formula"] for a in
             json.load(open(f"/root/lab/bench/vague_answers_{m}.json", encoding="utf-8"))}
        for i,(tid,t) in enumerate(tasks.items(),1):
            f=ans.get(tid)
            rec={"condition":"vague","model":m,"id":tid,"category":t["category"],
                 "formula":f,"expected":t["expected"]}
            if not f:
                rec.update(verdict="MISSING",detail="解答なし",got=None); results.append(rec); continue
            sh=calc.fresh_sheet(); calc.fill(sh,t["data"])
            gs,gv,ge,perr=calc.eval_formula(sh,f,at=(0,30))
            if perr is not None:
                rec.update(verdict="PARSE_ERROR",detail=perr[:120],got=None)
            else:
                if ge!=0 and not gs.startswith("#"): gs=f"#ERR{ge}"
                v,d=judge(t["expected"],gs); rec.update(verdict=v,detail=d,got=gs)
            results.append(rec)
        print(f"[{m}] 完了", flush=True)
finally:
    calc.close()

json.dump(results, open("/root/lab/bench/results_vague.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
from collections import Counter
print("\n=== 曖昧な指示での結果 ===")
for m in models:
    c=Counter(r["verdict"] for r in results if r["model"]==m)
    print(f"{m:8s} 正解 {c['CORRECT']:3d}/100  誤答 {c['WRONG']:3d}  計算エラー {c['ERROR']:3d}  構文エラー {c['PARSE_ERROR']:3d}")
