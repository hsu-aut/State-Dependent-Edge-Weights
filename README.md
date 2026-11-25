# State-dependent Edge Weights for Causal Graphs

Code and evaluation results for the paper

> **Method for Integrating State-dependent Edge Weights into Causal Graphs for Localizing Deviating Model Parameters**
> submitted to *at – Automatisierungstechnik* (manuscript auto-2026-0162, revised version).

The method learns edge weights for an expert-defined directed causal graph from simulation data. The data are segmented into operating states by the valve positions. For each state, a two-slice time-varying dynamic Bayesian network (TV-DBN) is fitted as a linear Gaussian Bayesian network, and the edge weights are computed as KL divergence (or, for comparison, as absolute regression coefficients). The weights are mapped back to the original graph and used in the graph-based root-cause localization of Ramonat et al. (2024).

This repository continues [hsu-aut/Temporal-Weighting-for-Causal-Graphs](https://github.com/hsu-aut/Temporal-Weighting-for-Causal-Graphs) (commit `34b76f9`, history included) and adds the corrections and the complete re-evaluation of the revised paper.

## Contents

| Folder | Content |
|---|---|
| `simulation/` | Simulation of the fault runs with OpenModelica via OMPython (one parameter varied per run) |
| `data_preparation/` | Mapping of simulation variables to graph vertices, segmentation into operating states (Dask), nominal parameter values (`PARAMETER_CONFIG.py`) |
| `graph_building/`, `graph_analyse/` | Causal graph from AutomationML (`Arroyo_DCDG_PLUT.py`), TV-DBN construction, weight computation (`graph_analyse/eval_graph.py`), original diagnosis driver (`graph_analyse/inst_algo.py`) |
| `graph_operations/` | Earlier in-memory version of the weight computation (not used for the paper) |
| `evaluation/` | Re-evaluation of the revised paper: reference run, test-case generation, train/test split, weight computation, diagnosis per test case, statistics (see below) |
| `results/` | Per-test-case results and summary tables of the revised paper |

The simulation data (approx. 15,000 runs, 59 GB of mode files) and the AutomationML models are not part of the repository (`Data/` is excluded). The scripts in `evaluation/` default to their locations on the HSUper cluster of Helmut Schmidt University; all paths can be set on the command line.

## Corrections in the revised version

The re-evaluation for the revision found the following problems in the original evaluation. All results in the revised paper were recomputed after correcting them.

1. **Parameter columns of the training data** (`graph_analyse/eval_graph.py`): parameter columns of the two-slice table were filled with the value of the first row of a mode file. Since a mode file pools all runs, every parameter was constant within an operating state, so the KL weights of all parameter edges were 0 and their regression coefficients meaningless. Fixed in this repository (per-row values, as for the sensors).
2. **Reference run**: the fault-free reference used to compute the residuals followed a different actuator schedule than the fault runs. A new reference run with the same model, solver settings, and schedule was simulated (`evaluation/sim_reference.py`), and all test cases were regenerated (`evaluation/regen_testcases.py`).
3. **Deviation detection**: with the correct reference, the original threshold of 5 % detects almost no faults. Deviations are now flagged at 0.2 % of the sensor range with a persistence of 3 s, and closed-valve pressures of V201–V203 are masked (see [Deviation detection](#deviation-detection)).
4. **Path search**: the path search skips edges with weight ≤ 0.01, which removed many learned edges. The threshold is now applied only to valve edges (`--prune valves` in `evaluation/step2_eval_cases.py`); results of the knowledge-based weighting are unchanged by this.
5. **Evaluation protocol**: ties are resolved by midpoint ranks, and the weights are learned on one half of the runs (even sweep index) and evaluated on the other half (odd sweep index).

Known discrepancies that could not be resolved from the available material:
- `data_preparation/parameter_values.py` generates equidistant parameter values, whereas the stored runs are approximately normally distributed around the nominal value (standard deviation about 8.3 %). The paper describes the values as they occur in the data.
- Tank parameters are listed in the sweep configuration, but no tank runs exist in the simulation data.
- `graph_analyse/inst_algo.py` uses the AML model `..._reduced_V2.aml` (102 candidates), whereas the weights and the paper use `..._reduced.aml` (81 candidates). The evaluation uses `evaluation/step2_eval_cases.py` with the `--aml` option instead.

## Deviation detection

Each test case compares a fault run with the fault-free reference run of the nominal model (same actuator schedule). For every sensor, the residual is the difference between both runs divided by the maximum absolute reference value of the sensor, on a 1 s grid. A sensor counts as deviating at time *t* if the absolute residual has exceeded 0.002 (0.2 % of the maximum reference value) with the same sign during the last three time steps *t*−2, …, *t*. The deviation is recorded as +1 or −1 according to this sign, and as 0 otherwise. Test cases are generated with `evaluation/regen_testcases.py` (`job_regen.sh` with `MASK=1 THR=0.002 PERSIST=3`).

**Masking of closed-valve pressures.** The pressures downstream of the tank outlet valves V201–V203 are not evaluated while the respective valve is closed (residual and deviation set to 0, `--mask-closed-valves`). The enclosed pipe section is then hydraulically isolated, and its pressure is numerically ill-defined in the simulation, with differences of up to 80 % between runs that otherwise agree (`evaluation/inspect_pressure.py`). The effect was found at V201 and V202; V203 is masked for consistency.

**Choice of threshold and persistence** (`evaluation/detectability.py`, `noise_vs_signal.py`, `threshold_sweep.py`):
- *Fault-free baseline.* 157 test cases have a parameter that deviates by less than 0.1 % from its nominal value and are therefore practically fault-free. Their residuals show isolated spikes of one time step of up to a few percent at fixed instants close to valve switching, but no persistent deviations.
- *Persistence.* With a persistence of three time steps, none of these 157 cases shows a deviation at any threshold between 0.1 % and 5 % (one-sided 95 % upper confidence bound of the false-alarm rate: 1.9 %). The persistence thus separates the numerical spikes from parameter effects.
- *Threshold.* The threshold determines which faults can be detected at all. For most parameter types, the effects on the sensors remain well below 1 % of the sensor range. With a threshold of 5 % (as in the original evaluation) and the same persistence, only 7.6 % of the faults with a deviation of at least 10 % would be detected, compared with 38 % at 0.2 % (stratified sample of 3,000 test cases).
- *Lower limit.* The residuals are stored with a resolution of 10⁻³. The threshold of 0.2 % is the smallest value that lies clearly above this resolution.

## Reproducing the evaluation

Requirements: Python 3.11 with numpy, pandas, pyarrow, scipy, scikit-learn, pgmpy, igraph, networkx, pyvis, openpyxl; OpenModelica 1.25.0 (container image `openmodelica/openmodelica:v1.25.0-ompython`) with Modelica Standard Library 4 for the reference run. The SLURM job scripts were written for HSUper (`small` partition, 72 cores per node).

Steps (run from `evaluation/`; each script documents its arguments in its header):

| Step | Script | Output |
|---|---|---|
| 1. Reference run of the nominal model | `sim_reference.py`, `job_sim_ref.sh` (`npy_to_json.py` converts the sweep file) | nominal result CSV |
| 2. Validate the reference against fault runs | `check_reference.py`, `compare_runs.py`, `inspect_pressure.py` | console |
| 3. Generate the test cases | `regen_testcases.py`, `job_regen.sh` with `MASK=1 THR=0.002 PERSIST=3` | `testcases_v4/` |
| 4. Choose threshold and persistence | `threshold_sweep.py`, `detectability.py`, `noise_vs_signal.py`, `check_testcases.py` | console |
| 5. Observable test cases per parameter type | `diag_by_type.py --out diagnosable_v4.csv`, `effect_check.py` | `diagnosable_v4.csv` |
| 6. Split runs into halves A/B | `split_modes.py`, `job_split.sh` | mode files of half A, `split_A.csv`, `split_B.csv`, `diagnosable_v4_B.csv` |
| 7. Edge weights per operating state | `step0_weights_fixed.py`, `job_weights.sh` with `MODESDIR=<half A> OUT=weights_A` | `weights_A/` |
| 8. Diagnosis per test case | `step2_eval_cases.py`, `job_eval.sh` (settings below) | `cases_<config>.csv` |
| 9. Statistics | `final_eval.py`, `heldout_eval.py`, `step3_analyze.py` | `results/summary/` |

Settings of the final evaluation (step 8), one job per row:

```bash
C="AML=<Data/models>/ModVA_Mixer_incl_SensorNamingConvention_reduced.aml,WEIGHTS=$PWD/weights_A,TESTCASES=$PWD/testcases_v4,INCLUDE=$PWD/diagnosable_v4_B.csv,IDAGG=max,WMAP=exp,PRUNE=valves"
sbatch --export=ALL,$C,CONFIGS="kl beta",PPRIOR=uniform,OUT=final_B job_eval.sh
sbatch --export=ALL,$C,CONFIGS="heuristic_uniform",PPRIOR=uniform,OUT=final_B_uni job_eval.sh
sbatch --export=ALL,$C,CONFIGS="heuristic",PPRIOR=code,OUT=final_B_code job_eval.sh
```

`IDAGG=max` assigns the larger weight when two TV-DBN edges map to the same original edge, `WMAP=exp` maps the learned weights to [0, 1) by 1 − exp(−w), and `PRUNE=valves` restricts the pruning to valve edges. The tables of the paper are then obtained with

```bash
python final_eval.py --results ../results --out summary
python heldout_eval.py ../results
```

## Results

`results/` contains the per-test-case results of the revised paper (one row per test case: rank, best/worst rank over ties, causal values, top-ranked candidate, SAE):

| Folder | Content |
|---|---|
| `final_B/`, `final_B_uni/`, `final_B_code/` | 2,419 observable test cases of half B; KL and regression coefficients, knowledge-based weighting with uniform and with expert prior |
| `heldout_B_weightsA/`, `heldout_B_weightsAll/` | Check on 200 half-B cases: weights learned on half A vs. on all runs |
| `examples/` | The two example test cases of the paper, with the full causal-value matrix per candidate and sensor (`debug/`) |
| `summary/` | Main table, pairwise Wilcoxon tests (Holm-corrected), breakdown by true cause and deviation magnitude |

Main result (mean midpoint rank of the true cause among 81 candidates, lower is better): KL divergence 8.28, regression coefficients 7.55, knowledge-based weighting 20.03 (uniform prior) and 15.21 (expert prior), random ranking 41.

## License

MIT, see `LICENSE`.
