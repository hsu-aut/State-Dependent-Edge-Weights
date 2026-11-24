#!/usr/bin/env python3
"""
Step 3 - statistics on the per-case results of step 2.

Reads results/cases_<config>.csv and writes to the same folder:
  analysis.md     human-readable summary (please send this back)
  analysis.json   all numbers
  table.tex       results table for the paper
  per_class.csv   mean rank per parameter class and config

Usage:
  python step3_analyze.py --results results --repo ~/Temporal-Weighting-for-Causal-Graphs
"""
import argparse
import json
import os
import re
import sys

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon
except ImportError:
    wilcoxon = None

PUBLISHED = {"heuristic": (39.76, 0.3949), "beta": (38.03, 0.3267), "kl": (36.21, 0.2812)}
ORDER = ["heuristic", "heuristic_uniform", "beta", "kl", "kl_cond"]
LABEL = {"heuristic": "Heuristic [Ra24]", "heuristic_uniform": "Heuristic, uniform parameter prior", "beta": "Regression coefficients", "kl": "KL divergence",
         "kl_cond": "KL divergence (conditional)"}
TOPK = (1, 3, 5, 10)
RNG = np.random.default_rng(20261117)
N_BOOT = 10000


def param_class(name):
    if not isinstance(name, str):
        return "unknown"
    for pat, cls in ((r"\.dp_nominal$", "valve: nominal pressure drop"),
                     (r"\.m_flow_nominal$", "valve: nominal mass flow"),
                     (r"^pipe_.*\.diameter$", "pipe: diameter"),
                     (r"^pipe_.*\.roughness$", "pipe: roughness"),
                     (r"^tank_.*\.crossArea$", "tank: cross-sectional area"),
                     (r"^tank_.*\.height$", "tank: height")):
        if re.search(pat, name):
            return cls
    return "other"


def boot_ci_mean(x):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return (np.nan, np.nan)
    idx = RNG.integers(0, len(x), size=(N_BOOT, len(x)))
    m = x[idx].mean(axis=1)
    return (float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))


def paired(a_name, b_name, A, B, metric):
    """A, B: DataFrames indexed by case. Positive diff = B better (lower) than A."""
    common = A.index.intersection(B.index)
    x = A.loc[common, metric].astype(float)
    y = B.loc[common, metric].astype(float)
    ok = x.notna() & y.notna()
    x, y = x[ok].to_numpy(), y[ok].to_numpy()
    d = x - y
    res = {"comparison": f"{b_name} vs {a_name}", "metric": metric, "n_pairs": int(len(d)),
           "mean_A": float(x.mean()) if len(d) else np.nan, "mean_B": float(y.mean()) if len(d) else np.nan,
           "mean_improvement": float(d.mean()) if len(d) else np.nan,
           "ci95_improvement": boot_ci_mean(d), "median_improvement": float(np.median(d)) if len(d) else np.nan,
           "B_better": int((d > 0).sum()), "equal": int((d == 0).sum()), "B_worse": int((d < 0).sum())}
    nz = d[d != 0]
    if len(nz):
        r = pd.Series(np.abs(nz)).rank().to_numpy()
        res["rank_biserial"] = float((r[nz > 0].sum() - r[nz < 0].sum()) / r.sum())
    if wilcoxon is not None and len(nz) >= 10:
        st = wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
        res["wilcoxon_W"], res["p_value"] = float(st.statistic), float(st.pvalue)
    else:
        res["p_value"] = np.nan
    return res


