#!/usr/bin/env python3
"""Convert Data/parameter_combination.npy (list of (param_name, sweep_values, baseline dict), pickled with numpy 2)
to JSON, so that sim_reference.py can read it inside the OpenModelica container (numpy 1.x).
  python npy_to_json.py <parameter_combination.npy> <out.json>"""
import json
import sys

import numpy as np


def plain(x):
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [plain(v) for v in x]
    if hasattr(x, "item"):
        return x.item()
    return x


sets = np.load(sys.argv[1], allow_pickle=True)
out = [{"name": str(n), "values": plain(v), "baseline": plain(dict(b))} for n, v, b in sets]
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(out, f)
print(f"{len(out)} sweep sets -> {sys.argv[2]}; first: {out[0]['name']} with {len(out[0]['values'])} values, "
      f"{len(out[0]['baseline'])} baseline parameters")
