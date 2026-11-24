#!/usr/bin/env python3
"""
Detectability vs. fault magnitude, and the numerical noise floor of the test cases.

For each sampled case: relative parameter change (value in parameters.txt vs. the baseline of the parameter sweep,
parameter_combination.json from npy_to_json.py) and max |residual| over all sensors in the horizon. Reports, per bin
of |relative change|, the share of cases with an alarm at several thresholds. Cases with an almost unchanged
parameter (|change| < --null-tol) are practically fault-free: their max |residual| is the noise floor (simulation
tool / library differences between the stored fault runs and the new reference), and a usable threshold must lie
clearly above it.

  python detectability.py --testcases testcases_v3 --sweep sim_ref/parameter_combination.json --n 3000
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from check_testcases import sample_cases

THRESHOLDS = [0.05, 0.02, 0.01, 0.005, 0.002]
BINS = [0, 0.001, 0.01, 0.05, 0.10, 0.25, 0.50, np.inf]


def read_parameters_txt(path):
    name, val = None, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("Geändert:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("Wert:"):
                val = float(line.split(":", 1)[1].strip())
    return name, val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testcases", required=True, type=Path)
    ap.add_argument("--sweep", required=True, type=Path, help="parameter_combination.json (npy_to_json.py)")
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--null-tol", type=float, default=0.001, help="|relative change| below this = fault-free")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    with open(a.sweep, encoding="utf-8") as f:
        baseline = json.load(f)[0]["baseline"]
    picked, n_types = sample_cases(a.testcases, a.n, a.seed)
    rows, missing = [], 0
    for p in picked:
        name, val = read_parameters_txt(p / "parameters.txt")
        if name not in baseline or val is None or not baseline[name]:
            missing += 1
            continue
        r = pd.read_parquet(p / "ModVA_residual_adjusted.parquet").to_numpy(dtype=float)[: a.steps + 1]
        rows.append((p.name, name, val / float(baseline[name]) - 1.0, float(np.abs(r).max())))
    df = pd.DataFrame(rows, columns=["case", "param", "rel_change", "max_res"])
    print(f"{a.testcases}: {len(df)} cases ({n_types} parameter types), horizon {a.steps} s, "
          f"{missing} without parameter/baseline")
    q = np.percentile(df.rel_change, [0, 5, 25, 50, 75, 95, 100])
    print("relative parameter change [min, 5, 25, 50, 75, 95 %, max]:", np.array2string(q, precision=3))

    df["bin"] = pd.cut(df.rel_change.abs(), BINS, right=False)
    print(f"\n{'|rel. change|':>16} {'cases':>6} {'median max|res|':>15}  " + " ".join(f"thr {t:<6}" for t in THRESHOLDS))
    for b, g in df.groupby("bin", observed=True):
        print(f"{str(b):>16} {len(g):6d} {g.max_res.median():15.4f}  "
              + " ".join(f"{(g.max_res > t).mean():10.1%}" for t in THRESHOLDS))

    null = df[df.rel_change.abs() < a.null_tol]
    print(f"\nfault-free cases (|rel. change| < {a.null_tol}): {len(null)}")
    if len(null):
        print("  max |residual| [min, 50, 90 %, max]:",
              np.array2string(np.percentile(null.max_res, [0, 50, 90, 100]), precision=4))
        print("  " + null.sort_values("max_res", ascending=False).head(8)[["case", "rel_change", "max_res"]].to_string(index=False).replace("\n", "\n  "))
    else:
        small = df.loc[df.rel_change.abs().nsmallest(8).index, ["case", "rel_change", "max_res"]]
        print("  none; the 8 smallest changes:\n  " + small.to_string(index=False).replace("\n", "\n  "))


if __name__ == "__main__":
    main()
