"""
step0_compare.py - compare two sets of edge-weight files (e.g. stored originals vs. recomputed).

Usage:
  python step0_compare.py <dir_A> <dir_B> [--modes mode_1_0_0_0_0_1 ...]

Each dir contains one subfolder per mode with kantengewichte_<mode>.csv (';' separated, ',' decimal).
Edges are matched by (Elternknoten, Kindknoten). Prints, per mode and separately for parameter and sensor
parent edges: number of edges, max |difference| of KL / beta / Var(X_i), and how many KL weights exceed the
pruning limit 0.01 in A and in B.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

COLS = ["MI_mit_Var_Xi", "MI_mit_Var_Xi_given_Z", "Beta_Absolut", "Var_Xi_Marginal"]


def load(d, mode):
    f = glob.glob(os.path.join(d, mode, "*.csv"))
    if not f:
        return None
    w = pd.read_csv(f[0], delimiter=";", decimal=",")
    w["is_param"] = w["Elternknoten"].str.contains(r"\(param\)", regex=True)
    return w.set_index(["Elternknoten", "Kindknoten"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir_a")
    ap.add_argument("dir_b")
    ap.add_argument("--modes", nargs="*")
    a = ap.parse_args()
    modes = a.modes or sorted(os.path.basename(p) for p in glob.glob(os.path.join(a.dir_b, "mode_*")))
    for m in modes:
        A, B = load(a.dir_a, m), load(a.dir_b, m)
        if A is None or B is None:
            print(f"{m}: missing in {'A' if A is None else 'B'}")
            continue
        j = A.add_suffix("_A").join(B.add_suffix("_B"), how="outer")
        print(f"\n== {m}: edges A={len(A)} B={len(B)} matched={int(j['MI_mit_Var_Xi_A'].notna().mul(j['MI_mit_Var_Xi_B'].notna()).sum())}")
        for kind, sel in (("parameter parents", j["is_param_A"].fillna(j["is_param_B"]).astype(bool)),
                          ("sensor parents", ~j["is_param_A"].fillna(j["is_param_B"]).astype(bool))):
            s = j[sel]
            parts = []
            for c in COLS:
                d = (pd.to_numeric(s[c + "_A"], errors="coerce") - pd.to_numeric(s[c + "_B"], errors="coerce")).abs()
                d = d[np.isfinite(d)]
                parts.append(f"max|d {c}|={d.max():.3g}" if len(d) else f"{c}: n/a")
            kl_a = int((pd.to_numeric(s["MI_mit_Var_Xi_A"], errors="coerce") > 0.01).sum())
            kl_b = int((pd.to_numeric(s["MI_mit_Var_Xi_B"], errors="coerce") > 0.01).sum())
            print(f"  {kind:18s} n={len(s):5d}  KL>0.01: A={kl_a:4d} B={kl_b:4d}  " + "  ".join(parts))


if __name__ == "__main__":
    main()
