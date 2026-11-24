#!/usr/bin/env python3
"""
Step 1 - read-only inventory of the data on HSUper.

Answers the open questions of the paper revision without running the diagnosis:
  * Which input paths are readable?
  * How many sweep runs were configured / completed (18,600 vs. ~12,000)?
  * How many operating states (mode files) and weight files exist, how large are they?
  * How many test cases exist, are they identical to sweep runs (train/test overlap)?
  * Which deviation threshold was used (bracketed from residual vs. deviation files)?

Nothing is written outside --out. Usage:
  python step1_inventory.py --out inventory
"""
import argparse
import json
import os
import re
import sys
import traceback
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

try:
    import pyarrow.parquet as pq
except ImportError:  # row counts then fall back to pandas
    pq = None

CODE = "/beegfs/project/ma-kausalegraphen/m778332/masterarbeit/Code"  # moved from /beegfs/home/m/m778332 (2026-11-20)
DEFAULTS = {
    "sweep_root": "/beegfs/project/ma-kausalegraphen",
    "intermediate_dir": f"{CODE}/Data/intermediate_parquets",
    "modes_dir": f"{CODE}/Data/mode_parquets_final_dask",
    "weights_dir": f"{CODE}/Data/mode_parquets_final_dask/weights",
    "testcases_root": f"{CODE}/Data/data_for_aroyyo",
    "aml": f"{CODE}/Data/models/ModVA_Mixer_incl_SensorNamingConvention_reduced_V2.aml",
    "designations": f"{CODE}/Data/models/ModVA_Designations.xlsx",
}
TC_FILES = {
    "alarms": "ModVA_deviation_adjusted.parquet",
    "xmv": "XMV.parquet",
    "residuals": "ModVA_residual_adjusted.parquet",
    "parameters": "parameters.txt",
    "modi_df": "modi_df.parquet",
}
ABORT_TIME = 300
CHANGED_RE = re.compile(r"^Ge\S{0,3}ndert\s*:", re.IGNORECASE)  # "Geändert:" in any encoding
VALUE_RE = re.compile(r"^Wert\s*:", re.IGNORECASE)

LOG = []


def log(msg=""):
    print(msg, flush=True)
    LOG.append(str(msg))


def read_param_txt(path):
    name, val = None, None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if CHANGED_RE.match(s):
                name = s.split(":", 1)[1].strip()
            elif VALUE_RE.match(s):
                try:
                    val = float(s.split(":", 1)[1].strip())
                except ValueError:
                    pass
    return name, val


def n_rows(path):
    if pq is not None:
        return pq.ParquetFile(path).metadata.num_rows
    return len(pd.read_parquet(path))


def list_subdirs(root):
    with os.scandir(root) as it:
        return sorted(e.name for e in it if e.is_dir())


def section_paths(a):
    log("== 1. Paths ==")
    ok = {}
    for key in DEFAULTS:
        p = getattr(a, key)
        exists = os.path.exists(p)
        readable = os.access(p, os.R_OK) if exists else False
        ok[key] = exists and readable
        log(f"  {key:17s} exists={exists!s:5s} readable={readable!s:5s} {p}")
    return ok


