"""Publication layout for the completed observer-study estimates.

This changes only figure layout; the executed observer and archived data remain
unchanged. Run this file after review_followup.py --analyze-only if needed.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent / "analysis"
data = json.loads((root / "results.json").read_text(encoding="utf-8"))
lookup = {(r["condition"], r["metric"]): r for r in data["estimates"]}
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 3, figsize=(11.8, 3.9))
seats = [0, 2, 5, 8, 10]
for mode, color, label in [("equal", "#975524", "Equal final weights"),
                           ("score", "#176575", "Record final weights")]:
    for ax, metric in zip(axes, ["loss", "represented_population_share", "effective_lottery_weight"]):
        values = [lookup[(f"record_{k:02d}_{mode}", metric)] for k in seats]
        ax.errorbar(seats, [v["mean"] for v in values],
                    yerr=[(v["high"]-v["low"])/2 for v in values],
                    marker="o", color=color, capsize=3, label=label)
        if mode == "score":
            base = lookup[("baseline_observed", metric)]
            ax.errorbar([5], [base["mean"]], yerr=[(base["high"]-base["low"])/2],
                        marker="*", markersize=11, color="black", capsize=3,
                        linestyle="none", label="Original baseline, deliberation on")
        ax.set_xlabel("Record-selected seats (10 total)")
        ax.set_xticks(seats); ax.grid(alpha=.15)
axes[0].set_ylabel("Mean squared Euclidean error"); axes[0].set_yscale("log")
axes[1].set_ylabel("Nominal stratum coverage")
axes[2].set_ylabel("Effective lottery input\ncoefficient share")
axes[2].plot(seats, [1, .8, .5, .2, 0], "--", color="gray", alpha=.7, label="Lottery seat share")
for ax, label in zip(axes, ["A  Accuracy", "B  Nominal coverage", "C  Input attribution"]):
    ax.set_title(label, loc="left")
handles, labels = axes[2].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
fig.tight_layout(rect=(0, .17, 1, 1))
fig.savefig(root / "figure_followup.png", dpi=220, bbox_inches="tight")
fig.savefig(root / "figure_followup.pdf", bbox_inches="tight")
plt.close(fig)
