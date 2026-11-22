"""Summarize paired curves, audit historical endpoints and plot Figure 4."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

from weight_strength import BETAS, CORRELATIONS, HUMAN_METRICS, OUT, ROOT, SIM_METRICS


def estimate(values):
    n = len(values)
    mean = np.mean(values)
    half = t.ppf(.975, n-1)*np.std(values, ddof=1)/np.sqrt(n)
    return [n,mean,mean-half,mean+half,np.median(values)]


def summaries(frame, groups, units, measures):
    rows = []
    for key, subset in frame.groupby(groups):
        for metric in measures:
            pivot = subset.pivot(index=units, columns="beta", values=metric)
            assert set(pivot.columns)==set(BETAS) and pivot.notna().all().all()
            for beta in BETAS:
                for ref in ("level","minus_0","minus_1"):
                    values = pivot[beta] if ref=="level" else pivot[beta]-pivot[int(ref[-1])]
                    rows.append([*key,beta,metric,ref,*estimate(values)])
    return pd.DataFrame(rows, columns=[*groups,"beta","metric","comparison","n","mean","low","high","median"])


def audit(directory):
    sim = pd.read_csv(directory/"simulation_runs.csv")
    human = pd.read_csv(directory/"human_pools.csv")
    assert len(sim)==30*len(CORRELATIONS)*2*len(BETAS) and len(human)==32*3*len(BETAS)
    assert set(sim["corr"])==set(CORRELATIONS) and set(sim.rule)=={"direct","local"}
    for keys,frame in [(["seed","corr","rule"],sim),(["experiment","group","network","pair","trim"],human)]:
        assert frame.groupby(keys).beta.nunique().eq(len(BETAS)).all()
        assert frame.groupby(keys).seat_party_tv.nunique().eq(1).all()
        assert frame.lottery_weight.between(0,1).all()
    assert sim.groupby(["seed","corr"]).coverage.nunique().eq(1).all()
    for f in (sim[sim.rule=="direct"],human):
        np.testing.assert_allclose(f[f.beta==0].lottery_weight,.5,atol=1e-12)
        np.testing.assert_allclose(f[f.beta==0].weighted_party_tv,f[f.beta==0].seat_party_tv,atol=1e-12)
    for rule,condition in [("direct","no_deliberation"),("local","baseline")]:
        ref = pd.read_csv(ROOT/f"results/preprint_2026/raw/{condition}/run_summary.csv").query("system == 'PKD'").set_index("seed")
        match = sim[(sim.rule==rule)&(sim["corr"]==0)&(sim.beta==1)].set_index("seed")
        assert set(ref.index)==set(match.index) and len(match)==30
        np.testing.assert_allclose(match.loss,-ref.loc[match.index].mean_performance,rtol=1e-11)
    ref = pd.read_csv(ROOT/"results/november_2026/empirical_folds.csv")
    keys = ["experiment","group","network","pair","trim"]
    base = ref.rename(columns={"set":"group"}).groupby(keys).mean(numeric_only=True)
    for b,rule in [(0,"mixed_equal"),(1,"mixed_score")]:
        check = human[human.beta==b].set_index(keys).sort_index()
        assert check.index.equals(base.index)
        np.testing.assert_allclose(check.loss,base[rule],rtol=1e-10)
        np.testing.assert_allclose(check.absolute_error,base[rule+"_mae"],rtol=1e-10)
        np.testing.assert_allclose(check.pool_median_loss,base.pool_median,rtol=1e-10)
        np.testing.assert_allclose(check.lottery_weight,base.lottery_weight if b else .5,atol=1e-12)
    return sim,human


def figure(sim,human,path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    fig,axes = plt.subplots(3,3,figsize=(9.6,6.9),sharex=True)
    fig.subplots_adjust(left=.095,right=.98,top=.86,bottom=.10,hspace=.30,wspace=.33)
    x=np.arange(len(BETAS))
    palette=["#233b63","#187d78","#a35a24","#834573"]
    series=[[(f"r = {c:g}",sim[(sim.rule=="local")&(sim["corr"]==c)],color)
             for c,color in zip(CORRELATIONS,palette)]]
    for exp in (1,2):
        series.append([("Observed responses",human[(human.experiment==exp)&(human.trim==.05)],"#233b63")])
    for col,sets in enumerate(series):
        axes[0,col].set_title(["Simulation","Human experiment 1","Human experiment 2"][col],loc="left",fontsize=11,weight="bold")
        for name,subset,color in sets:
            g=subset.groupby("beta").mean(numeric_only=True).reindex(BETAS)
            for row,metric in enumerate(["lottery_weight","loss","weighted_party_tv"]):
                ax=axes[row,col]
                ax.plot(x,g[metric],color=color,marker="o",markersize=3,lw=1.5,label=name)
                if row==2:
                    ax.axhline(g.seat_party_tv.iloc[0],color=color,ls=":",lw=1)
            if col and len(sets)==1:
                axes[1,col].axhline(g.pool_median_loss.iloc[0],color="#666666",ls="--",lw=1)
        axes[0,col].set_ylim(0,.56)
        axes[0,col].yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
        axes[2,col].set_ylim(0,.34)
        axes[2,col].set_xticks(x,["0","⅛","¼","½","1","2","4"])
        axes[2,col].set_xlabel("Weight strength β",fontsize=9)
        for ax in axes[:,col]:
            ax.spines[["right","top"]].set_visible(False)
            ax.tick_params(labelsize=8)
            ax.grid(axis="y",alpha=.22)
    for i,label in enumerate(["Lottery input share","Mean squared error","Party discrepancy (TV)"]):
        axes[i,0].set_ylabel(label,fontsize=9)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.995),ncol=4,frameon=False,title="Within-coordinate correlation of simulation errors")
    fig.savefig(path,dpi=200,facecolor="white")
    plt.close(fig)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory",type=Path,default=OUT)
    ap.add_argument("--check",action="store_true",help="Verify archived summary tables without writing")
    args=ap.parse_args()
    sim,human=audit(args.directory)
    for name,summary in [
        ("simulation_estimates",summaries(sim,["corr","rule"],["seed"],SIM_METRICS)),
        ("human_estimates",summaries(human,["experiment","trim"],["group","network","pair"],HUMAN_METRICS))]:
        path=args.directory/(name+".csv")
        if args.check:
            pd.testing.assert_frame_equal(summary.reset_index(drop=True),pd.read_csv(path),check_dtype=False,rtol=1e-10,atol=1e-11)
        else:
            summary.to_csv(path,index=False,lineterminator="\n")
    if not args.check:
        figure(sim,human,args.directory/"weight_strength.png")
    print("Verified historical endpoints, fixed memberships and paired summaries.")
