import json, sys, copy, traceback
sys.path.insert(0, "/root/lab/bench")
from harness import Calc, judge

tasks = {t["id"]: t for t in json.load(open("/root/lab/bench/tasks_all.json", encoding="utf-8"))}
models = ["opus", "sonnet", "haiku"]

calc = Calc()
results = []
try:
    for m in models:
        answers = {a["id"]: a["formula"] for a in
                   json.load(open(f"/root/lab/bench/answers_{m}.json", encoding="utf-8"))}
        for i, (tid, t) in enumerate(tasks.items(), 1):
            f = answers.get(tid)
            rec = {"model": m, "id": tid, "category": t["category"],
                   "formula": f, "expected": t["expected"]}
            if not f:
                rec.update(verdict="MISSING", detail="解答なし", got=None)
                results.append(rec); continue
            sh = calc.fresh_sheet()
            calc.fill(sh, t["data"])
            got_str, got_val, got_err, perr = calc.eval_formula(sh, f, at=(0, 30))
            if perr is not None:
                rec.update(verdict="PARSE_ERROR", detail=perr[:120], got=None)
            else:
                v, d = judge(t["expected"], got_str, got_val, got_err)
                rec.update(verdict=v, detail=d, got=got_str)
            results.append(rec)
            if i % 25 == 0:
                print(f"  {m}: {i}/100", flush=True)
        print(f"[{m}] 完了", flush=True)
finally:
    calc.close()

json.dump(results, open("/root/lab/bench/results.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

from collections import Counter, defaultdict
print("\n=== モデル別 判定内訳 ===")
for m in models:
    c = Counter(r["verdict"] for r in results if r["model"] == m)
    tot = sum(c.values())
    print(f"{m:8s} 正解 {c['CORRECT']:3d}/{tot}  誤答 {c['WRONG']:3d}  計算エラー {c['ERROR']:3d}  構文エラー {c['PARSE_ERROR']:3d}")
