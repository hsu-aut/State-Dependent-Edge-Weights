#!/usr/bin/env python3
"""
Step 2 - per-case re-run of the diagnosis (graph_analyse/inst_algo.py of
https://github.com/hsu-aut/Temporal-Weighting-for-Causal-Graphs).

The per-test-case logic is copied unchanged from inst_algo.process_testcase.
Differences to inst_algo.py:
  * one CSV row per test case is written instead of only printing the means,
  * the edge-weight column can be selected (--config),
  * multiprocessing on one node instead of MPI, paths as command-line options,
  * createNameList is copied inline, so the mysql/opcua imports are not needed.

Configs:
  kl        weight column MI_mit_Var_Xi            (as published, expected MR 36.21 / SAE 0.2812)
  beta      weight column Beta_Absolut             (regression coefficients, expected 38.03 / 0.3267)
  heuristic no state-specific weights, rule weights of [Ra24] (expected 39.76 / 0.3949)
  kl_cond   weight column MI_mit_Var_Xi_given_Z    (conditional variant, not published)
  heuristic_uniform  heuristic with the same weight on every parameter edge (rules 21-35, see --param-prior)

Usage:
  python step2_eval_cases.py --repo ~/Temporal-Weighting-for-Causal-Graphs --config kl --workers 8 --limit 8 --out smoke
"""
import argparse
import os
import sys
import time
import traceback
import multiprocessing as mp

import numpy as np
import pandas as pd
from openpyxl import load_workbook

CODE = "/beegfs/project/ma-kausalegraphen/m778332/masterarbeit/Code"  # moved from /beegfs/home/m/m778332 (2026-11-20)
WEIGHT_COLUMN = {"kl": "MI_mit_Var_Xi", "beta": "Beta_Absolut", "kl_cond": "MI_mit_Var_Xi_given_Z", "heuristic": None,
                 "heuristic_uniform": None}
# Parameter rules of Arroyo_DCDG_PLUT.generate_graphfromAML (rulenumber 21-35). Their strength is the
# "probability index" of the parameter type: 0.99 for Diameter/Length/Roughness/PDropNom, 0.3 for
# HDiff/MFNominal/Rotational_Speed/Area. This prior is not part of [Ra24] (named there as future work).
PARAM_RULES = set(range(21, 36))
TESTCASE_FILENAMES = {
    "alarms": "ModVA_deviation_adjusted.parquet",
    "xmv": "XMV.parquet",
    "residuals": "ModVA_residual_adjusted.parquet",
    "parameters": "parameters.txt",
    "modi_df": "modi_df.parquet",
}

# set in main() before the worker pool is forked
G = {}


def createNameList(inputList, indices):
    """Copied from graph_analyse/MySQL_OPCUA_Datahistorian.py (avoids mysql/opcua imports)."""
    outList = [''] * len(inputList)
    for counter, name in enumerate(inputList):
        for i in indices:
            outList[counter] += name[i]
    return outList


def load_dynamic_weights(modes_base_path):
    """Copied from inst_algo.load_dynamic_weights."""
    all_weights = {}
    if not os.path.isdir(modes_base_path):
        print(f"WARNUNG: Verzeichnis für dynamische Gewichte nicht gefunden: {modes_base_path}")
        return all_weights
    for mode_folder in os.listdir(modes_base_path):
        mode_path = os.path.join(modes_base_path, mode_folder)
        if os.path.isdir(mode_path):
            try:
                csv_file_name = next((f for f in os.listdir(mode_path) if f.endswith('.csv')), None)
                if csv_file_name:
                    df = pd.read_csv(os.path.join(mode_path, csv_file_name), delimiter=';', decimal=',')
                    df.dropna(subset=['Original_Edge_ID'], inplace=True)
                    if not df.empty:
                        df['Original_Edge_ID'] = df['Original_Edge_ID'].astype(int)
                    df.set_index('Original_Edge_ID', inplace=True)
                    all_weights[mode_folder] = df
                else:
                    print(f"WARNUNG: Keine CSV-Datei im Modus-Ordner gefunden: {mode_path}")
            except Exception as e:
                print(f"FEHLER beim Lesen und Bereinigen des Modus {mode_folder}: {e}")
    print(f"{len(all_weights)} Gewichts-Modi erfolgreich geladen.")
    return all_weights


