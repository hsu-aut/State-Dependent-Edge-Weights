#!/usr/bin/env python3
"""
Check where the fault-independent deviation pattern of the test cases comes from (debug run 2026-11-23:
~95 % of the alarmed sensor-steps are identical in all 24 cases).

Compares the single reference run used by data_preparation/dataframe_adjustment.py with a few raw fault runs:
  1. time grid of reference vs fault runs (sample spacing, number of samples, duration),
  2. raw signals (before any processing): reference vs fault run, and fault run vs fault run,
  3. the residual as computed by dataframe_adjustment.py (levels differenced per sample, resampled to 1 s,
     normalised by max|reference|), and the same with the levels differenced on the common 1 s grid.

Usage:
  python check_reference.py --ref <ModVA_online_stable_res_original.csv> --raw-dir <input dir of dataframe_adjustment.py> --n 4
"""
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

SENSORS = ['tank_B201.level', 'pipe_B201_V201.port_b.p', 'tank_B202.level', 'pipe_B202_V202.port_b.p',
           'tank_B203.level', 'pipe_B203_V203.port_b.p', 'FI201.V_flow', 'tank_B204.level',
           'pipe_B204_P202.port_b.p', 'pipe_V207_Tee4.port_b.m_flow']
ACT = ['V201.opening', 'V202.opening', 'V203.opening', 'P201.N', 'P202.N', 'V206.opening', 'V205.opening', 'V204.opening']


def grid(df):
    t = df["time"].astype(float).values
    dt = np.diff(t)
    return f"n={len(t)} t=[{t[0]:.2f}, {t[-1]:.2f}] dt median={np.median(dt):.4g} min={dt.min():.3g} max={dt.max():.3g}"


def on_1s(df, diff_levels_first):
    """diff_levels_first=True reproduces dataframe_adjustment.py (difference per raw sample, then 1 s mean)."""
    d = df[["time"] + [c for c in SENSORS + ACT if c in df.columns]].copy()
    d["time"] = d["time"].astype(float)
    if diff_levels_first:
        for c in d.columns:
            if "level" in c:
                d[c] = d[c] - d[c].shift(-1)
    d.index = pd.to_timedelta(d["time"], unit="s")
    d = d.drop(columns="time").resample("1s").mean().interpolate()
    if not diff_levels_first:
        for c in d.columns:
            if "level" in c:
                d[c] = d[c] - d[c].shift(-1)
    return d


def residual(ref, flt):
    idx = ref.index.intersection(flt.index)
    r = {}
    for c in SENSORS:
        a, b = ref.loc[idx, c].values, flt.loc[idx, c].values
        m = np.nanmax(np.abs(a))
        r[c] = np.where((a == 0) & (b == 0), 0, (b - a) / m) if m > 0 else np.zeros_like(a)
    return pd.DataFrame(r, index=idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    ref = pd.read_csv(a.ref)
    print("reference:", a.ref, "\n  ", grid(ref))
    missing = [c for c in SENSORS + ACT if c not in ref.columns]
    if missing:
        print("  columns missing in reference:", missing)

    dirs = sorted(p for p in a.raw_dir.iterdir() if p.is_dir())
    random.Random(a.seed).shuffle(dirs)
    runs = []
    for p in dirs[: a.n]:
        f = list(p.glob("*.parquet"))
        if len(f) != 1:
            continue
        df = pd.read_parquet(f[0])
        txt = list(p.glob("*.txt"))
        info = txt[0].read_text(encoding="utf-8", errors="replace").replace("\n", " | ")[:120] if txt else ""
        runs.append((p.name, df))
        print(f"\nfault run {p.name}: {info}\n   {grid(df)}")

    print("\n== raw signals: max |difference| / max |reference| over the common time span (no processing)")
    rt = ref["time"].astype(float).values
    for name, df in runs:
        ft = df["time"].astype(float).values
        t = np.arange(max(rt[0], ft[0]), min(rt[-1], ft[-1]), 1.0)
        row = []
        for c in SENSORS + ACT:
            if c not in df.columns or c not in ref.columns:
                continue
            x = np.interp(t, rt, ref[c].astype(float).values)
            y = np.interp(t, ft, df[c].astype(float).values)
            m = np.max(np.abs(x)) or 1.0
            row.append(f"{c.split('.')[0][-6:]}.{c.split('.')[-1][:5]}={np.max(np.abs(y - x)) / m:.3f}")
        print(f"  ref vs {name}:\n     " + "  ".join(row))
    if len(runs) >= 2:
        (n1, d1), (n2, d2) = runs[0], runs[1]
        t1, t2 = d1["time"].astype(float).values, d2["time"].astype(float).values
        t = np.arange(max(t1[0], t2[0]), min(t1[-1], t2[-1]), 1.0)
        row = []
        for c in SENSORS + ACT:
            if c in d1.columns and c in d2.columns:
                x = np.interp(t, t1, d1[c].astype(float).values)
                y = np.interp(t, t2, d2[c].astype(float).values)
                m = np.max(np.abs(x)) or 1.0
                row.append(f"{c.split('.')[0][-6:]}.{c.split('.')[-1][:5]}={np.max(np.abs(y - x)) / m:.3f}")
        print(f"  {n1} vs {n2}:\n     " + "  ".join(row))

    print("\n== residual as in dataframe_adjustment.py vs. levels differenced on the 1 s grid")
    print("   share of 1 s steps with |residual| > 0.05 (= alarm), per sensor")
    R0 = on_1s(ref, True)
    R1 = on_1s(ref, False)
    for name, df in runs:
        a0 = (residual(R0, on_1s(df, True)).abs() > 0.05).mean()
        a1 = (residual(R1, on_1s(df, False)).abs() > 0.05).mean()
        print(f"  {name}")
        print("     as implemented : " + "  ".join(f"{c.split('.')[0][-6:]}={v:.2f}" for c, v in a0.items()))
        print("     1 s differences: " + "  ".join(f"{c.split('.')[0][-6:]}={v:.2f}" for c, v in a1.items()))


if __name__ == "__main__":
    main()
