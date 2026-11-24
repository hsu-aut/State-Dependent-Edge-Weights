#!/usr/bin/env python3
"""
How many test cases become diagnosable at lower alarm thresholds / longer horizons?
(testcases_v3, masked, threshold 0.05, 300 s: 37/48 sample cases without any alarm, 2026-11-23)

Recomputes the alarms from the stored residuals (ModVA_residual_adjusted.parquet, (faulty - ref) / max|ref|,
rounded to 3 decimals by dataset_comparison.py, so thresholds below 0.001 are meaningless) for a stratified
sample of cases and reports per (horizon, threshold):
  * share of cases with at least one alarm,
  * alarmed sensor-steps per case (median / 90 %),
  * share of alarmed sensor-steps identical (same sensor, step, sign) in >= 80 % of the cases (artefact indicator:
    old test cases 93.5 %), and the mean pairwise Jaccard similarity of the alarm patterns,
  * alarm share per sensor,
and, per threshold, the parameter types for which no sampled case has an alarm.

  python threshold_sweep.py --testcases testcases_v3 --n 540
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from check_testcases import sample_cases

THRESHOLDS = [0.05, 0.02, 0.01, 0.005, 0.002, 0.001]
HORIZONS = [300, 600]


def stats(R, t):
    """R: cases x time x sensor residuals. Returns a dict of summary numbers for threshold t."""
    P = np.where(np.abs(R) > t, np.sign(R), 0).astype(np.int8)
    alarmed = P != 0
    n_alarm = alarmed.sum((1, 2))
    common = np.zeros(P.shape[1:], dtype=bool)
    for s in (+1, -1):
        common |= (P == s).mean(0) >= 0.8
    share_common = (alarmed & common[None]).sum() / max(alarmed.sum(), 1)
    A = alarmed.reshape(len(P), -1).astype(np.int32)
    inter = A @ A.T
    sizes = A.sum(1)
    union = sizes[:, None] + sizes[None, :] - inter
    iu = np.triu_indices(len(P), 1)
    ok = union[iu] > 0
    jac = float((inter[iu][ok] / union[iu][ok]).mean()) if ok.any() else float("nan")
    return dict(diag=(n_alarm > 0).mean(), med=np.median(n_alarm), p90=np.percentile(n_alarm, 90),
                common=share_common, jac=jac, per_sensor=alarmed.mean((0, 1)), any_case=n_alarm > 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testcases", required=True, type=Path)
    ap.add_argument("--n", type=int, default=540, help="sample size (stratified, about 10 per parameter type)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    picked, n_types = sample_cases(a.testcases, a.n, a.seed)
    res = [pd.read_parquet(p / "ModVA_residual_adjusted.parquet") for p in picked]
    cols = list(res[0].columns)
    T = min(len(r) for r in res)
    R_all = np.stack([r[cols].to_numpy(dtype=float)[:T] for r in res])      # case x time x sensor
    types = np.array([p.name.rsplit("_", 1)[0] for p in picked])
    print(f"{a.testcases}: {len(picked)} cases, {n_types} parameter types, {T} stored steps")
    q = np.percentile(np.abs(R_all).max((1, 2)), [0, 25, 50, 75, 90, 100])
    print("max |residual| per case over all sensors and steps [min, 25, 50, 75, 90 %, max]:",
          np.array2string(q, precision=4))

    short = [c.split(".")[0][-6:] for c in cols]
    for H in HORIZONS:
        if H + 1 > T:
            print(f"\n(horizon {H} s skipped: only {T} steps stored)")
            continue
        R = R_all[:, : H + 1]
        print(f"\n=== horizon {H} s")
        print(f"{'threshold':>9} {'cases w/ alarm':>14} {'median':>7} {'p90':>6} {'common>=80%':>11} {'Jaccard':>7}   per sensor")
        for t in THRESHOLDS:
            s = stats(R, t)
            ps = " ".join(f"{n}:{v:.3f}" for n, v in zip(short, s["per_sensor"]))
            print(f"{t:9.3f} {s['diag']:14.1%} {s['med']:7.0f} {s['p90']:6.0f} {s['common']:11.1%} {s['jac']:7.3f}   {ps}")
            never = sorted(set(types) - set(types[s["any_case"]]))
            print(f"{'':9} parameter types without any alarmed case: {len(never)}/{n_types}"
                  + (f"  e.g. {', '.join(never[:6])}" if never else ""))


if __name__ == "__main__":
    main()
