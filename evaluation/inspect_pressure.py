#!/usr/bin/env python3
"""
Where and when do the pressure signals of V201/V202 differ between runs that should be (almost) identical?
Hypothesis: the pressure in a pipe section that is cut off by a closed valve is numerically ill-defined.

Compares, on a 1 s grid, the stored fault run with its re-simulation and with the new nominal run:
for each sensor the share of time with |diff| > 5 % of max|stored|, the value range, and whether the large
differences coincide with the adjacent valve being closed.

  python inspect_pressure.py --stored-run <raw run dir> --reproduced <csv> --nominal <csv>
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PAIRS = {  # sensor -> adjacent valve opening
    "pipe_B201_V201.port_b.p": "V201.opening",
    "pipe_B202_V202.port_b.p": "V202.opening",
    "pipe_B203_V203.port_b.p": "V203.opening",
    "pipe_B204_P202.port_b.p": "P202.N",
}


def on_grid(df, t, cols):
    tt = df["time"].astype(float).values
    return {c: np.interp(t, tt, df[c].astype(float).values) for c in cols if c in df.columns}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stored-run", required=True, type=Path)
    ap.add_argument("--reproduced", required=True, type=Path)
    ap.add_argument("--nominal", required=True, type=Path)
    a = ap.parse_args()
    S = pd.read_parquet(next(a.stored_run.glob("*.parquet")))
    t = np.arange(0, 600, 1.0)
    cols = list(PAIRS) + list(PAIRS.values())
    s = on_grid(S, t, cols)
    for name, other in [("reproduced", pd.read_csv(a.reproduced)), ("nominal", pd.read_csv(a.nominal))]:
        o = on_grid(other, t, cols)
        print(f"\n== stored vs {name}")
        for p, v in PAIRS.items():
            if p not in s or p not in o:
                continue
            m = np.max(np.abs(s[p])) or 1.0
            big = np.abs(o[p] - s[p]) > 0.05 * m
            closed = s[v] <= 1e-6 if v in s else np.zeros_like(big)
            q = np.percentile(s[p], [0, 1, 50, 99, 100])
            print(f"  {p:26s} |diff|>5%: {big.mean():5.1%} of the time;  of these with {v} closed: "
                  f"{(big & closed).sum() / max(big.sum(), 1):5.1%}   ({v} closed {closed.mean():5.1%} of the time)")
            print(f"  {'':26s} stored range [min, 1%, median, 99%, max] = {np.array2string(q, precision=4)}")
            if big.any():
                idx = np.flatnonzero(big)
                runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
                print(f"  {'':26s} time windows: " + ", ".join(f"{t[r[0]]:.0f}-{t[r[-1]]:.0f}s" for r in runs[:8])
                      + (" ..." if len(runs) > 8 else ""))


if __name__ == "__main__":
    main()