def section_sweep(a, out):
    log("\n== 2. Parameter sweep (raw runs) ==")
    all_dirs = list_subdirs(a.sweep_root)
    dirs = [d for d in all_dirs if re.match(r"^.+_\d{5}$", d)]  # run folders only ("<param>_<idx:05d>")
    run_set = set(dirs)
    other = [d for d in all_dirs if d not in run_set]
    if other:
        log(f"  ignored non-run folders in sweep root: {', '.join(other[:10])}{' ...' if len(other) > 10 else ''}")
    rows = []
    for d in dirs:
        folder = os.path.join(a.sweep_root, d)
        try:
            files = os.listdir(folder)
        except OSError as e:
            rows.append({"run": d, "has_parquet": False, "has_txt": False, "param": None, "value": None, "error": str(e)})
            continue
        pq_file = next((f for f in files if f.lower().endswith(".parquet")), None)
        has_pq = pq_file is not None
        rows_pq, pq_err = None, None
        if has_pq:  # reads only the parquet footer -> cheap; detects aborted/corrupt runs
            try:
                rows_pq = n_rows(os.path.join(folder, pq_file))
            except Exception as e:  # noqa: BLE001
                pq_err = f"{type(e).__name__}: {e}"
        txt = next((f for f in files if f.lower().endswith(".txt")), None)
        name, val = (None, None)
        if txt:
            try:
                name, val = read_param_txt(os.path.join(folder, txt))
            except OSError:
                pass
        if name is None:  # simulate.py names folders "<param>_<idx:05d>"
            m = re.match(r"^(.*)_(\d{5})$", d)
            name = m.group(1) if m else None
        rows.append({"run": d, "has_parquet": has_pq, "has_txt": txt is not None, "param": name, "value": val,
                     "n_rows": rows_pq, "error": pq_err})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, "sweep_runs.csv"), index=False)
    n_total = len(df)
    n_complete = int((df["has_parquet"] & df["has_txt"]).sum()) if n_total else 0
    log(f"  run folders: {n_total}   completed (parquet + txt): {n_complete}   without parquet: {n_total - n_complete}")
    if n_total:
        per = df.groupby("param").agg(folders=("run", "size"), completed=("has_parquet", "sum"))
        per.to_csv(os.path.join(out, "sweep_per_parameter.csv"))
        log(f"  distinct parameters: {per.shape[0]}")
        log(f"  completed runs per parameter: min={int(per['completed'].min())} median={int(per['completed'].median())} max={int(per['completed'].max())}")
        # Row counts: a full run (0-600 s) should have ~12,645 output steps; shorter files = aborted simulations
        r = df["n_rows"].dropna().astype(int)
        n_unreadable = int(df["error"].notna().sum())
        if len(r):
            full = int(r.max())
            log(f"  parquet rows: max={full} median={int(r.median())} min={int(r.min())}   unreadable parquets: {n_unreadable}")
            log(f"  runs with full length (rows >= 99% of max): {int((r >= 0.99 * full).sum())}   shorter: {int((r < 0.99 * full).sum())}")
            log("  most frequent row counts: " + ", ".join(f"{k}x{v}" for k, v in r.value_counts().head(8).items()))
            per_full = df[df["n_rows"] >= 0.99 * full].groupby("param").size()
            per = per.join(per_full.rename("full_length"), how="left").fillna({"full_length": 0})
            per.to_csv(os.path.join(out, "sweep_per_parameter.csv"))
    return df


def section_intermediate(a):
    log("\n== 3. Intermediate parquets (input to the mode segmentation) ==")
    if not os.path.isdir(a.intermediate_dir):
        log("  not found")
        return None
    files = [f for f in os.listdir(a.intermediate_dir) if f.startswith("intermediate__") and f.endswith(".parquet")]
    log(f"  intermediate files: {len(files)}  (= runs that entered the weight learning)")
    return len(files)


def section_modes(a, out):
    log("\n== 4. Operating states and weights ==")
    res = {}
    if os.path.isdir(a.modes_dir):
        mode_files = sorted(f for f in os.listdir(a.modes_dir) if f.startswith("mode_") and f.endswith(".parquet"))
        rows = []
        for f in mode_files:
            try:
                rows.append({"mode": f[:-8], "rows": n_rows(os.path.join(a.modes_dir, f))})
            except Exception as e:
                rows.append({"mode": f[:-8], "rows": None, "error": str(e)})
        mdf = pd.DataFrame(rows)
        mdf.to_csv(os.path.join(out, "modes.csv"), index=False)
        log(f"  mode files (operating states with data): {len(mode_files)}")
        if len(mdf) and mdf["rows"].notna().any():
            r = mdf["rows"].dropna()
            log(f"  rows per mode: min={int(r.min())} median={int(r.median())} max={int(r.max())} total={int(r.sum())}")
        res["n_mode_files"] = len(mode_files)
    else:
        log("  modes dir not found")

    if os.path.isdir(a.weights_dir):
        wdirs = list_subdirs(a.weights_dir)
        log(f"  weight folders: {len(wdirs)}")
        res["n_weight_folders"] = len(wdirs)
        stats = []
        cols_seen = Counter()
        for wd in wdirs:
            p = os.path.join(a.weights_dir, wd)
            csv = next((f for f in os.listdir(p) if f.endswith(".csv") and f.startswith("kantengewichte")), None)
            if csv is None:
                csv = next((f for f in os.listdir(p) if f.endswith(".csv") and not f.startswith("df_flat")), None)
            if csv is None:
                stats.append({"mode": wd, "csv": None})
                continue
            try:
                w = pd.read_csv(os.path.join(p, csv), delimiter=";", decimal=",")
            except Exception as e:
                stats.append({"mode": wd, "csv": csv, "error": str(e)})
                continue
            cols_seen.update(w.columns)
            row = {"mode": wd, "csv": csv, "edges": len(w),
                   "edge_id_missing": int(pd.to_numeric(w.get("Original_Edge_ID"), errors="coerce").isna().sum())
                   if "Original_Edge_ID" in w else None}
            for c in ("MI_mit_Var_Xi", "MI_mit_Var_Xi_given_Z", "Beta_Absolut"):
                if c in w:
                    v = pd.to_numeric(w[c], errors="coerce")
                    row[f"{c}_gt1"] = int((v > 1).sum())
                    row[f"{c}_le0.01"] = int((v <= 0.01).sum())
                    row[f"{c}_inf"] = int(np.isinf(v).sum())
                    row[f"{c}_max"] = float(v[np.isfinite(v)].max()) if np.isfinite(v).any() else None
            stats.append(row)
        sdf = pd.DataFrame(stats)
        sdf.to_csv(os.path.join(out, "weights_per_mode.csv"), index=False)
        log(f"  weight CSV columns seen: {dict(cols_seen)}")
        for c in ("MI_mit_Var_Xi", "MI_mit_Var_Xi_given_Z", "Beta_Absolut"):
            if f"{c}_gt1" in sdf:
                log(f"  {c}: weights > 1: {int(sdf[f'{c}_gt1'].sum())}, <= 0.01 (pruned in path search): "
                    f"{int(sdf[f'{c}_le0.01'].sum())}, inf: {int(sdf[f'{c}_inf'].sum())}")
    else:
        log("  weights dir not found")
    return res


