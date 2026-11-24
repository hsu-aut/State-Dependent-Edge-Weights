#!/usr/bin/env python3
"""
Compare a re-simulated fault run with the stored original (validation of the OpenModelica version) and check
that the new nominal reference has the same actuator schedule as the fault runs.

  python compare_runs.py --stored-run <raw run dir> --reproduced <reproduce_<run>.csv> --nominal <..._nominal.csv>
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from check_reference import SENSORS, ACT, grid


def rel_diff(a, b, cols):
    ta, tb = a["time"].astype(float).values, b["time"].astype(float).values
    t = np.arange(max(ta[0], tb[0]), min(ta[-1], tb[-1]), 0.5)
    out = {}
    for c in cols:
        if c in a.columns and c in b.columns:
            x = np.interp(t, ta, a[c].astype(float).values)
            y = np.interp(t, tb, b[c].astype(float).values)
            out[c] = np.max(np.abs(y - x)) / (np.max(np.abs(x)) or 1.0)
    return out


def show(title, d):
    print(title)
    print("   " + "  ".join(f"{c.split('.')[0][-6:]}.{c.split('.')[-1][:5]}={v:.2e}" for c, v in d.items()))
    print(f"   max over all: {max(d.values()):.2e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stored-run", required=True, type=Path)
    ap.add_argument("--reproduced", required=True, type=Path)
    ap.add_argument("--nominal", required=True, type=Path)
    a = ap.parse_args()
    stored = pd.read_parquet(next(a.stored_run.glob("*.parquet")))
    rep = pd.read_csv(a.reproduced)
    nom = pd.read_csv(a.nominal)
    print("stored    :", grid(stored))
    print("reproduced:", grid(rep))
    print("nominal   :", grid(nom))
    print("columns only in stored:", sorted(set(stored.columns) - set(rep.columns))[:10],
          " only in reproduced:", sorted(set(rep.columns) - set(stored.columns))[:10])
    show("\n1) reproduced vs stored fault run (max |diff| / max |stored|) - should be ~0 if the version reproduces:",
         rel_diff(stored, rep, SENSORS + ACT))
    allc = [c for c in stored.columns if c != "time" and c in rep.columns]
    d = rel_diff(stored, rep, allc)
    worst = sorted(d.items(), key=lambda kv: -kv[1])[:5]
    print("   largest differences over all", len(allc), "common columns:", [(c, f"{v:.2e}") for c, v in worst])
    show("\n2) nominal vs stored fault run, actuators (should be 0: same schedule):", rel_diff(stored, nom, ACT))
    show("\n3) nominal vs stored fault run, sensors (= effect of the fault):", rel_diff(stored, nom, SENSORS))


if __name__ == "__main__":
    main()
