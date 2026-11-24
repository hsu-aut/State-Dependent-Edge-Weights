#!/usr/bin/env python3
"""
Which fault types are diagnosable at all in a test-case set? (noise_vs_signal.py, 2026-11-23: with threshold 0.002
and 3 s persistence, detection saturates at ~37 % regardless of the fault magnitude -> depends on the parameter type.)

Reads the alarms (ModVA_deviation_adjusted.parquet, as written by regen_testcases.py) of ALL cases and reports per
parameter type: number of cases, share with at least one alarm in the horizon, the same for |rel. change| >= 5 %,
median alarmed sensor-steps of the alarmed cases, and the sensors that alarm most often. Optionally writes the list
of diagnosable cases (>= 1 alarm) as cases CSV for step2 (--out).

  python diag_by_type.py --testcases testcases_v4 --sweep sim_ref/parameter_combination.json [--out diagnosable_v4.csv]
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from detectability import read_parameters_txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testcases", required=True, type=Path)
    ap.add_argument("--sweep", required=True, type=Path)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--out", default="", help="write the cases with >= 1 alarm as CSV (columns case, param)")
    a = ap.parse_args()

    with open(a.sweep, encoding="utf-8") as f:
        baseline = json.load(f)[0]["baseline"]
    rows = []
    for p in sorted(x for x in a.testcases.iterdir() if (x / "ModVA_deviation_adjusted.parquet").exists()):
        name, val = read_parameters_txt(p / "parameters.txt")
        d = pd.read_parquet(p / "ModVA_deviation_adjusted.parquet").iloc[: a.steps + 1]
        m = d.to_numpy() != 0
        rel = val / float(baseline[name]) - 1.0 if name in baseline and val is not None and baseline[name] else np.nan
        top = [d.columns[j] for j in np.flatnonzero(m.any(0))]
        rows.append((p.name, p.name.rsplit("_", 1)[0], name, rel, int(m.sum()), top))
    df = pd.DataFrame(rows, columns=["case", "type", "param", "rel", "n_alarm", "sensors"])
    df["alarm"] = df.n_alarm > 0
    print(f"{a.testcases}: {len(df)} cases, {df.type.nunique()} parameter types, horizon {a.steps} s; "
          f"cases with >= 1 alarm: {df.alarm.sum()} ({df.alarm.mean():.1%})\n")
    print(f"{'parameter type':34s} {'cases':>5} {'alarm':>6} {'|chg|>=5%':>9} {'med steps':>9}  most frequent alarmed sensors")
    for t, g in sorted(df.groupby("type"), key=lambda x: -x[1].alarm.mean()):
        big = g[g.rel.abs() >= 0.05]
        sens = Counter(s for lst in g.sensors for s in lst).most_common(3)
        med = int(g.loc[g.alarm, "n_alarm"].median()) if g.alarm.any() else 0
        print(f"{t:34s} {len(g):5d} {g.alarm.mean():6.0%} {big.alarm.mean() if len(big) else float('nan'):9.0%} {med:9d}  "
              + ", ".join(f"{s.split('.')[0]} ({c})" for s, c in sens))
    n_types_never = int((df.groupby("type").alarm.mean() == 0).sum())
    n_types_some = int((df.groupby("type").alarm.mean() >= 0.5).sum())
    print(f"\ntypes never diagnosable: {n_types_never}; types with >= 50 % diagnosable cases: {n_types_some}")
    if a.out:
        df.loc[df.alarm, ["case", "param"]].to_csv(a.out, index=False)
        print(f"{df.alarm.sum()} diagnosable cases -> {a.out}")


if __name__ == "__main__":
    main()
