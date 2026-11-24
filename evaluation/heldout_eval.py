"""Held-out check: weights learned on half A vs. on all runs, on the same 200 half-B test cases.
  python heldout_eval.py [results folder, default ../results]"""
import os, glob, sys
import numpy as np, pandas as pd
from scipy.stats import wilcoxon
os.chdir(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results"))
runs = {}
for fo, tag in [("heldout_B_weightsA", "A"), ("heldout_B_weightsAll", "All")]:
    for f in sorted(glob.glob(f"{fo}/cases_*.csv")):
        d = pd.read_csv(f); d = d[d["rank"].notna()].set_index("case")
        d["mid"] = (d.rank_best_case_ties + d.rank_worst_case_ties) / 2
        runs[f"{tag}:{os.path.basename(f)[6:-4]}"] = d
rng = np.random.default_rng(0)
ci = lambda x: np.percentile([rng.choice(x, len(x)).mean() for _ in range(2000)], [2.5, 97.5])
print(f"{'run':24s} {'n':>4s} {'mid':>6s} {'mid CI':>15s} {'top1':>5s} {'top5':>5s} {'top10':>5s} {'sae':>5s} {'sae_abs':>7s} {'zeroGT':>6s} top1 most frequent")
for k, d in runs.items():
    lo, hi = ci(d.mid.values); tc = d.top1_code.value_counts()
    print(f"{k:24s} {len(d):4d} {d.mid.mean():6.2f} [{lo:5.2f},{hi:6.2f}] {(d.mid<=1).mean():5.0%} {(d.mid<=5).mean():5.0%} {(d.mid<=10).mean():5.0%} "
          f"{d.sae.mean():5.2f} {d.sae_abs.mean():7.2f} {int((d.c_gt==0).sum()):6d} {tc.index[0]} ({tc.iloc[0]})")
print("\npaired (Wilcoxon), diff = first - second, positive = second better:")
for A, B in [("All:kl", "A:kl"), ("All:beta", "A:beta"), ("A:heuristic_uniform", "A:kl"), ("A:heuristic_uniform", "A:beta")]:
    c = runs[A].index.intersection(runs[B].index)
    for m in ["mid", "sae_abs"]:
        a, b = runs[A].loc[c, m], runs[B].loc[c, m]; diff = a - b
        lo, hi = ci(diff.values)
        p = wilcoxon(a, b).pvalue if (diff != 0).any() else np.nan
        print(f"  {A:20s} vs {B:8s} {m:7s} n={len(c)} {a.mean():6.3f} vs {b.mean():6.3f} diff {diff.mean():+.3f} [{lo:+.3f},{hi:+.3f}] "
              f"better/eq/worse={int((diff>0).sum())}/{int((diff==0).sum())}/{int((diff<0).sum())} p={p:.2g}")
print("\nrank correlation per case A vs All (Spearman):")
for m in ["kl", "beta"]:
    c = runs[f"A:{m}"].index.intersection(runs[f"All:{m}"].index)
    print(f"  {m}: {runs[f'A:{m}'].loc[c,'mid'].corr(runs[f'All:{m}'].loc[c,'mid'], method='spearman'):.2f}; "
          f"identical top-1 {(runs[f'A:{m}'].loc[c,'top1_code']==runs[f'All:{m}'].loc[c,'top1_code']).mean():.0%}")
print("\nper true parameter (mean midpoint rank):")
tab = pd.DataFrame({k: d.groupby(d.index.str.rsplit("_", n=1).str[0]).mid.mean() for k, d in runs.items()})
tab.insert(0, "n", runs["A:kl"].groupby(runs["A:kl"].index.str.rsplit("_", n=1).str[0]).size())
print(tab.round(1).to_string())
