"""Recompute November contrasts from the published run and fold tables."""
import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from empirical_panels import save_csv
from adaptive_panels import PANELS, MODES, fresh_seeds

T975 = {16: 2.131449545559323, 30: 2.045229642132703}
RULES = ("mixed_score", "mixed_equal", "record10_score", "random10_equal", "pool_equal", "pool_score", "pool_median", "lottery_weight")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def summarize(output, study, group, measure, values):
    n = len(values)
    mean = statistics.mean(values)
    delta = T975[n]*statistics.stdev(values)/math.sqrt(n)
    output.append(dict(study=study, group=group, measure=measure, n=n, mean=mean, low=mean-delta, high=mean+delta))


def empirical(rows, output):
    assert len(rows) == 32*4*3
    for exp in ("1","2"):
        for trim in ("0.05","0.025","0.0"):
            subset = [r for r in rows if r["experiment"]==exp and r["trim"]==trim]
            pools = defaultdict(list)
            for r in subset:
                pools[r["set"],r["network"],r["pair"]].append(r)
            assert len(pools)==16 and all(len({r["question"] for r in g})==len(g)==4 for g in pools.values())
            unit = {k:[statistics.mean(float(r[k]) for r in g) for g in pools.values()] for k in RULES}
            group = f"experiment{exp}_trim{trim}"
            for k, v in unit.items():
                summarize(output, "empirical", group, k, v)
            for comparator in RULES[1:-1]:
                summarize(output, "empirical", group, "mixed_score_minus_"+comparator,
                          [x-y for x,y in zip(unit["mixed_score"],unit[comparator])])
            mae = [statistics.mean(float(r["mixed_score_mae"])-float(r["mixed_equal_mae"]) for r in g)
                   for g in pools.values()]
            summarize(output,"empirical",group,"mixed_score_minus_mixed_equal_mae",mae)


def adaptive(rows, root, output):
    assert len(rows) == 2*30*len(MODES)*len(PANELS)
    cases = {(r["cohort"],int(r["seed"]),r["panel"],r["mode"]):r for r in rows}
    assert len(cases)==len(rows)
    for panel, condition, system in (("mixed","no_deliberation","PKD"),("record","record_only_10","PKD"),
                                     ("random","baseline","Sortition")):
        reference = {int(r["seed"]):-float(r["mean_performance"]) for r in read(root/f"results/preprint_2026/raw/{condition}/run_summary.csv") if r["system"]==system}
        assert len(reference)==30
        for seed, expected in reference.items():
            assert math.isclose(float(cases["archive",seed,panel,"private"]["loss"]),expected,rel_tol=1e-11)
    for cohort, seeds in (("archive",sorted(reference)),("fresh",fresh_seeds())):
        for panel in PANELS:
            for mode in MODES:
                group = f"{cohort}_{panel}_{mode}"
                for metric in ("loss","occupancy","copy","late_copy","coverage","party_tv"):
                    v = [float(cases[cohort,s,panel,mode][metric]) for s in seeds]
                    summarize(output,"adaptive",group,metric,v)
                    if mode != "private":
                        private = [float(cases[cohort,s,panel,"private"][metric]) for s in seeds]
                        summarize(output,"adaptive",group,metric+"_minus_private",[a-b for a,b in zip(v,private)])
                    if mode.startswith("learn"):
                        coin = [float(cases[cohort,s,panel,"coin"][metric]) for s in seeds]
                        summarize(output,"adaptive",group,metric+"_minus_coin",[a-b for a,b in zip(v,coin)])
                    if mode=="learn1":
                        zero = [float(cases[cohort,s,panel,"learn0"][metric]) for s in seeds]
                        summarize(output,"adaptive",group,metric+"_minus_learn0",[a-b for a,b in zip(v,zero)])
                    if mode=="learn1_optimistic":
                        neutral = [float(cases[cohort,s,panel,"learn1"][metric]) for s in seeds]
                        summarize(output,"adaptive",group,metric+"_minus_neutral",[a-b for a,b in zip(v,neutral)])
        for metric in ("coverage","party_tv","loss"):
            v=[float(cases[cohort,s,"mixed","private"][metric])-float(cases[cohort,s,"record","private"][metric]) for s in seeds]
            summarize(output,"adaptive",cohort+"_mixed_minus_record_private",metric,v)


def variance(rows, root, output):
    assert len(rows)==810
    base={(int(r["seed"]),r["system"]):-float(r["mean_performance"])
          for r in read(root/"results/preprint_2026/raw/baseline/run_summary.csv")}
    assert len(base)==270
    indexed={(float(r["alpha"]),int(r["seed"]),r["system"]): float(r["loss"]) for r in rows}
    assert len(indexed)==len(rows)
    for (seed,system),loss in base.items():
        assert math.isclose(indexed[1,seed,system],loss,rel_tol=1e-10,abs_tol=1e-12)
    seeds=sorted({s for s,_ in base})
    for a in (1,.5,0):
        for system in sorted({system for _,system in base}):
            summarize(output,"variance",str(a),system,[indexed[a,s,system] for s in seeds])
        summarize(output,"variance",str(a),"PKD_minus_baseline",[indexed[a,s,"PKD"]-indexed[1,s,"PKD"] for s in seeds])


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory",type=Path,default=Path("results/november_2026"))
    ap.add_argument("--write",action="store_true",help="Save summaries; default verifies existing values")
    args=ap.parse_args()
    root=Path(__file__).resolve().parent
    result=[]
    empirical(read(args.directory/"empirical_folds.csv"),result)
    adaptive(read(args.directory/"adaptive_runs.csv"),root,result)
    variance(read(args.directory/"citizen_noise_runs.csv"),root,result)
    out=args.directory/"estimates.csv"
    if args.write:
        save_csv(out,result)
    else:
        stored=read(out)
        assert len(stored)==len(result)
        for left,right in zip(stored,result):
            for k in ("study","group","measure","n"):
                assert left[k]==str(right[k])
            for k in ("mean","low","high"):
                assert math.isclose(float(left[k]),right[k],rel_tol=1e-10,abs_tol=1e-12)
    print(f"{len(result)} summaries; 270 variance and 90 adaptive replay cells checked.")

