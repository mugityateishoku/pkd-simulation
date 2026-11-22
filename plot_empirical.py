"""Plot paired, pool-level weighting contrasts, one point per paired participant pool."""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

folder = Path(__file__).parent / "results/november_2026"
groups = defaultdict(list)
with (folder / "empirical_folds.csv").open() as stream:
    for row in csv.DictReader(stream):
        if float(row["trim"]) == .05:
            k = (row["experiment"], row["set"], row["network"], row["pair"])
            groups[k].append(float(row["mixed_score"]) - float(row["mixed_equal"]))
fig, axes = plt.subplots(2, 1, figsize=(7.6, 3.8), constrained_layout=True)
for ex, ax in enumerate(axes, start=1):
    xs = np.sort([np.mean(v) for k,v in groups.items() if k[0] == str(ex)])
    jitter = .075 * (np.arange(len(xs)) % 4 - 1.5)
    ax.axvline(0,color="#66737b",lw=.9)
    ax.scatter(xs, jitter, color="#185b76", s=31, zorder=2, label="Paired participant pool")
    ax.scatter([np.mean(xs)],[-.33],marker="D",s=43,color="#bd542d",zorder=3,label="Mean over pools")
    ax.set_ylim(-.54,.37)
    ax.set_yticks([])
    ax.set_title(f"Experiment {ex}",loc="left",fontsize=10,fontweight="semibold")
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="x",labelsize=8)
    ax.grid(axis="x",color="#e4e8eb",lw=.6)
    if ex == 1:
        ax.legend(loc="upper right",fontsize=8,frameon=False, ncol=2)
    else:
        ax.set_xscale("symlog",linthresh=1)
        ax.set_xticks([-10,-1,0,1,10,80],["−10","−1","0","1","10","80"])
        ax.set_xlim(-12,105)
fig.supxlabel("Squared error with record weights minus squared error with equal weights",fontsize=9)
fig.savefig(folder/"empirical_contrasts.png",dpi=200,bbox_inches="tight")

