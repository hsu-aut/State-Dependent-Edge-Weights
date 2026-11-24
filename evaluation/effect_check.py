#!/usr/bin/env python3
"""
Do the never-diagnosable fault parameters change the simulation at all? (diag_by_type.py on testcases_v4,
2026-11-23: all valve dp_nominal / m_flow_nominal, 19 of 21 pipe roughnesses and pipe_Tee3_V207.diameter have 0 %
diagnosable cases even at +-30 %.)

For each parameter type: the raw fault run with the largest |relative change| is compared with the nominal run over
ALL simulated variables (not only the sensors), on a 1 s grid over the diagnosis horizon, as |diff| / max |nominal|:
the persistent change (largest level exceeded for >= 3 consecutive seconds, the alarm rule of testcases_v4) and the
median change over time (offset vs. spike). The first version (max |diff|) was dominated by 1-s spikes, closed
sections and branches without flow (pipe_Tee3_V207). Reported:
  * the value of the parameter itself in the result file, if it is written there (was it really set?),
  * the variables of the affected component (name contains the component, e.g. "V201." or "pipe_B201_V201."),
  * the 5 most changed variables overall and the largest change among the 10 sensors.
A diameter fault (diagnosable) serves as positive control. If even the component's own variables do not change,
the parameter has no effect in the model (data-generation issue); if they change but the sensors do not, the fault
is not observable with this sensor set (limitation).

  python effect_check.py --raw-dir /beegfs/project/ma-kausalegraphen --nominal sim_ref/ModVA_online_stable_V6_nominal.csv \
      --sweep sim_ref/parameter_combination.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from check_reference import SENSORS
from detectability import read_parameters_txt

DEFAULT_TYPES = ["pipe_B201_V201.diameter", "V201.dp_nominal", "V201.m_flow_nominal", "V205.dp_nominal",
                 "pipe_B201_V201.roughness", "pipe_FI201_B204.roughness", "pipe_Tee3_V207.diameter"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--nominal", required=True, type=Path)
    ap.add_argument("--sweep", required=True, type=Path)
    ap.add_argument("--types", default=",".join(DEFAULT_TYPES))
    ap.add_argument("--horizon", type=float, default=300.0, help="seconds compared (diagnosis horizon)")
    a = ap.parse_args()

    with open(a.sweep, encoding="utf-8") as f:
        baseline = json.load(f)[0]["baseline"]
    nom = pd.read_csv(a.nominal)
    tn = nom["time"].astype(float).values
    for typ in a.types.split(","):
        best = None
        for d in sorted(a.raw_dir.glob(f"{typ}_*")):
            if not (d / "parameters.txt").exists():
                continue
            name, val = read_parameters_txt(d / "parameters.txt")
            if name in baseline and val is not None and baseline[name]:
                rel = val / float(baseline[name]) - 1.0
                if best is None or abs(rel) > abs(best[2]):
                    best = (d, name, rel, val)
        if best is None:
            print(f"\n=== {typ}: no raw runs found")
            continue
        d, name, rel, val = best
        run = pd.read_parquet(next(d.glob("*.parquet")))
        tr = run["time"].astype(float).values
        t = np.arange(0.0, min(a.horizon, tr[-1], tn[-1]) + 1e-9, 1.0)  # 1 s grid as in the test cases
        diffs, const = {}, set()
        for c in run.columns:
            if c == "time" or c not in nom.columns:
                continue
            try:
                x = np.interp(t, tn, nom[c].astype(float).values)
                y = np.interp(t, tr, run[c].astype(float).values)
            except (ValueError, TypeError):
                continue
            scale = np.max(np.abs(x)) or 1.0
            r = np.abs(y - x) / scale
            # persistent change: largest level exceeded for >= 3 consecutive seconds (alarm rule of testcases_v4)
            p3 = float(np.max(np.minimum(np.minimum(r[:-2], r[1:-1]), r[2:]))) if len(r) > 2 else float(r.max())
            diffs[c] = (p3, float(np.median(r)), float(scale))
            if np.ptp(x) == 0 and np.ptp(y) == 0:
                const.add(c)  # parameter or constant (changed parameters / derived constants show up here)
        fmt = lambda c, v, pre="": f"{c[len(pre):]}={v[0]:.1e}/{v[1]:.0e} (max|nom| {v[2]:.1e})"
        comp = name.rsplit(".", 1)[0] + "."
        print(f"\n=== {typ}: run {d.name}, {name} = {val:g} (baseline {baseline[name]:g}, {rel:+.1%}); "
              f"{len(diffs)} common variables, first {t[-1]:.0f} s; values: persistent (>= 3 s) / median change")
        if name in run.columns:
            print(f"  parameter in result file: run {run[name].iloc[0]:g}, nominal "
                  f"{nom[name].iloc[0] if name in nom.columns else float('nan'):g}")
        pc = sorted(((c, v) for c, v in diffs.items() if c in const and v[0] > 1e-9), key=lambda x: -x[1][0])
        print(f"  changed constants/parameters ({len(pc)} > 1e-9): " + ", ".join(f"{c}={v[0]:.1e}" for c, v in pc[:4]))
        own = sorted(((c, v) for c, v in diffs.items() if c.startswith(comp) and c not in const), key=lambda x: -x[1][0])
        print(f"  {comp[:-1]} ({len(own)} time-varying): " + ", ".join(fmt(c, v, comp) for c, v in own[:6]))
        top = sorted(((c, v) for c, v in diffs.items() if c not in const), key=lambda x: -x[1][0])[:5]
        print("  most changed overall: " + ", ".join(fmt(c, v) for c, v in top))
        print("  sensors: " + ", ".join(f"{c.split('.')[0]}.{c.split('.')[-1]}={diffs[c][0]:.1e}/{diffs[c][1]:.0e}"
                                        for c in SENSORS if c in diffs))

if __name__ == "__main__":
    main()
