#!/bin/bash
#SBATCH --job-name=tw_weights
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=72
#SBATCH --time=24:00:00
#SBATCH --array=0-12%6
#SBATCH --output=tw_weights_%A_%a.log
# One array task per operating state (13 mode files), at most 6 at the same time.
# The original ran all 13 sequentially on one core with 230 GB RAM (approx. 41 h in total).
#
# Usage:
#   validation (smallest mode, original behaviour -> must reproduce the stored file):
#     sbatch --partition=dev --time=01:00:00 --array=0 --export=ALL,MODE=mode_1_0_0_0_0_1,FILL=first,OUT=weights_check_first job_weights.sh
#   same mode with the fix:
#     sbatch --partition=dev --time=01:00:00 --array=0 --export=ALL,MODE=mode_1_0_0_0_0_1,FILL=row,OUT=weights_check_row job_weights.sh
#   all 13 modes with the fix:
#     sbatch job_weights.sh
MODES=(mode_0_0_0_0_0_0 mode_0_0_0_0_0_1 mode_0_0_0_0_1_0 mode_0_0_0_0_1_1 mode_0_0_0_1_0_0 mode_0_0_0_1_1_0
       mode_0_0_1_0_0_0 mode_0_0_1_1_0_0 mode_0_1_0_0_0_0 mode_0_1_1_0_0_0 mode_1_0_0_0_0_0 mode_1_0_0_0_0_1
       mode_1_1_0_0_0_0)
MODE=${MODE:-${MODES[$SLURM_ARRAY_TASK_ID]}}
FILL=${FILL:-row}
OUT=${OUT:-weights_fixed}
# Optional AML=<path>: graph for which the weights are computed (default in step0: ..._reduced.aml, K = 81)
AMLARG=()
[ -n "${AML:-}" ] && AMLARG=(--aml "$AML")
# Optional MODESDIR=<dir>: training data (default in step0: Data/mode_parquets_final_dask); held-out check: tw_modes_A
[ -n "${MODESDIR:-}" ] && AMLARG+=(--modes-dir "$MODESDIR")
# Temporary memmap file: up to approx. 60 GB for the largest mode; deleted at the end of each task.
TMP=${TMP:-/beegfs/project/ma-kausalegraphen/tw_tmp_${USER}}

module load python/3.11.7
set -euo pipefail
source "$HOME/twenv/bin/activate"
cd "$SLURM_SUBMIT_DIR"

echo "=== $MODE  fill=$FILL  out=$OUT  aml=${AML:-default}  modes=${MODESDIR:-default}  tmp=$TMP  $(date) ==="
python step0_weights_fixed.py --out "$OUT" --tmp-dir "$TMP" --param-fill "$FILL" --only "$MODE" ${AMLARG[@]+"${AMLARG[@]}"}
echo "=== finished $MODE $(date) ==="