def aggregate_ids(df, how):
    """One row per Original_Edge_ID. update_edge_weights_from_mode sets the weight row by row, so with
    duplicates the last row in the file wins (original behaviour, how='last')."""
    w = df.copy()
    w["_order"] = np.arange(len(w))
    slice_of = lambda s: str(s).rsplit("_", 1)[-1]
    w["_type"] = [slice_of(p) + "->" + slice_of(c) for p, c in zip(w["Elternknoten"], w["Kindknoten"])]
    v = pd.to_numeric(w["MI_mit_Var_Xi"], errors="coerce")
    w["MI_mit_Var_Xi"] = v
    if how == "max":
        w["_key"] = v.fillna(-np.inf)
    else:
        pref = "0->0" if how == "intra" else "0->1"
        w["_key"] = (w["_type"] == pref).astype(int) * 2 + w["_order"] / len(w)  # preferred type first, then file order
    w = w.sort_values("_key").groupby(level=0).tail(1).sort_values("_order")
    return w.drop(columns=["_order", "_type", "_key"])


def map_weights(df, how):
    """Map the learned weight (column MI_mit_Var_Xi, >= 0) to [0, 1] before it enters the path search.
    The path search prunes edges with w <= 0.01 and uses the cost -log(w), which is negative for w > 1
    (KL > 1, |beta| > 1); the rule weights of the heuristic are all in (0, 1].
      exp: w' = 1 - exp(-w)   (monotone; w' <= 0.01 <=> w <= 0.01005, so pruning is practically unchanged)
      max: w' = w / max(w) over the finite weights of this operating state (inf -> 1)"""
    w = df.copy()
    v = pd.to_numeric(w["MI_mit_Var_Xi"], errors="coerce").astype(float)
    if how == "exp":
        m = 1.0 - np.exp(-v.clip(lower=0))
    elif how == "max":
        fin = v[np.isfinite(v)]
        vmax = fin.max() if len(fin) and fin.max() > 0 else 1.0
        m = (v / vmax).clip(lower=0, upper=1)
    else:
        raise ValueError(how)
    m[np.isinf(v) & (v > 0)] = 1.0
    w["MI_mit_Var_Xi"] = m  # NaN stays NaN, as in the original
    return w


def apply_param_prior(dcdg, value):
    """Set the rule weight of every parameter edge (rules 21-35) to the same value (uniform prior).
    Returns the number of edges changed. Learned state-specific weights, if used, are applied later and
    overwrite the edges they cover, exactly as before."""
    n = 0
    for e in dcdg.g.es:
        try:
            rn = e["rulenumber"]
        except KeyError:
            return 0
        if rn is not None and int(rn) in PARAM_RULES:
            e["weight"] = value
            n += 1
    return n


PRUNE_OLD = "if edge_weight <= 0.01 or edge_lambda is None"
PRUNE_NEW = ("if edge_weight <= 0 or (edge_weight <= 0.01 and edge_id in self._prune_eids) "
             "or edge_lambda is None")


def patch_pruning(DCDG_Class):
    """--prune valves: modified_dijkstra skips an edge with w <= 0.01 only if its weight is set by the valve
    kernel (closed valve, kernel minimum 0.01); learned weights in (0, 0.01] are kept with cost -log(w).
    Edges with w <= 0 are still skipped (cost undefined). The original method is otherwise unchanged; it is
    re-compiled from its source with only this condition replaced. For the rule-based configs the result is
    identical, because all non-valve rule weights are >= 0.1."""
    import inspect, textwrap, Arroyo_DCDG_PLUT as mod
    if getattr(DCDG_Class, "_prune_patched", False):
        return
    src = textwrap.dedent(inspect.getsource(DCDG_Class.modified_dijkstra))
    assert src.count(PRUNE_OLD) == 1, "pruning condition in modified_dijkstra not found - code changed?"
    ns = {}
    exec(compile(src.replace(PRUNE_OLD, PRUNE_NEW), mod.__file__, "exec"), mod.__dict__, ns)
    DCDG_Class.modified_dijkstra = ns["modified_dijkstra"]
    DCDG_Class._prune_patched = True


def valve_edge_ids(dcdg):
    """Edge IDs whose weight is overwritten by the valve kernel in every step (Valve.apply_weights)."""
    return {e for v in dcdg.valves for ids in v.relationDict.values() for e in ids}


