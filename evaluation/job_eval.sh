#!/bin/bash
#SBATCH --job-name=tw_eval
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=72
#SBATCH --time=24:00:00
#SBATCH --output=tw_eval_%j.log
#SBATCH --partition=small
# HSUper partitions: small = regular nodes, exclusive, 72 h limit (node: 2x 36-core Xeon 8360Y = 72 cores, 256 GB);
# dev = testing only, 1 h limit, 1 job at a time.

# Usage:
#   smoke test : sbatch --partition=dev --time=00:30:00 --cpus-per-task=8 --export=ALL,CONFIGS="kl",LIMIT=8,OUT=smoke job_eval.sh
#   full run   : sbatch job_eval.sh
CONFIGS=${CONFIGS:-"kl heuristic beta kl_cond"}
LIMIT=${LIMIT:-0}
OUT=${OUT:-results}
REPO=${REPO:-$(dirname "$PWD")}   # repository root (submit the job from evaluation/)
# Optional: AML=<path> and WEIGHTS=<dir> override the defaults of step2 (V2 AML, stored weights).
# The stored weights belong to the non-V2 AML (K = 81); recomputed weights from job_weights.sh are in weights_fixed/.
#   sbatch --export=ALL,AML=/beegfs/project/ma-kausalegraphen/m778332/masterarbeit/Code/Data/models/ModVA_Mixer_incl_SensorNamingConvention_reduced.aml,WEIGHTS=$PWD/weights_fixed,OUT=results_fixed job_eval.sh
EXTRA=()
[ -n "${AML:-}" ] && EXTRA+=(--aml "$AML")
[ -n "${WEIGHTS:-}" ] && EXTRA+=(--weights-dir "$WEIGHTS")
[ -n "${SAMPLE:-}" ] && EXTRA+=(--sample "$SAMPLE")
[ -n "${IDAGG:-}" ] && EXTRA+=(--id-agg "$IDAGG")
[ -n "${WMAP:-}" ] && EXTRA+=(--weight-map "$WMAP")   # none | exp | max
[ -n "${PRUNE:-}" ] && EXTRA+=(--prune "$PRUNE")      # all | valves
[ -n "${FALLBACK:-}" ] && EXTRA+=(--fallback "$FALLBACK")   # none | rule
[ -n "${PPRIOR:-}" ] && EXTRA+=(--param-prior "$PPRIOR")    # code | uniform (rule weight of parameter edges)
[ -n "${EXCLUDE:-}" ] && EXTRA+=(--exclude "$EXCLUDE")      # cases_*.csv of an earlier run (skip those cases)
[ -n "${INCLUDE:-}" ] && EXTRA+=(--include "$INCLUDE")      # only these cases (e.g. diagnosable_v4.csv), before SAMPLE
[ -n "${DEBUG:-}" ] && EXTRA+=(--debug-dir "$OUT/debug")    # per-step decomposition of the causal value (small runs only)
[ -n "${TESTCASES:-}" ] && EXTRA+=(--testcases "$TESTCASES")  # test-case folder (default: original data_for_aroyyo)

module load python/3.11.7   # the venv was created with this module and needs it at runtime
set -euo pipefail
source "$HOME/twenv/bin/activate"
cd "$SLURM_SUBMIT_DIR"
mkdir -p "$OUT"

# Avoid oversubscription: one numpy thread per worker process
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

for CFG in $CONFIGS; do
  echo "=== $CFG  $(date) ==="
  python step2_eval_cases.py --repo "$REPO" --config "$CFG" \
      --workers "$SLURM_CPUS_PER_TASK" --limit "$LIMIT" --out "$OUT" ${EXTRA[@]+"${EXTRA[@]}"}
done

python step3_analyze.py --results "$OUT" --repo "$REPO"
echo "=== finished $(date) ==="
