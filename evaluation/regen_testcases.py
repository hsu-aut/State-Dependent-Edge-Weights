#!/usr/bin/env python3
"""
Regenerate the diagnosis test cases (data_for_aroyyo) with a new reference run, using
data_preparation/dataframe_adjustment.py of https://github.com/hsu-aut/Temporal-Weighting-for-Causal-Graphs unchanged
except for one point:
  * dataset_comparison.convert_time_of_df is called with a fixed start time instead of datetime.now(), so that
    reference and fault run share the same time anchor (datetime.now() is taken separately for both data frames and
    can differ by 1 s after rounding).
Everything else (level differencing, 1 s resampling, residual / max|reference|, threshold 0.05, XMV, modi_df,
copying parameters.txt) is the original code, unless one of the optional post-processing switches is given
(--mask-closed-valves, --threshold, --persist; see noise_vs_signal.py, 2026-11-23). The old reference (ModVA_online_stable_res_original.csv) follows a
different actuator schedule than all fault runs (check_reference.py, 2026-11-23); the new one is simulated with
sim_reference.py.

  python regen_testcases.py --repo ~/Temporal-Weighting-for-Causal-Graphs --input-dir /beegfs/project/ma-kausalegraphen \
      --output-dir <new data_for_aroyyo> --original-csv sim_ref/ModVA_online_stable_V6_nominal.csv [--cases-from cases_kl.csv]
"""
import argparse
import multiprocessing as mp
import os
import sys
from datetime import datetime
from pathlib import Path

FIXED_START = datetime(2000, 1, 1, 0, 0, 0)
# --mask-closed-valves: pressure sensor -> adjacent valve. While the valve is closed, the simulated pressure at
# V201/V202 is numerically ill-defined (not reproducible between runs, down to 16 kPa; inspect_pressure.py,
# 2026-11-23); residual and alarm of these sensors are set to 0 while the valve is closed (V203 for consistency).
MASK = {"pipe_B201_V201.port_b.p": "V201.opening", "pipe_B202_V202.port_b.p": "V202.opening",
        "pipe_B203_V203.port_b.p": "V203.opening"}


def persistent(dev, k):
    """Causal persistence filter on a deviation matrix (time x sensor, -1/0/1): an alarm at t is kept only if the
    same sign was present at t-k+1..t (alarm raised after k consecutive seconds above the threshold)."""
    import numpy as np
    if k <= 1:
        return dev
    out = np.zeros_like(dev)
    for s in (+1, -1):
        run = np.zeros(dev.shape[1], dtype=int)
        for t in range(dev.shape[0]):
            run = np.where(dev[t] == s, run + 1, 0)
            out[t][run >= k] = s
    return out


def postprocess(job):
    """Post-process one generated test case in place: (1) mask the pressure sensors at closed valves,
    (2) persistence filter. Returns (alarms removed by masking, alarms removed by persistence)."""
    folder, mask, k = job
    import pandas as pd
    xmv = pd.read_parquet(folder / "XMV.parquet")
    res_f, dev_f = folder / "ModVA_residual_adjusted.parquet", folder / "ModVA_deviation_adjusted.parquet"
    res, dev = pd.read_parquet(res_f), pd.read_parquet(dev_f)
    assert len(xmv) == len(res) == len(dev), (folder, len(xmv), len(res), len(dev))
    n_mask = 0
    if mask:
        for s, v in MASK.items():
            closed = (xmv[v].values <= 1e-6)
            n_mask += int(((dev[s].values != 0) & closed).sum())
            res.loc[closed, s] = 0.0
            dev.loc[closed, s] = 0
    m = dev.to_numpy()
    f = persistent(m, k)
    n_pers = int((m != 0).sum() - (f != 0).sum())
    dev = pd.DataFrame(f.astype(m.dtype), columns=dev.columns)
    res.to_parquet(res_f, index=False)
    dev.to_parquet(dev_f, index=False)
    return n_mask, n_pers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--input-dir", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--original-csv", required=True, type=Path)
    ap.add_argument("--cases-from", default="", help="only the cases listed in this cases_*.csv (quick check)")
    ap.add_argument("--mask-closed-valves", action="store_true",
                    help="set residual/alarm of the pressure sensors at V201-V203 to 0 while the valve is closed")
    ap.add_argument("--threshold", type=float, default=0.05, help="alarm threshold on |residual| (original 0.05)")
    ap.add_argument("--persist", type=int, default=1,
                    help="alarm only after k consecutive seconds above the threshold (original 1 = no filter)")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "4")))
    a = ap.parse_args()

    sys.path.insert(0, str(a.repo / "data_preparation"))
    import dataset_comparison as dc
    import dataframe_adjustment as da

    orig = dc.convert_time_of_df
    dc.convert_time_of_df = lambda df, col, start_time=None: orig(df, col, FIXED_START)
    assert da.dc is dc
    if a.threshold != 0.05:  # dataframe_adjustment calls compare_dataframes(..., threshold=0.05) explicitly
        orig_cmp = dc.compare_dataframes
        dc.compare_dataframes = lambda o, f, threshold=0.05: orig_cmp(o, f, threshold=a.threshold)

    paths = sorted(p for p in a.input_dir.iterdir() if p.is_dir() and len(list(p.glob("*.parquet"))) == 1)
    if a.cases_from:
        import pandas as pd
        keep = set(pd.read_csv(a.cases_from)["case"].astype(str))
        paths = [p for p in paths if p.name in keep]
    a.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"{len(paths)} fault runs, reference {a.original_csv}, output {a.output_dir}, workers {a.workers}, "
          f"threshold {a.threshold}, persistence {a.persist} s, mask closed valves {a.mask_closed_valves}", flush=True)

    jobs = [(p, a.output_dir, a.original_csv) for p in paths]
    if a.workers > 1:  # fork, so that the workers inherit the patched convert_time_of_df
        with mp.get_context("fork").Pool(a.workers) as pool:
            res = pool.map(da.process_test_case, jobs, chunksize=4)
    else:
        res = [da.process_test_case(j) for j in jobs]
    print(f"processed {sum(r[0] for r in res)}, skipped {sum(r[1] for r in res)}", flush=True)
    if a.mask_closed_valves or a.persist > 1:
        outs = [(a.output_dir / p.name, a.mask_closed_valves, a.persist) for p in paths
                if (a.output_dir / p.name / "XMV.parquet").exists()]
        if a.workers > 1:
            with mp.get_context("fork").Pool(a.workers) as pool:
                removed = pool.map(postprocess, outs, chunksize=8)
        else:
            removed = [postprocess(o) for o in outs]
        rm, rp = sorted(r[0] for r in removed), sorted(r[1] for r in removed)
        print(f"post-processing of {len(outs)} cases: masking removed {sum(rm)} alarms (median per case "
              f"{rm[len(rm) // 2] if rm else 0}), persistence removed {sum(rp)} (median {rp[len(rp) // 2] if rp else 0})",
              flush=True)

if __name__ == "__main__":
    main()
