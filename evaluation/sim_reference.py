#!/usr/bin/env python3
"""
Simulate a fault-free reference run with exactly the settings of simulation/simulate.py
(https://github.com/hsu-aut/Temporal-Weighting-for-Causal-Graphs), to replace
ModVA_online_stable_res_original.csv, whose actuator schedule differs from all fault runs (check 2026-11-23).

Two steps, both with the same model build:
  1. validation: re-simulate one existing fault run (same baseline, same changed parameter and value) so that the
     result can be compared with the stored parquet of that run (compare_runs.py) - this shows whether the
     OpenModelica version reproduces the original simulations,
  2. reference: all parameters at their baseline values, nothing changed.

Runs inside the OpenModelica container (needs only OMPython + numpy):
  apptainer exec openmodelica.sif python3 sim_reference.py --model <...V6.mo> --npy <parameter_combination.npy>
      --validate-run <raw run dir> --out <dir>
"""
import argparse
import os
import time

import numpy as np
from OMPython import ModelicaSystem

START_TIME, STOP_TIME, STEP_NUMBER, SOLVER, OUT_FORMAT = 0, 600, 12645, "ida", "csv"  # SIMULATION_CONFIG.py
MODEL_NAME = "ModVA_online_stable"
SIMFLAGS = "-abortSlowSimulation -noEventEmit"


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
    ap.add_argument("--model", required=True)
    ap.add_argument("--npy", required=True, help="Data/parameter_combination.npy used by simulate.py")
    ap.add_argument("--validate-run", required=True, help="raw fault-run folder (parquet + parameters.txt)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    os.chdir(a.out)  # build files go here

    if a.npy.endswith(".json"):  # converted with npy_to_json.py (the npy was pickled with numpy 2, the container has 1.x)
        import json
        with open(a.npy, encoding="utf-8") as f:
            sweep_sets = [(s["name"], s["values"], s["baseline"]) for s in json.load(f)]
    else:
        sweep_sets = np.load(a.npy, allow_pickle=True)
    baselines = [dict(b) for _, _, b in sweep_sets]
    same = all(b == baselines[0] for b in baselines)
    print(f"{len(sweep_sets)} sweep sets; identical baseline in all sets: {same}", flush=True)
    if not same:
        keys = sorted(set().union(*baselines))
        diff = [k for k in keys if len({repr(b.get(k)) for b in baselines}) > 1]
        print("  baseline keys that differ between sets:", diff[:20], flush=True)

    run = os.path.basename(os.path.normpath(a.validate_run))
    p_name, p_val = read_parameters_txt(os.path.join(a.validate_run, "parameters.txt"))
    idx = int(run.rsplit("_", 1)[1])
    k = [i for i, (n, _, _) in enumerate(sweep_sets) if n == p_name]
    assert len(k) == 1, f"parameter {p_name} found {len(k)} times in the sweep sets"
    _, sweep_values, baseline = sweep_sets[k[0]]
    print(f"validation run {run}: {p_name} = {p_val} (sweep value [{idx}] = {sweep_values[idx]})", flush=True)
    assert abs(float(sweep_values[idx]) - p_val) <= 1e-9 * max(1.0, abs(p_val)), "value in parameters.txt != sweep value"

    t0 = time.time()
    mod = ModelicaSystem(a.model, MODEL_NAME)
    mod.setSimulationOptions([f"startTime={START_TIME}", f"stopTime={STOP_TIME}",
                              f"stepSize={(STOP_TIME - START_TIME) / STEP_NUMBER}",
                              f"solver={SOLVER}", f"outputFormat={OUT_FORMAT}"])
    mod.buildModel()
    print(f"model built in {time.time() - t0:.0f} s", flush=True)

    # 1) validation: reproduce the stored fault run
    for p, v in baseline.items():
        mod.setParameters(f"{p}={v}")
    mod.setParameters(f"{p_name}={p_val}")
    csv = os.path.abspath(f"reproduce_{run}.csv")
    t0 = time.time()
    mod.simulate(resultfile=csv, simflags=SIMFLAGS)
    print(f"validation run simulated in {time.time() - t0:.0f} s -> {csv} exists: {os.path.isfile(csv)}", flush=True)

    # 2) reference: baseline only (reset the changed parameter to its baseline value)
    base_ref = dict(baselines[0])
    for p, v in base_ref.items():
        mod.setParameters(f"{p}={v}")
    if p_name not in base_ref:
        print(f"WARNING: {p_name} has no baseline value in the npy; it keeps the value {p_val} - check!", flush=True)
    csv = os.path.abspath("ModVA_online_stable_V6_nominal.csv")
    t0 = time.time()
    mod.simulate(resultfile=csv, simflags=SIMFLAGS)
    print(f"nominal run simulated in {time.time() - t0:.0f} s -> {csv} exists: {os.path.isfile(csv)}", flush=True)
    with open("nominal_parameters.txt", "w", encoding="utf-8") as f:
        for p, v in sorted(base_ref.items()):
            f.write(f"{p}={v}\n")


if __name__ == "__main__":
    main()
