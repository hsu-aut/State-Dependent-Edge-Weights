#!/bin/bash
#SBATCH --job-name=tw_regen
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=72
#SBATCH --time=06:00:00
#SBATCH --output=tw_regen_%j.log
#SBATCH --partition=small
# Regenerates the test cases with the new reference (regen_testcases.py) and checks the alarm patterns of the old
# and the new set (check_testcases.py).
#   quick check on the 200 sample cases : sbatch --partition=dev --time=01:00:00 --export=ALL,CASES=$HOME/hsuper_eval/sample_prune_valves/cases_kl.csv,OUTTC=$HOME/hsuper_eval/testcases_v2_sample job_regen.sh
#   all cases                            : sbatch job_regen.sh
set -euo pipefail
CODE=/beegfs/project/ma-kausalegraphen/m778332/masterarbeit/Code
REPO=${REPO:-$HOME/Temporal-Weighting-for-Causal-Graphs}
REF=${REF:-$HOME/hsuper_eval/sim_ref/ModVA_online_stable_V6_nominal.csv}
OUTTC=${OUTTC:-$HOME/hsuper_eval/testcases_v2}
EXTRA=()
[ -n "${CASES:-}" ] && EXTRA+=(--cases-from "$CASES")
[ -n "${MASK:-}" ] && EXTRA+=(--mask-closed-valves)   # pressure V201-V203 ignored while the valve is closed
[ -n "${THR:-}" ] && EXTRA+=(--threshold "$THR")      # alarm threshold (original 0.05)
[ -n "${PERSIST:-}" ] && EXTRA+=(--persist "$PERSIST")  # alarm after k consecutive seconds (original 1)

module load python/3.11.7
source "$HOME/twenv/bin/activate"
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "ref=$REF out=$OUTTC $(date)"
python regen_testcases.py --repo "$REPO" --input-dir /beegfs/project/ma-kausalegraphen --output-dir "$OUTTC" \
    --original-csv "$REF" --workers "$SLURM_CPUS_PER_TASK" ${EXTRA[@]+"${EXTRA[@]}"} > "$OUTTC.regen.log" 2>&1 || { tail -30 "$OUTTC.regen.log"; exit 1; }
tail -3 "$OUTTC.regen.log"
echo "=== old test cases"
python check_testcases.py --testcases "$CODE/Data/data_for_aroyyo" --n 48
echo "=== new test cases"
python check_testcases.py --testcases "$OUTTC" --n 48
du -sh "$OUTTC"
echo "=== finished $(date) ==="