def fallback_ids(df, tau):
    """--fallback rule: edge IDs of this operating state whose learned weight is <= tau or NaN."""
    v = pd.to_numeric(df["MI_mit_Var_Xi"], errors="coerce")
    return np.unique(df.index[(v <= tau) | v.isna()].astype(int))


def read_gt_code(path_parameters, reverse_mapping):
    """Ground-truth parameter code from parameters.txt (same parsing as below), for --debug-dir."""
    if not os.path.exists(path_parameters):
        return None
    with open(path_parameters, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith("Geändert:"):
                return reverse_mapping.get(line.split(":", 1)[1].strip())
    return None


def debug_step(dcdg, tc, mode, tracked):
    """--debug-dir: decomposition of the causal value of the tracked parameters for one diagnosis step.
    Mirrors generate_parameterinfluence_matrix / evaluate_distance_matrix of Arroyo_DCDG_PLUT (read-only)."""
    sens = dcdg.possible_alarm_list
    S = dcdg.current_statevariable_influence_matrix
    ratio = []
    for j in range(S.shape[1]):
        sc = max(float(np.sum(S[:, j])), 0.1)
        ratio.append(float(np.sum(S[j, :])) / sc)
    plist = dcdg.current_parameter_list
    tags = [v["Tag"] for v in plist]
    out = {"tc": tc, "mode": mode, "sensors": [v["Tag"] for v in sens], "AS": [v["AS"] for v in sens],
           "dev": [float(v["deviation"]) if v["deviation"] is not None else None for v in sens],
           "ratio": ratio, "params": {}}
    P = dcdg.current_parameter_influence_matrix
    for t in tracked:
        if t not in tags:
            continue
        i = tags.index(t)
        dists, paths = [], []
        for v in sens:
            if v["AS"] is None:
                dists.append(None); paths.append(None); continue
            d, p = dcdg.modified_dijkstra(plist[i].index, v.index, dijkstra_type="parameter")
            dists.append(float(d))
            paths.append([dcdg.g.vs[k]["Tag"] for k in p if k != ""])
        plen = [len(p) if p else 1 for p in paths if p is not None]
        out["params"][t] = {
            "dist": dists, "path": paths,
            "path_w": [[float(dcdg.g.es[dcdg.g.get_eid(a, b)]["weight"]) for a, b in
                        zip([dcdg.g.vs["Tag"].index(x) for x in p[:-1]], [dcdg.g.vs["Tag"].index(x) for x in p[1:]])]
                       if p else [] for p in paths],
            "n_neutral": int(dcdg.current_parameter_neutral_influencelist[i]),
            "range_factor": float(np.power(1.1, np.mean(plen))) if plen else None,
            "param_infl": [float(x) for x in P[i, :]],
            "combined": [float(P[i, j] * (ratio[j] + 1)) for j in range(P.shape[1])],
        }
    return out


def process_testcase(case_path):
    """Logic of inst_algo.process_testcase, plus bookkeeping for the per-case CSV."""
    from Arroyo_DCDG_PLUT import DCDG_Class  # imported in the worker

    aml_file = G["aml"]
    dList = G["dList"]
    dNumbers = G["dNumbers"]
    reverse_mapping = G["reverse_mapping"]
    abort_time = G["abort_time"]
    testcase_files = TESTCASE_FILENAMES
    all_mode_weights = G["all_mode_weights"]
    use_mode_weights = G["use_mode_weights"]

    rec = {"case": os.path.basename(case_path), "status": "ok", "error": None}
    try:
        t0 = time.time()
        dcdg = DCDG_Class()
        dcdg.generate_graphfromAML(aml_file)
        if G["param_prior"] == "uniform":
            rec["n_prior_edges"] = apply_param_prior(dcdg, G["prior_value"])
        if G["prune"] == "valves":
            patch_pruning(DCDG_Class)
            dcdg._prune_eids = valve_edge_ids(dcdg)
            rec["n_valve_edges"] = len(dcdg._prune_eids)
        rule_weights = list(dcdg.g.es["weight"])  # rule weights (after the optional uniform prior)
        fb_cache, n_fb_set = {}, 0
        dbg = None

        path_alarms = os.path.join(case_path, testcase_files['alarms'])
        path_xmv = os.path.join(case_path, testcase_files['xmv'])
        path_residuals = os.path.join(case_path, testcase_files['residuals'])
        path_parameters = os.path.join(case_path, testcase_files['parameters'])
        path_modi_df = os.path.join(case_path, testcase_files['modi_df'])

        df_alarms = pd.read_parquet(path_alarms)
        df_xmv = pd.read_parquet(path_xmv)
        df_residuals = pd.read_parquet(path_residuals)
        df_modi = pd.read_parquet(path_modi_df)

        xmv_dict, alarm_dict, deviation_dict = {}, {}, {}
        accumulated_combined_influence_matrix = None
        parameter_names_total = None

        n_steps_loop = n_diag_steps = n_missing_mode_steps = 0
        modes_seen = set()
        last_tc = -1

        for tc in range(len(df_alarms)):
            last_tc = tc
            n_steps_loop += 1
            current_mode_values = df_modi.iloc[tc].astype(int).tolist()
            mode_folder_name = f"mode_{'_'.join(map(str, current_mode_values))}"
            modes_seen.add(mode_folder_name)

            if use_mode_weights:
                if mode_folder_name in all_mode_weights:
                    dcdg.update_edge_weights_from_mode(all_mode_weights[mode_folder_name])
                    if G["fallback"] == "rule":
                        if mode_folder_name not in fb_cache:
                            ids = fallback_ids(all_mode_weights[mode_folder_name], G["fallback_tau"])
                            fb_cache[mode_folder_name] = [i for i in ids if 0 <= i < len(rule_weights)]
                        for i in fb_cache[mode_folder_name]:
                            dcdg.g.es[i]["weight"] = rule_weights[i]
                        n_fb_set += len(fb_cache[mode_folder_name])
                else:
                    n_missing_mode_steps += 1  # inst_algo prints a warning and keeps the previous weights

            for i in range(8):  # number_of_actuators
                val = df_xmv.iloc[tc, dNumbers[i] - 1]
                xmv_dict[dList[10 + i].replace("_State", "")] = (0 if val is None else val) / 100
            dcdg.update_valves(xmv_dict)

            for j in range(10):  # number_of_sensors
                if "AIR" not in dList[j]:
                    alarm_dict[dList[j].replace("V", "YIC").replace("_", "_Measurement_")] = df_alarms.iloc[tc, j]
            dcdg.add_sensorlabels(alarm_dict)
            dcdg.set_alarmstates(alarm_dict)

            for k in range(10):  # number_of_sensors
                if "AIR" not in dList[k]:
                    deviation_dict[dList[k].replace("V", "YIC").replace("_", "_Measurement_")] = df_residuals.iloc[tc, k]
            dcdg.set_deviations(deviation_dict)

            if not any(alarm_dict.values()):
                continue

            (combined_influence_matrix, _, parameter_names_total, _, _, _,) = dcdg.evaluate_distance_matrix(0.5, update_distance=True)
            n_diag_steps += 1
            if G["debug_dir"]:
                if dbg is None:
                    dbg = []
                    tracked = list(G["debug_params"])
                    gtc = read_gt_code(path_parameters, reverse_mapping)
                    if gtc and gtc not in tracked:
                        tracked.append(gtc)
                dbg.append(debug_step(dcdg, tc, mode_folder_name, tracked))

            if accumulated_combined_influence_matrix is None:
                accumulated_combined_influence_matrix = combined_influence_matrix.copy()
            else:
                accumulated_combined_influence_matrix += combined_influence_matrix

            if tc >= abort_time:
                break

        rec.update({"n_steps_total": len(df_alarms), "n_steps_loop": n_steps_loop, "last_step": last_tc,
                    "n_diag_steps": n_diag_steps, "n_missing_mode_steps": n_missing_mode_steps,
                    "n_modes_seen": len(modes_seen),
                    "n_fallback_per_step": n_fb_set / max(n_steps_loop, 1)})

        # ground truth (as in inst_algo)
        current_changed_params, changed_value = [], None
        if os.path.exists(path_parameters):
            with open(path_parameters, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith("Geändert:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            current_changed_params.append(parts[1].strip())
                    elif line.strip().startswith("Wert:"):
                        try:
                            changed_value = float(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
        rec["gt_param"] = current_changed_params[0] if current_changed_params else None
        rec["gt_value"] = changed_value

        if accumulated_combined_influence_matrix is None:
            rec["status"] = "no_deviation"  # inst_algo returns None -> not counted
            rec["proc_time_s"] = time.time() - t0
            return rec

        row_sums = np.sum(accumulated_combined_influence_matrix, axis=1)
        sorted_indices = np.argsort(np.abs(row_sums))[::-1]
        rec["n_candidates"] = len(parameter_names_total)

        rank, scaled_error = np.nan, np.nan
        if current_changed_params:
            ground_truth_param_name = current_changed_params[0]
            code_param_gt = reverse_mapping.get(ground_truth_param_name)
            rec["gt_code"] = code_param_gt
            if code_param_gt and code_param_gt in parameter_names_total:
                param_index_gt = parameter_names_total.index(code_param_gt)
                rank = list(sorted_indices).index(param_index_gt) + 1

                influence_gt = row_sums[param_index_gt]
                influence_top1 = row_sums[sorted_indices[0]]
                influence_range = np.max(row_sums) - np.min(row_sums)
                if influence_range > 1e-9:
                    scaled_error = abs(influence_top1 - influence_gt) / influence_range

                a = np.abs(row_sums)
                a_gt = a[param_index_gt]
                tol = 1e-12 * max(1.0, float(a.max()))
                rec.update({
                    "c_gt": float(influence_gt), "c_top1": float(influence_top1),
                    "top1_code": parameter_names_total[sorted_indices[0]],
                    "rank_best_case_ties": int(np.sum(a > a_gt + tol)) + 1,
                    "rank_worst_case_ties": int(np.sum(a >= a_gt - tol)),
                    "n_tied_with_gt": int(np.sum(np.abs(a - a_gt) <= tol)),
                    "n_zero_causal_value": int(np.sum(a <= tol)),
                    # SAE on |causal value|, consistent with the ranking (the original SAE above uses the signed
                    # row sums, so a true cause with the opposite sign of the top-1 gets ~1 even at rank 2)
                    "sae_abs": float((a.max() - a_gt) / (a.max() - a.min())) if a.max() - a.min() > 1e-12 else np.nan,
                })
            else:
                rec["status"] = "gt_not_in_candidates"
        else:
            rec["status"] = "no_parameters_txt"

        rec["rank"] = rank
        rec["sae"] = scaled_error
        if G["debug_dir"] and dbg is not None:
            import json
            try:
                os.makedirs(G["debug_dir"], exist_ok=True)
                payload = json.dumps({"case": rec["case"], "gt_code": rec.get("gt_code"), "rank": rank,
                                      "param_names": parameter_names_total,
                                      "sensors": [v["Tag"] for v in dcdg.possible_alarm_list],
                                      "accumulated": accumulated_combined_influence_matrix.tolist(),
                                      "steps": dbg},
                                     default=lambda o: o.item() if hasattr(o, "item") else str(o))
                with open(os.path.join(G["debug_dir"], f"{rec['case']}.json"), "w") as fh:
                    fh.write(payload)
            except Exception as ex:  # the debug output must never invalidate the case result
                rec["debug_error"] = repr(ex)
        rec["proc_time_s"] = time.time() - t0
        return rec

    except Exception as e:
        rec["status"] = "error"
        rec["error"] = f"{type(e).__name__}: {e} | {traceback.format_exc(limit=3)}"
        return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="clone of Temporal-Weighting-for-Causal-Graphs")
    ap.add_argument("--config", required=True, choices=sorted(WEIGHT_COLUMN))
    ap.add_argument("--aml", default=f"{CODE}/Data/models/ModVA_Mixer_incl_SensorNamingConvention_reduced_V2.aml")
    ap.add_argument("--designations", default=f"{CODE}/Data/models/ModVA_Designations.xlsx")
    ap.add_argument("--weights-dir", default=f"{CODE}/Data/mode_parquets_final_dask/weights")
    ap.add_argument("--testcases", default=f"{CODE}/Data/data_for_aroyyo")
    ap.add_argument("--abort-time", type=int, default=300)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "4")))
    ap.add_argument("--limit", type=int, default=0, help="only the first N test cases (smoke test)")
    ap.add_argument("--sample", type=int, default=0,
                    help="random sample of N test cases, stratified over the true parameters (same cases for every config)")
    ap.add_argument("--seed", type=int, default=20261121)
    ap.add_argument("--debug-dir", default="",
                    help="write a per-case JSON with the per-step decomposition of the causal value (use with --limit)")
    ap.add_argument("--debug-params", default="Pipe_FI271_B204_Diameter,Pipe_B204_P202_Diameter",
                    help="comma-separated parameter codes to decompose (the true cause is added automatically)")
    ap.add_argument("--exclude", default="",
                    help="cases_*.csv of an earlier run; its cases are removed (e.g. a confirmation run on new cases)")
    ap.add_argument("--include", default="",
                    help="CSV with a column 'case'; only these cases are used, applied before --sample "
                         "(e.g. diagnosable_v4.csv from diag_by_type.py)")
    ap.add_argument("--id-agg", choices=["last", "max", "intra", "inter"], default="last",
                    help="how several TV-DBN edges with the same Original_Edge_ID are combined: last = original "
                         "behaviour (last row in the file wins), max = larger weight, intra = prefer the edge within "
                         "time slice 0 (0->0), inter = prefer the edge from slice 0 to slice 1 (0->1)")
    ap.add_argument("--weight-map", choices=["none", "exp", "max"], default="none",
                    help="map learned weights to [0, 1] before the path search (applied after --id-agg): "
                         "none = original, exp = 1 - exp(-w), max = w / max(w) per operating state")
    ap.add_argument("--param-prior", choices=["code", "uniform"], default="code",
                    help="rule weight of the parameter edges: code = as in Arroyo_DCDG_PLUT (0.99 / 0.3 by parameter "
                         "type), uniform = --prior-value for all (implied by --config heuristic_uniform)")
    ap.add_argument("--prior-value", type=float, default=0.99)
    ap.add_argument("--prune", choices=["all", "valves"], default="all",
                    help="all = original path search (every edge with w <= 0.01 is skipped); valves = only edges "
                         "set by the valve kernel are skipped at w <= 0.01 (closed valve), learned weights are kept")
    ap.add_argument("--fallback", choices=["none", "rule"], default="none",
                    help="rule = where the learned weight of an operating state is <= --fallback-tau (or NaN), "
                         "use the rule weight of the edge instead")
    ap.add_argument("--fallback-tau", type=float, default=0.01,
                    help="threshold for --fallback rule (default 0.01 = the pruning threshold, not tuned)")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    graph_dir = os.path.join(os.path.abspath(os.path.expanduser(a.repo)), "graph_analyse")
    if not os.path.isfile(os.path.join(graph_dir, "Arroyo_DCDG_PLUT.py")):
        sys.exit(f"Arroyo_DCDG_PLUT.py not found in {graph_dir}")
    sys.path.insert(0, graph_dir)
    from MAPPING_DICT import matching  # noqa: E402

    os.makedirs(a.out, exist_ok=True)
    t_start = time.time()

    # global data (as in inst_algo __main__)
    wb = load_workbook(filename=a.designations)
    ws = wb.active
    d = {}
    for row in list(ws.rows)[1:]:
        if str(row[1].value) != "None" and str(row[2].value) != "None":
            d[row[0].value] = [str(c.value) for c in row[1:]]
    dList = createNameList(list(d.values()), [0, 1, 4])

    col = WEIGHT_COLUMN[a.config]
    all_mode_weights = {}
    if col is not None:
        all_mode_weights = load_dynamic_weights(a.weights_dir)
        if not all_mode_weights:
            sys.exit("No weights loaded - check --weights-dir")
        missing = [m for m, df in all_mode_weights.items() if col not in df.columns]
        if missing:
            sys.exit(f"Column {col} missing in {len(missing)} weight files, e.g. {missing[:3]}")
        if col != "MI_mit_Var_Xi":  # update_edge_weights_from_mode reads MI_mit_Var_Xi
            for df in all_mode_weights.values():
                df["MI_mit_Var_Xi"] = pd.to_numeric(df[col], errors="coerce")
        if a.id_agg != "last":
            all_mode_weights = {m: aggregate_ids(df, a.id_agg) for m, df in all_mode_weights.items()}
        n_multi = sum(int(df.index.duplicated().sum()) for df in all_mode_weights.values())
        print(f"id_agg={a.id_agg}: remaining duplicate edge IDs over all modes: {n_multi}", flush=True)
        if a.weight_map != "none":
            all_mode_weights = {m: map_weights(df, a.weight_map) for m, df in all_mode_weights.items()}
        allv = pd.concat([pd.to_numeric(df["MI_mit_Var_Xi"], errors="coerce") for df in all_mode_weights.values()])
        print(f"weight_map={a.weight_map}: weights min={allv.min():.4g} median={allv.median():.4g} "
              f"max={allv.max():.4g} >1: {int((allv > 1).sum())} <=0.01: {int((allv <= 0.01).sum())} "
              f"NaN: {int(allv.isna().sum())}", flush=True)

    G.update({
        "aml": a.aml, "dList": dList, "dNumbers": list(range(1, 9)),
        "reverse_mapping": {v: k for k, v in matching.items() if v != "none"},
        "abort_time": a.abort_time, "all_mode_weights": all_mode_weights,
        "use_mode_weights": col is not None,
        "param_prior": "uniform" if (a.param_prior == "uniform" or a.config == "heuristic_uniform") else "code",
        "prior_value": a.prior_value,
        "prune": a.prune, "fallback": a.fallback, "fallback_tau": a.fallback_tau,
        "debug_dir": os.path.join(a.debug_dir, a.config) if a.debug_dir else "", "debug_params": [p for p in a.debug_params.split(",") if p],
    })
    print(f"prune={a.prune} fallback={a.fallback} fallback_tau={a.fallback_tau}", flush=True)

    cases = sorted(os.path.join(a.testcases, f) for f in os.listdir(a.testcases)
                   if os.path.isdir(os.path.join(a.testcases, f)))
    if a.include:  # before sampling, so that the sample is drawn from the listed cases only
        keep = set(pd.read_csv(a.include)["case"].astype(str))
        n0 = len(cases)
        cases = [c for c in cases if os.path.basename(c) in keep]
        print(f"include={a.include}: {len(cases)} of {n0} cases kept", flush=True)
    if a.sample:
        # stratified: round-robin over the true parameters (folder name minus run index), fixed seed
        rng = np.random.default_rng(a.seed)
        groups = {}
        for c in cases:
            groups.setdefault(os.path.basename(c).rsplit("_", 1)[0], []).append(c)
        for g in groups.values():
            rng.shuffle(g)
        keys = sorted(groups)
        picked, i = [], 0
        while len(picked) < min(a.sample, len(cases)):
            g = groups[keys[i % len(keys)]]
            if g:
                picked.append(g.pop())
            i += 1
        cases = sorted(picked)
    if a.exclude:
        used = set(pd.read_csv(a.exclude)["case"].astype(str))
        n0 = len(cases)
        cases = [c for c in cases if os.path.basename(c) not in used]
        print(f"exclude={a.exclude}: {n0 - len(cases)} cases removed, {len(cases)} remain", flush=True)
    if a.limit:
        cases = cases[: a.limit]
    print(f"config={a.config} column={col} cases={len(cases)} workers={a.workers} aml={a.aml} weights={a.weights_dir}", flush=True)
    print(f"dList={dList}", flush=True)

    out_csv = os.path.join(a.out, f"cases_{a.config}.csv")
    results = []
    ctx = mp.get_context("fork")
    with ctx.Pool(processes=a.workers) as pool:
        for i, rec in enumerate(pool.imap_unordered(process_testcase, cases, chunksize=1)):
            rec["config"] = a.config
            results.append(rec)
            if (i + 1) % 25 == 0 or i + 1 == len(cases):
                pd.DataFrame(results).to_csv(out_csv, index=False)  # checkpoint
                print(f"  {i + 1}/{len(cases)} done, {time.time() - t_start:.0f} s", flush=True)

    df = pd.DataFrame(results).sort_values("case")
    df.to_csv(out_csv, index=False)

    valid = df[df["rank"].notna()] if "rank" in df else df.iloc[0:0]
    print("\n--- Summary ---")
    print(df["status"].value_counts().to_string())
    if len(valid):
        print(f"N valid ranks: {len(valid)}")
        print(f"Mean rank: {valid['rank'].mean():.2f}")
        print(f"Mean SAE: {df['sae'].dropna().mean():.4f}")
    print(f"Total time: {time.time() - t_start:.0f} s -> {out_csv}")


if __name__ == "__main__":
    main()