def holm(pvals):
    p = np.array([np.nan if v is None else v for v in pvals], dtype=float)
    out = np.full_like(p, np.nan)
    ok = np.where(~np.isnan(p))[0]
    order = ok[np.argsort(p[ok])]
    m, running = len(order), 0.0
    for i, j in enumerate(order):
        running = max(running, min(1.0, (m - i) * p[j]))
        out[j] = running
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--repo", default=None, help="repo clone, for nominal values (relative deviation)")
    a = ap.parse_args()

    nominals = {}
    if a.repo:
        sys.path.insert(0, os.path.join(os.path.expanduser(a.repo), "data_preparation"))
        try:
            import PARAMETER_CONFIG
            nominals = dict(PARAMETER_CONFIG.NOMINALS)
        except Exception as e:
            print(f"PARAMETER_CONFIG not loaded: {e}")

    data = {}
    for cfg in ORDER:
        p = os.path.join(a.results, f"cases_{cfg}.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            df = df.drop_duplicates("case").set_index("case")
            df["param_class"] = df["gt_param"].map(param_class)
            if nominals:
                df["rel_dev"] = [(v / nominals[g] - 1.0) if (g in nominals and pd.notna(v)) else np.nan
                                 for g, v in zip(df["gt_param"], df["gt_value"])]
            data[cfg] = df
    if not data:
        sys.exit(f"no cases_<config>.csv in {a.results}")

    out = {"configs": {}, "paired": []}
    lines = ["# Per-case evaluation\n"]

    # --- 1. per-config descriptive statistics
    lines.append("## Descriptive statistics\n")
    lines.append("| config | cases | valid ranks | no deviation | errors | K | mean rank [95% CI] | median | IQR | top-1 | top-3 | top-5 | top-10 | mean SAE [95% CI] | MR ties best/worst | published MR / SAE |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cfg, df in data.items():
        r = df["rank"].dropna().astype(float)
        s = df["sae"].dropna().astype(float)
        st = df["status"].value_counts().to_dict()
        K = sorted(df["n_candidates"].dropna().astype(int).unique().tolist()) if "n_candidates" in df else []
        c = {
            "cases": int(len(df)), "valid_ranks": int(len(r)), "status": {k: int(v) for k, v in st.items()},
            "K": K, "mean_rank": float(r.mean()), "mean_rank_ci95": boot_ci_mean(r),
            "median_rank": float(r.median()), "iqr": [float(r.quantile(.25)), float(r.quantile(.75))],
            "std_rank": float(r.std()),
            "topk": {k: float((r <= k).mean()) for k in TOPK},
            "mean_sae": float(s.mean()) if len(s) else np.nan, "mean_sae_ci95": boot_ci_mean(s), "n_sae": int(len(s)),
            "mean_rank_ties_best": float(df["rank_best_case_ties"].dropna().mean()) if "rank_best_case_ties" in df else np.nan,
            "mean_rank_ties_worst": float(df["rank_worst_case_ties"].dropna().mean()) if "rank_worst_case_ties" in df else np.nan,
            "cases_with_ties_at_gt": int((df.get("n_tied_with_gt", pd.Series(dtype=float)) > 1).sum()),
            "mean_diag_steps": float(df["n_diag_steps"].dropna().mean()) if "n_diag_steps" in df else np.nan,
            "steps_with_missing_mode_weights": int(df.get("n_missing_mode_steps", pd.Series(dtype=float)).fillna(0).sum()),
        }
        pub = PUBLISHED.get(cfg)
        if pub:
            c["published"] = pub
            c["reproduced"] = bool(abs(c["mean_rank"] - pub[0]) < 0.006 and abs(c["mean_sae"] - pub[1]) < 0.00006)
        out["configs"][cfg] = c
        lines.append(
            f"| {cfg} | {c['cases']} | {c['valid_ranks']} | {st.get('no_deviation', 0)} | {st.get('error', 0)} | {K} | "
            f"{c['mean_rank']:.2f} [{c['mean_rank_ci95'][0]:.2f}, {c['mean_rank_ci95'][1]:.2f}] | {c['median_rank']:.1f} | "
            f"{c['iqr'][0]:.0f}-{c['iqr'][1]:.0f} | " + " | ".join(f"{100 * c['topk'][k]:.1f}%" for k in TOPK) +
            f" | {c['mean_sae']:.4f} [{c['mean_sae_ci95'][0]:.4f}, {c['mean_sae_ci95'][1]:.4f}] | "
            f"{c['mean_rank_ties_best']:.2f} / {c['mean_rank_ties_worst']:.2f} | "
            + (f"{pub[0]} / {pub[1]} -> {'REPRODUCED' if c['reproduced'] else 'DIFFERENT'}" if pub else "-") + " |")

    # --- 2. paired comparisons
    lines.append("\n## Paired comparisons (positive improvement = second method better)\n")
    lines.append("| comparison | metric | pairs | mean A | mean B | mean improvement [95% CI] | median impr. | better/equal/worse | rank-biserial | p (Wilcoxon) | p (Holm) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    pairs = [("heuristic", "kl"), ("beta", "kl"), ("heuristic", "beta"), ("kl", "kl_cond"),
             ("heuristic", "heuristic_uniform"), ("heuristic_uniform", "kl"), ("heuristic_uniform", "beta")]
    for metric in ("rank", "sae"):
        block = [paired(x, y, data[x], data[y], metric) for x, y in pairs if x in data and y in data]
        hp = holm([b.get("p_value") for b in block])
        for b, h in zip(block, hp):
            b["p_holm"] = float(h)
            out["paired"].append(b)
            ci = b["ci95_improvement"]
            lines.append(f"| {b['comparison']} | {metric} | {b['n_pairs']} | {b['mean_A']:.4g} | {b['mean_B']:.4g} | "
                         f"{b['mean_improvement']:.4g} [{ci[0]:.4g}, {ci[1]:.4g}] | {b['median_improvement']:.4g} | "
                         f"{b['B_better']}/{b['equal']}/{b['B_worse']} | {b.get('rank_biserial', np.nan):.3f} | "
                         f"{b.get('p_value', np.nan):.3g} | {b['p_holm']:.3g} |")
    if wilcoxon is None:
        lines.append("\n(scipy not available: no p-values)")

    # --- 3. breakdown by parameter class and deviation magnitude
    rows = []
    for cfg, df in data.items():
        for cls, g in df.groupby("param_class"):
            r = g["rank"].dropna()
            rows.append({"config": cfg, "group": cls, "n": int(len(r)), "mean_rank": float(r.mean()) if len(r) else np.nan,
                         "median_rank": float(r.median()) if len(r) else np.nan, "top5": float((r <= 5).mean()) if len(r) else np.nan})
        if "rel_dev" in df and df["rel_dev"].notna().any():
            bins = pd.cut(df["rel_dev"].abs(), [0, 0.05, 0.15, 0.2501], include_lowest=True,
                          labels=["|dev| <= 5%", "5-15%", "15-25%"])
            for b, g in df.groupby(bins, observed=False):
                r = g["rank"].dropna()
                rows.append({"config": cfg, "group": f"deviation {b}", "n": int(len(r)),
                             "mean_rank": float(r.mean()) if len(r) else np.nan,
                             "median_rank": float(r.median()) if len(r) else np.nan,
                             "top5": float((r <= 5).mean()) if len(r) else np.nan})
    pc = pd.DataFrame(rows)
    pc.to_csv(os.path.join(a.results, "per_class.csv"), index=False)
    if len(pc):
        piv = pc.pivot_table(index="group", columns="config", values="mean_rank")
        n = pc.pivot_table(index="group", columns="config", values="n")
        lines.append("\n## Mean rank by parameter class / deviation magnitude\n")
        cols = [c for c in ORDER if c in piv.columns]
        lines.append("| group | n | " + " | ".join(cols) + " |")
        lines.append("|---|---|" + "---|" * len(cols))
        for gname in piv.index:
            nn = int(n.loc[gname].max())
            lines.append(f"| {gname} | {nn} | " + " | ".join(f"{piv.loc[gname, c]:.2f}" for c in cols) + " |")
        out["per_group"] = rows

    # --- 4. LaTeX table
    tex = ["\\begin{tabular}{lcccc}", "\\hline",
           "\\textbf{Method} & \\textbf{Mean Rank [95\\,\\% CI]} & \\textbf{Median} & \\textbf{Top-5} & \\textbf{SAE} \\\\", "\\hline"]
    for cfg in ORDER:
        if cfg in out["configs"]:
            c = out["configs"][cfg]
            tex.append(f"{LABEL[cfg]} & {c['mean_rank']:.2f} [{c['mean_rank_ci95'][0]:.2f}, {c['mean_rank_ci95'][1]:.2f}] & "
                       f"{c['median_rank']:.0f} & {100 * c['topk'][5]:.1f}\\,\\% & {c['mean_sae']:.4f} \\\\")
    tex += ["\\hline", "\\end{tabular}"]
    with open(os.path.join(a.results, "table.tex"), "w") as f:
        f.write("\n".join(tex) + "\n")

    with open(os.path.join(a.results, "analysis.json"), "w") as f:
        json.dump(out, f, indent=2, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else str(o))
    with open(os.path.join(a.results, "analysis.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWritten: {a.results}/analysis.md, analysis.json, table.tex, per_class.csv")


if __name__ == "__main__":
    main()
