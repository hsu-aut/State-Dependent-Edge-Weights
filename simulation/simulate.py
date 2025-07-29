import os
import numpy as np
import pandas as pd
import time
from OMPython import OMCSessionZMQ, ModelicaSystem
from SIMULATION_CONFIG import (
    ROOT_DIR,
    PROJECT_PATH,
    MODELICAFILENAME,
    MODELICAFILELOCATION,
    MODELICAMODELNAME,
)
from SIMULATION_CONFIG import (
    START_TIME,
    STOP_TIME,
    STEP_NUMBER,
    SOLVER,
    OUT_FORMAT,
)


sweep_sets = np.load(
    os.path.join(ROOT_DIR, "Data", "parameter_combination.npy"), allow_pickle=True
)

task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
param_name, sweep_values, baseline = sweep_sets[task_id]

omc = OMCSessionZMQ()
mod = ModelicaSystem(
    os.path.join(MODELICAFILELOCATION, MODELICAFILENAME), MODELICAMODELNAME
)
sim_opts = [
    f"startTime={START_TIME}",
    f"stopTime={STOP_TIME}",
    f"stepSize={(STOP_TIME-START_TIME)/STEP_NUMBER}",
    f"solver={SOLVER}",
    f"outputFormat={OUT_FORMAT}",
]
mod.setSimulationOptions(sim_opts)
mod.buildModel()

try:
    for idx, val in enumerate(sweep_values):
        run_name = f"{param_name}_{idx:05d}"
        out_dir = os.path.join(PROJECT_PATH, run_name)
        os.makedirs(out_dir, exist_ok=True)

        for p, v in baseline.items():
            mod.setParameters(f"{p}={v}")
        mod.setParameters(f"{param_name}={val}")

        abs_csv = os.path.join(out_dir, f"{run_name}.csv")
        start = time.time()
        mod.simulate(resultfile=abs_csv, simflags="-abortSlowSimulation -noEventEmit")
        print(f"Simulation {run_name} completed in {time.time() - start:.2f} seconds.")

        if not os.path.isfile(abs_csv):
            raise FileNotFoundError(f"Simulation result file {abs_csv} not found.")
        
        df = pd.read_csv(abs_csv)
        parquet_path = abs_csv.replace(".csv", ".parquet")
        df.to_parquet(parquet_path, compression="gzip", index=False)
        os.remove(abs_csv)
        print(f"✓ {run_name} gespeichert in {parquet_path}")

        with open(os.path.join(out_dir, "parameters.txt"), "w") as f:
            f.write(f"Geändert: {param_name}\nWert: {val}\n")

except Exception as e:
    print(f"Fehler in Lauf {run_name}: {e}")
