#!/usr/bin/env python3
"""
How fault-specific are the deviation patterns of a test-case set? (old set: ~95-100 % of the alarmed
sensor-steps identical in all cases, debug run 2026-11-23)

For a stratified sample of cases (one per true parameter, round robin) it reports
  * cases without any alarm in the first --steps seconds (not diagnosable, "no_deviation" in step2),
  * alarm share per sensor,
  * share of alarmed sensor-steps that occur (same sensor, same time step, same sign) in >= 80 % of the cases,
  * mean pairwise Jaccard similarity of the alarm patterns between cases.

  python check_testcases.py --testcases <data_for_aroyyo dir> --n 48
"""
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd


def sample_cases(testcases, n, seed=1):
    """Stratified sample: one case per true parameter type, round robin. Returns (cases, number of types)."""
    groups = {}
    for p in sorted(x for x in testcases.iterdir() if (x / "ModVA_deviation_adjusted.parquet").exists()):
        groups.setdefault(p.name.rsplit("_", 1)[0], []).append(p)
    rng = random.Random(seed)
    for g in groups.values():
        rng.shuffle(g)
    keys, picked, i = sorted(groups), [], 0
    total = sum(map(len, groups.values()))
    while len(picked) < min(n, total):
        g = groups[keys[i % len(keys)]]
        if g:
            picked.append(g.pop())
        i += 1
    return picked, len(groups)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testcases", required=True, type=Path)
    ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--steps", type=int, default=300, help="diagnosis horizon of step2 (abort_time)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    picked, n_types = sample_cases(a.testcases, a.n, a.seed)

    pats, names, no_alarm = [], [], 0
    for p in picked:
        d = pd.read_parquet(p / "ModVA_deviation_adjusted.parquet").iloc[: a.steps + 1]
        m = d.to_numpy(dtype=float)
        if not np.any(m != 0):
            no_alarm += 1
        pats.append(m)
        names.append(p.name)
    cols = list(pd.read_parquet(picked[0] / "ModVA_deviation_adjusted.parquet").columns)
    T = min(x.shape[0] for x in pats)
    P = np.stack([x[:T] for x in pats])                        # case x time x sensor, values -1/0/1

    print(f"{a.testcases}: {len(picked)} cases ({n_types} parameter types), horizon {T} steps")
    print(f"cases without any alarm: {no_alarm}")
    print("alarm share per sensor:", {c.split('.')[0][-6:]: round(float(v), 3) for c, v in zip(cols, (P != 0).mean((0, 1)))})
    common =np.zeros(P.shape[1:], dtype=bool)
    for s in (+1, -1):
        common |= (P == s).mean(0) >= 0.8
    alarmed = P != 0
    share_common = (alarmed & common[None]).sum() / max(alarmed.sum(), 1)
    print(f"alarmed sensor-steps that occur identically in >= 80 % of the cases: {share_common:.1%}")
    A = alarmed.reshape(len(picked), -1)
    jac = []
    for i in range(len(picked)):
        for j in range(i + 1, len(picked)):
            u = np.logical_or(A[i], A[j]).sum()
            if u:
                jac.append(np.logical_and(A[i], A[j]).sum() / u)
    print(f"mean pairwise Jaccard similarity of the alarm patterns: {np.mean(jac):.3f} (1 = identical)")
    n_alarm = alarmed.sum((1, 2))
    print("alarmed sensor-steps per case: median", int(np.median(n_alarm)), " min", int(n_alarm.min()), " max", int(n_alarm.max()))


if __name__ == "__main__":
    main()
