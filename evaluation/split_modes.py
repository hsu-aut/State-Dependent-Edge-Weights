#!/usr/bin/env python3
"""
Held-out check: training data for the edge weights from one half of the fault runs only.

The learned edge weights (step0_weights_fixed.py) are computed from Data/mode_parquets_final_dask, i.e. from the
same simulated fault runs the test cases are built from (data_preparation/prepare_data_for_graph.py +
dask_process_modes.py; the per-run intermediate files no longer exist). The mode files have no run column, but
every row carries the parameter values of its run (prepare_data_for_graph.py assigns all nominal values and the
changed one, under the simulation names, float32). So each row is assigned to its run: the one parameter that
deviates from its nominal value, and its value -> index in the sweep (parameter_combination.json) -> run
"<param>_<index:05d>" (same naming as the raw run folders, validated in sim_reference.py).

Split (fixed, stratified per parameter): half A = even sweep index (training), half B = odd (test).
Writes the A rows of every mode file to --out (same file names), the run lists split_A.csv / split_B.csv, and,
with --diagnosable, the diagnosable test cases of half B (INCLUDE file for job_eval.sh).

  python split_modes.py --modes-dir <Data/mode_parquets_final_dask> --sweep sim_ref/parameter_combination.json \
      --out /beegfs/project/ma-kausalegraphen/tw_modes_A --diagnosable diagnosable_v4.csv [--dry-run]
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REL_TOL = 1e-5  # float32 storage: relative resolution ~6e-8; sweep values are ~0.2 % apart


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes-dir", required=True, type=Path)
    ap.add_argument("--sweep", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--diagnosable", default="", help="diagnosable_v4.csv -> writes diagnosable_v4_B.csv next to it")
    ap.add_argument("--batch", type=int, default=500_000)
    ap.add_argument("--dry-run", action="store_true", help="first batch of each file only, nothing written")
    a = ap.parse_args()

    with open(a.sweep, encoding="utf-8") as f:
        sets = json.load(f)
    baseline = sets[0]["baseline"]
    sweep = {s["name"]: np.asarray(s["values"], dtype=float) for s in sets}

    files = sorted(a.modes_dir.glob("mode_*.parquet"))
    print(f"{len(files)} mode files in {a.modes_dir}", flush=True)
    if not a.dry_run:
        a.out.mkdir(parents=True, exist_ok=True)
    runs_all = Counter()
    for fpath in files:
        pf = pq.ParquetFile(fpath)
        names = pf.schema_arrow.names
        pcols = [c for c in names if c in baseline and c in sweep]
        if not pcols:
            raise SystemExit(f"{fpath.name}: no parameter columns with simulation names found; first columns {names[:15]}")
        nom = np.array([float(baseline[c]) for c in pcols])
        writer = None
        n_rows = n_keep = n_none = n_multi = n_nomatch = 0
        runs_file = Counter()
        for bi, batch in enumerate(pf.iter_batches(batch_size=a.batch)):
            P = np.column_stack([batch.column(c).to_numpy(zero_copy_only=False).astype(float) for c in pcols])
            dev = np.abs(P / nom - 1.0) > REL_TOL
            k = dev.sum(1)
            j = dev.argmax(1)
            run_idx = np.full(len(P), -1)
            for jj in np.unique(j[k == 1]):
                rows = np.flatnonzero((k == 1) & (j == jj))
                sv = sweep[pcols[jj]]
                v = P[rows, jj]
                nearest = np.abs(sv[None, :] - v[:, None]).argmin(1)
                ok = np.abs(sv[nearest] / v - 1.0) <= REL_TOL
                run_idx[rows[ok]] = nearest[ok]
                n_nomatch += int((~ok).sum())
            n_rows += len(P)
            n_none += int((k == 0).sum())
            n_multi += int((k > 1).sum())
            ident = run_idx >= 0
            keys = [f"{pcols[jj]}_{ii:05d}" for jj, ii in zip(j[ident], run_idx[ident])]
            runs_file.update(keys)
            keep = ident & (run_idx % 2 == 0)
            n_keep += int(keep.sum())
            if not a.dry_run:
                tab = pa.Table.from_batches([batch]).filter(pa.array(keep))
                if writer is None:
                    writer = pq.ParquetWriter(a.out / fpath.name, tab.schema)
                writer.write_table(tab)
            if a.dry_run:
                break
        if writer is not None:
            writer.close()
        runs_all.update(runs_file)
        print(f"{fpath.name}: {n_rows} rows{' (first batch)' if a.dry_run else ''}, {len(pcols)} parameter columns, "
              f"runs {len(runs_file)}, rows kept (half A) {n_keep} ({n_keep / max(n_rows, 1):.1%}); "
              f"unassigned: no deviating parameter {n_none}, several {n_multi}, value not in sweep {n_nomatch}",
              flush=True)
        if a.dry_run and runs_file:
            print(f"   rows per run (min/median/max): {min(runs_file.values())}/"
                  f"{int(np.median(list(runs_file.values())))}/{max(runs_file.values())}; e.g. {list(runs_file)[:3]}")

    runs = pd.DataFrame({"case": sorted(runs_all)})
    runs["idx"] = runs.case.str.rsplit("_", n=1).str[1].astype(int)
    print(f"runs identified over all files: {len(runs)} (half A {int((runs.idx % 2 == 0).sum())}, "
          f"half B {int((runs.idx % 2 == 1).sum())})")
    if a.dry_run:
        return
    runs[runs.idx % 2 == 0][["case"]].to_csv(a.out / "split_A.csv", index=False)
    runs[runs.idx % 2 == 1][["case"]].to_csv(a.out / "split_B.csv", index=False)
    if a.diagnosable:
        d = pd.read_csv(a.diagnosable)
        d["idx"] = d.case.str.rsplit("_", n=1).str[1].astype(int)
        b = d[d.idx % 2 == 1].drop(columns="idx")
        outb = Path(a.diagnosable).with_name(Path(a.diagnosable).stem + "_B.csv")
        b.to_csv(outb, index=False)
        print(f"diagnosable cases of half B: {len(b)} of {len(d)} -> {outb}")


if __name__ == "__main__":
    main()
