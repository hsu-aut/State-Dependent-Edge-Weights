#!/usr/bin/env python3
"""
Final evaluation (revision 2026-11-24): all diagnosable test cases of half B (diagnosable_v4_B.csv, testcases_v4:
correct nominal reference, closed-valve masking, threshold 0.002, 3 s persistence), weights learned on half A only
(weights_A), reduced AML (K = 81), prune valves, ID aggregation max, weight map exp.

Folders (step2_eval_cases.py output): final_B (kl, beta; uniform parameter prior), final_B_uni (heuristic_uniform),
final_B_code (heuristic with the code prior). Ranks are midpoint ranks (best + worst) / 2 over tied causal values.

  python final_eval.py --results ../results --out summary
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

RUNS = {"Knowledge-based, code prior": ("final_B_code", "heuristic"),
        "Knowledge-based, uniform prior": ("final_B_uni", "heuristic_uniform"),
        "Regression coefficients": ("final_B", "beta"),
        "KL divergence": ("final_B", "kl")}
SHORT = {"Knowledge-based, code prior": "KB code", "Knowledge-based, uniform prior": "KB uni",
         "Regression coefficients": "beta", "KL divergence": "KL"}
PAIRS = [("Knowledge-based, uniform prior", "KL divergence"), ("Knowledge-based, uniform prior", "Regression coefficients"),
         ("Regression coefficients", "KL divergence"), ("Knowledge-based, code prior", "KL divergence"),
         ("Knowledge-based, code prior", "Regression coefficients"),
         ("Knowledge-based, uniform prior", "Knowledge-based, code prior")]
K = 81
rng = np.random.default_rng(0)


def boot_ci(x, n=5000, stat=np.mean):
    x = np.asarray(x)
    idx = rng.integers(0, len(x), (n, len(x)))
    return np.percentile(stat(x[idx], axis=1), [2.5, 97.5])


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (len(p) - i) * p[j]))
        adj[j] = run
    return adj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
                    help="repository root (for data_preparation/PARAMETER_CONFIG.py)")
    ap.add_argument("--results", default=".", help="folder that contains final_B, final_B_uni, final_B_code")
    ap.add_argument("--out", default="final_results")
    a = ap.parse_args()
    a.repo = os.path.abspath(a.repo)
    os.chdir(a.results)
    os.makedirs(a.out, exist_ok=True)
    sys.path.insert(0, os.path.join(a.repo, "data_preparation"))
    import PARAMETER_CONFIG
    nominals = dict(PARAMETER_CONFIG.NOMINALS)

    R = {}
    for name, (fo, cfg) in RUNS.items():
        d = pd.read_csv(f"{fo}/cases_{cfg}.csv").drop_duplicates("case").set_index("case")
        assert (d.status == "ok").all() and d["rank"].notna().all(), name
        d["mid"] = (d.rank_best_case_ties + d.rank_worst_case_ties) / 2
        R[name] = d
    cases = sorted(set.intersection(*(set(d.index) for d in R.values())))
    R = {k: d.loc[cases] for k, d in R.items()}
    ref = R["KL divergence"]
    ptype = pd.Series(ref.index.str.rsplit("_", n=1).str[0], index=ref.index)
    rel = pd.Series([v / nominals[g] - 1.0 if g in nominals else np.nan for g, v in zip(ref.gt_param, ref.gt_value)],
                    index=ref.index)
    print(f"N = {len(cases)} test cases (half B, diagnosable), {ptype.nunique()} true parameters, K = {K}; "
          f"rel. deviation {rel.min():+.1%} .. {rel.max():+.1%} (missing nominal: {int(rel.isna().sum())})")

    # --- 1. main table
    rows = []
    for name, d in R.items():
        m = d.mid.values
        lo, hi = boot_ci(m)
        slo, shi = boot_ci(d.sae.values)
        alo, ahi = boot_ci(d.sae_abs.values)
        tc = d.top1_code.value_counts()
        rows.append({"method": name, "N": len(d), "MR": m.mean(), "MR_lo": lo, "MR_hi": hi, "median": np.median(m),
                     "q1": np.percentile(m, 25), "q3": np.percentile(m, 75),
                     **{f"top{k}": (m <= k).mean() for k in (1, 3, 5, 10)},
                     "SAE": d.sae.mean(), "SAE_lo": slo, "SAE_hi": shi,
                     "SAE_abs": d.sae_abs.mean(), "SAE_abs_lo": alo, "SAE_abs_hi": ahi,
                     "ties_mean": (d.rank_worst_case_ties - d.rank_best_case_ties).mean(),
                     "gt_zero": int((d.c_gt == 0).sum()), "top1_most": f"{tc.index[0]} ({tc.iloc[0] / len(d):.0%})"})
    T = pd.DataFrame(rows).set_index("method")
    T.to_csv(f"{a.out}/table_main.csv")
    print("\n=== 1. Main results (midpoint ranks; random ranking: MR = 41, top-k = k/81)")
    print(f"{'method':32s} {'MR':>6s} {'95% CI':>15s} {'med':>5s} {'IQR':>9s} {'top1':>5s} {'top3':>5s} {'top5':>5s} "
          f"{'top10':>5s} {'SAE':>6s} {'95% CI':>15s} {'SAEabs':>6s} {'ties':>5s} {'GT=0':>4s}  top-1 most frequent")
    for n, r in T.iterrows():
        print(f"{n:32s} {r.MR:6.2f} [{r.MR_lo:5.2f},{r.MR_hi:6.2f}] {r['median']:5.1f} {r.q1:4.1f}-{r.q3:<4.1f} "
              f"{r.top1:5.1%} {r.top3:5.1%} {r.top5:5.1%} {r.top10:5.1%} {r.SAE:6.3f} [{r.SAE_lo:.3f},{r.SAE_hi:.3f}] "
              f"{r.SAE_abs:6.3f} {r.ties_mean:5.2f} {r.gt_zero:4d}  {r.top1_most}")

    # --- 2. paired tests
    P = []
    for A, B in PAIRS:
        for met in ("mid", "sae", "sae_abs"):
            x, y = R[A][met].values, R[B][met].values
            diff = x - y  # positive = B better (lower)
            nz = diff[diff != 0]
            w = wilcoxon(x, y)
            rk = pd.Series(np.abs(nz)).rank().values
            rb = (rk[nz > 0].sum() - rk[nz < 0].sum()) / rk.sum() if len(nz) else 0.0
            lo, hi = boot_ci(diff)
            P.append({"A": A, "B": B, "metric": met, "mean_A": x.mean(), "mean_B": y.mean(), "diff": diff.mean(),
                      "lo": lo, "hi": hi, "median_diff": np.median(diff), "B_better": int((diff > 0).sum()),
                      "equal": int((diff == 0).sum()), "B_worse": int((diff < 0).sum()), "r_rb": rb, "p": w.pvalue})
    P = pd.DataFrame(P)
    P["p_holm"] = np.nan
    for met in P.metric.unique():
        s = P.metric == met
        P.loc[s, "p_holm"] = holm(P.loc[s, "p"].values)
    P.to_csv(f"{a.out}/paired_tests.csv", index=False)
    print("\n=== 2. Paired comparisons (Wilcoxon signed-rank, Holm within metric; diff = A - B, positive = B better; "
          "r_rb = rank-biserial effect size)")
    for _, r in P.iterrows():
        print(f"  {SHORT[r.A]:7s} vs {SHORT[r.B]:7s} {r.metric:7s} {r.mean_A:7.3f} vs {r.mean_B:7.3f}  diff {r['diff']:+7.3f} "
              f"[{r.lo:+.3f},{r.hi:+.3f}] med {r.median_diff:+.2f}  B better/eq/worse {r.B_better}/{r.equal}/{r.B_worse}  "
              f"r_rb {r.r_rb:+.2f}  p {r.p:.1e}  p_Holm {r.p_holm:.1e}")

    # --- 3. per true parameter and deviation magnitude
    tab = pd.DataFrame({SHORT[k]: d.mid.groupby(ptype).mean() for k, d in R.items()})
    tab.insert(0, "n", ptype.value_counts())
    tab["KL top5"] = (R["KL divergence"].mid <= 5).groupby(ptype).mean()
    tab["beta top5"] = (R["Regression coefficients"].mid <= 5).groupby(ptype).mean()
    tab = tab.sort_values("KL")
    tab.to_csv(f"{a.out}/per_parameter.csv")
    print("\n=== 3a. Mean midpoint rank per true parameter")
    print(tab.round(2).to_string())
    bins = pd.cut(rel.abs(), [0, 0.05, 0.10, 0.15, 0.20, 1.0], labels=["<=5%", "5-10%", "10-15%", "15-20%", ">20%"])
    tb = pd.DataFrame({SHORT[k]: d.mid.groupby(bins, observed=True).mean() for k, d in R.items()})
    tb.insert(0, "n", bins.value_counts())
    sign = np.sign(rel).map({1.0: "increase", -1.0: "decrease"})
    ts = pd.DataFrame({SHORT[k]: d.mid.groupby(sign).mean() for k, d in R.items()})
    ts.insert(0, "n", sign.value_counts())
    pd.concat([tb, ts]).to_csv(f"{a.out}/per_deviation.csv")
    print("\n=== 3b. Mean midpoint rank by |relative deviation| and by direction")
    print(pd.concat([tb, ts]).round(2).to_string())

    # --- 4. dominant top-1 candidate
    print("\n=== 4. Top-1 candidates (share of cases)")
    for k, d in R.items():
        print(f"  {SHORT[k]:7s} " + ", ".join(f"{c} {v:.0%}" for c, v in d.top1_code.value_counts(normalize=True).head(4).items()))
    for k in ("KL divergence", "Regression coefficients"):
        d = R[k]
        hub = d.top1_code.value_counts().index[0]
        own = d.gt_code == hub
        print(f"  {SHORT[k]}: hub {hub} top-1 in {(d.top1_code == hub).mean():.0%}; MR when hub is NOT the true cause "
              f"{d.mid[~own].mean():.2f} (n={int((~own).sum())}), when it is {d.mid[own].mean():.2f} (n={int(own.sum())}); "
              f"median c_top1/|c_gt| {np.median(np.abs(d.c_top1) / np.abs(d.c_gt).clip(lower=1e-300)):.0f}")

    # --- 5. candidate example cases
    kl, kb = R["KL divergence"], R["Knowledge-based, uniform prior"]
    good = kl[(kl.mid == 1)].assign(kb=kb.mid).sort_values("kb", ascending=False)
    bad = kl.assign(kb=kb.mid)[(kl.mid >= 15) & (kb.mid <= 3)].sort_values("mid", ascending=False)
    typical = kl.assign(kb=kb.mid)[(kl.mid.between(4, 7)) & (kb.mid.between(15, 25))]
    print("\n=== 5. Example candidates (KL midpoint rank / KB-uniform midpoint rank, top-1 of KL)")
    for lab, df in (("KL top-1, KB far down", good), ("typical (KL 4-7, KB 15-25)", typical), ("KL fails, KB good", bad)):
        print(f"  {lab} ({len(df)} cases): " + "; ".join(f"{c} {r.mid:g}/{r.kb:g} top1={r.top1_code}"
                                                     for c, r in df.head(4).iterrows()))


if __name__ == "__main__":
    main()
