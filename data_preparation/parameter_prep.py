import numpy as np
import PARAMETER_CONFIG
import parameter_values 
from typing import Dict, List, Tuple
import os

def generate_sweep_sets(nominals: dict, parameters_range: dict):
    baseline = nominals.copy()

    sweep_sets: List[Tuple[str, np.array, Dict[str, float]]] = []
    for param, values in parameters_range.items():
        sweep_values = np.array(values, dtype=np.float32)
        sweep_sets.append((param, sweep_values, baseline.copy()))

    return sweep_sets



if __name__ == "__main__":
    parameters = parameter_values.parameters_gaussian
    sweep_sets = generate_sweep_sets(PARAMETER_CONFIG.NOMINALS, parameters)
    sweep_array = np.empty(len(sweep_sets), dtype=object)
    sweep_array[:] = sweep_sets
    output_dir = r"C:\Users\Moritz\Desktop\Master\Code\Data"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "parameter_combination.npy")
    np.save(output_path, sweep_array, allow_pickle=True)

