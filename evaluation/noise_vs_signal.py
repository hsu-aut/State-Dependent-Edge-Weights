#!/usr/bin/env python3
"""
Can numerical noise be separated from fault effects?  (detectability.py, 2026-11-23: cases with an almost unchanged
parameter (|rel. change| < 0.1 %) still reach max |residual| up to 0.043; 24 % of them alarm at threshold 0.002.)

Part 1, what the noise looks like: for the near-fault-free cases, the sensor and time of the largest residual,
how long it stays above 0.005 (longest run of consecutive seconds), and whether an actuator switches within +-3 s
(XMV.parquet).
Part 2, decision table: an alarm counts only if |residual| > threshold for >= k consecutive seconds (persistence).
For each (threshold, k): false-alarm rate = share of near-fault-free cases with any alarm, detection rate per
fault-magnitude bin. A usable setting has false-alarm rate ~0 and high detection.

  python noise_vs_signal.py --testcases testcases_v3 --sweep sim_ref/parameter_combination.json --n 3000
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from check_testcases import sample_cases
from detectability import read_parameters_txt

THRESHOLDS = [0.05, 0.02, 0.01, 0.005, 0.002]
PERSIST = [1, 3, 5, 10, 20]
SIGNAL_BINS = [(0.01, 0.05), (0.05, 0.10), (0.10, np.inf)]


def longest_run(mask):
    """mask: time x sensor bool -> longest run of consecutive True per sensor."""
    best = np.zeros(mask.shape[1], dtype=int)
    cur = np.zeros(mask.shape[1], dtype=int)
    for row in mask:
        cur = np.where(row, cur + 1, 0)
        best = np.maximum(best, cur)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testcases", required=True, type=Path)
    ap.add_argument("--sweep", required=True, type=Path)
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--null-tol", type=float, default=0.001)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    with open(a.sweep, encoding="utf-8") as f:
        baseline = json.load(f)[0]["baseline"]
    picked, _ = sample_cases(a.testcases, a.n, a.seed)
    cases = []
    for p in picked:
        name, val = read_parameters_txt(p / "parameters.txt")
        if name not in baseline or val is None or not baseline[name]:
            continue
        res = pd.read_parquet(p / "ModVA_residual_adjusted.parquet")
        r = np.abs(res.to_numpy(dtype=float)[: a.steps + 1])
        rel = val / float(baseline[name]) - 1.0
        cases.append(dict(case=p.name, rel=rel, cols=list(res.columns), path=p,
                          runs={t: longest_run(r > t).max() for t in THRESHOLDS},
                          r=r if abs(rel) < a.null_tol else None))  # keep the matrix only where needed (memory)
    null = [c for c in cases if abs(c["rel"]) < a.null_tol]
    print(f"{len(cases)} cases, {len(null)} near-fault-free (|rel. change| < {a.null_tol}), horizon {a.steps} s")

    print("\n=== part 1: the largest residuals of the near-fault-free cases")
    xmv_cols = None
    for c in sorted(null, key=lambda c: -c["r"].max())[:10]:
        r = c["r"]
        t, s = np.unravel_index(np.argmax(r), r.shape)
        run = longest_run(r[:, [s]] > 0.005)[0]
        xmv = pd.read_parquet(c["path"] / "XMV.parquet").to_numpy(dtype=float)[: a.steps + 1]
        if xmv_cols is None:
            xmv_cols = list(pd.read_parquet(c["path"] / "XMV.parquet").columns)
        lo, hi = max(t - 3, 1), min(t + 4, len(xmv))
        switched = [xmv_cols[j] for j in range(xmv.shape[1]) if np.any(np.abs(np.diff(xmv[lo - 1:hi, j])) > 1e-6)]
        above = np.flatnonzero(r[:, s] > 0.005)
        print(f"  {c['case']:34s} rel {c['rel']:+.5f}  max {r[t, s]:.3f} at t={t:3d}s {c['cols'][s]:28s} "
              f"> 0.005 for {len(above):3d} s (longest run {run:3d} s, first {above[0] if len(above) else '-'} s)  "
              f"actuator switch +-3 s: {', '.join(switched) or 'none'}")

    print("\n=== part 2: alarm if |residual| > threshold for >= k consecutive seconds")
    hdr = "  ".join(f"|chg| {lo:.0%}-{hi:.0%}" if np.isfinite(hi) else f"|chg| >={lo:.0%}" for lo, hi in SIGNAL_BINS)
    print(f"{'thr':>6} {'k':>3}  {'false alarm (null)':>18}  {hdr}")
    for t in THRESHOLDS:
        for k in PERSIST:
            fa = np.mean([c["runs"][t] >= k for c in null]) if null else float("nan")
            det = []
            for lo, hi in SIGNAL_BINS:
                g = [c["runs"][t] >= k for c in cases if lo <= abs(c["rel"]) < hi]
                det.append(f"{np.mean(g):11.1%} (n={len(g)})" if g else f"{'-':>11}")
            print(f"{t:6.3f} {k:3d}  {fa:18.1%}  " + "  ".join(det))


if __name__ == "__main__":
    main()