def section_testcases(a, out, sweep_df):
    log("\n== 5. Test cases ==")
    if not os.path.isdir(a.testcases_root):
        log("  not found")
        return {}
    cases = list_subdirs(a.testcases_root)
    log(f"  test case folders: {len(cases)}")

    # index of sweep runs by (param, value) for the overlap check
    sweep_index = defaultdict(list)
    sweep_names = set()
    if sweep_df is not None and len(sweep_df):
        sweep_names = set(sweep_df["run"])
        for _, r in sweep_df.dropna(subset=["param", "value"]).iterrows():
            sweep_index[r["param"]].append(float(r["value"]))
    sweep_arr = {k: np.array(v) for k, v in sweep_index.items()}

    weight_modes = set(list_subdirs(a.weights_dir)) if os.path.isdir(a.weights_dir) else set()

    rows = []
    thr_no_dev, thr_dev = [], []  # |residual| where deviation == 0 / != 0
    first_columns = None
    for i, c in enumerate(cases):
        folder = os.path.join(a.testcases_root, c)
        row = {"case": c}
        try:
            present = {k: os.path.exists(os.path.join(folder, f)) for k, f in TC_FILES.items()}
            row.update({f"has_{k}": v for k, v in present.items()})
            name, val = (None, None)
            if present["parameters"]:
                name, val = read_param_txt(os.path.join(folder, TC_FILES["parameters"]))
            row["param"], row["value"] = name, val
            row["folder_name_in_sweep"] = c in sweep_names
            if name in sweep_arr and val is not None:
                d = np.abs(sweep_arr[name] - val) / max(abs(val), 1e-30)
                row["min_rel_diff_to_sweep_value"] = float(d.min())
                row["value_in_sweep"] = bool(d.min() < 1e-6)
            else:
                row["min_rel_diff_to_sweep_value"] = None
                row["value_in_sweep"] = None

            if present["alarms"]:
                al = pd.read_parquet(os.path.join(folder, TC_FILES["alarms"]))
                if first_columns is None:
                    first_columns = {"alarms_columns": list(map(str, al.columns)),
                                     "alarms_index_head": list(map(str, al.index[:3]))}
                row["n_steps"] = len(al)
                sub = al.iloc[: ABORT_TIME + 1, :10].apply(pd.to_numeric, errors="coerce").fillna(0)
                row["n_alarm_steps_first301"] = int((sub != 0).any(axis=1).sum())
                row["n_alarm_steps_all"] = int((al.iloc[:, :10].apply(pd.to_numeric, errors="coerce").fillna(0) != 0).any(axis=1).sum())
                if present["residuals"]:
                    rs = pd.read_parquet(os.path.join(folder, TC_FILES["residuals"]))
                    n = min(al.shape[1], rs.shape[1], 10)
                    m = min(len(al), len(rs))
                    A = al.iloc[:m, :n].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
                    R = np.abs(rs.iloc[:m, :n].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float))
                    ok = np.isfinite(A) & np.isfinite(R)
                    if (ok & (A == 0)).any():
                        thr_no_dev.append(float(R[ok & (A == 0)].max()))
                    if (ok & (A != 0)).any():
                        thr_dev.append(float(R[ok & (A != 0)].min()))
            if present["modi_df"]:
                md = pd.read_parquet(os.path.join(folder, TC_FILES["modi_df"]))
                names = {"mode_" + "_".join(map(str, r)) for r in md.iloc[: ABORT_TIME + 1].astype(int).itertuples(index=False)}
                row["n_modes_first301"] = len(names)
                row["n_modes_without_weights"] = len(names - weight_modes) if weight_modes else None
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        rows.append(row)
        if (i + 1) % 200 == 0:
            log(f"  ... {i + 1}/{len(cases)} test cases read")

    tdf = pd.DataFrame(rows)
    tdf.to_csv(os.path.join(out, "testcases.csv"), index=False)
    res = {"n_testcases": len(cases)}
    if first_columns:
        log(f"  alarm file columns (first case): {first_columns['alarms_columns']}")
        log(f"  alarm file index head: {first_columns['alarms_index_head']}")
        res.update(first_columns)
    if len(tdf):
        if "n_alarm_steps_first301" in tdf:
            n_no = int((tdf["n_alarm_steps_first301"] == 0).sum())
            log(f"  cases without any deviation in the first 301 steps (excluded by the diagnosis): {n_no}")
            res["n_cases_no_deviation_first301"] = n_no
        if "n_steps" in tdf:
            log(f"  steps per case: min={tdf['n_steps'].min()} median={tdf['n_steps'].median()} max={tdf['n_steps'].max()}")
        if "param" in tdf:
            log(f"  distinct true parameters in test cases: {tdf['param'].nunique()}")
            tdf["param"].value_counts().to_csv(os.path.join(out, "testcases_per_parameter.csv"))
        for k in ("folder_name_in_sweep", "value_in_sweep"):
            if k in tdf:
                vc = tdf[k].value_counts(dropna=False).to_dict()
                log(f"  overlap check {k}: {vc}")
                res[k] = {str(kk): int(vv) for kk, vv in vc.items()}
        if "n_modes_without_weights" in tdf and tdf["n_modes_without_weights"].notna().any():
            log(f"  cases that visit a mode without weights: {int((tdf['n_modes_without_weights'] > 0).sum())}")
        if "error" in tdf:
            log(f"  cases with read errors: {int(tdf['error'].notna().sum())}")
    if thr_no_dev and thr_dev:
        lo, hi = max(thr_no_dev), min(thr_dev)
        log(f"  deviation threshold bracket: max|r| without deviation = {lo:.4f}, min|r| with deviation = {hi:.4f}")
        res["threshold_bracket"] = [lo, hi]
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, default=v)
    ap.add_argument("--out", default="inventory")
    ap.add_argument("--skip-sweep", action="store_true", help="skip the (slow) scan of the raw sweep folders")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    summary = {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__}
    log(f"python {summary['python']}, pandas {summary['pandas']}, numpy {summary['numpy']}")
    for mod in ("pyarrow", "openpyxl", "igraph", "networkx", "pyvis", "scipy"):
        try:
            m = __import__(mod)
            summary[mod] = getattr(m, "__version__", "ok")
        except Exception as e:
            summary[mod] = f"MISSING ({type(e).__name__})"
        log(f"  module {mod}: {summary[mod]}")

    summary["paths"] = section_paths(a)
    sweep_df = None
    if not a.skip_sweep and os.path.isdir(a.sweep_root):
        try:
            sweep_df = section_sweep(a, a.out)
            summary["sweep_folders"] = int(len(sweep_df))
            summary["sweep_completed"] = int((sweep_df["has_parquet"] & sweep_df["has_txt"]).sum())
        except Exception:
            log(traceback.format_exc())
    for name, fn in (("intermediate", lambda: section_intermediate(a)),
                     ("modes", lambda: section_modes(a, a.out)),
                     ("testcases", lambda: section_testcases(a, a.out, sweep_df))):
        try:
            summary[name] = fn()
        except Exception:
            log(traceback.format_exc())

    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(os.path.join(a.out, "summary.txt"), "w") as f:
        f.write("\n".join(LOG) + "\n")
    log(f"\nDone. Please send the folder '{a.out}' (or at least summary.txt and summary.json).")


if __name__ == "__main__":
    main()
