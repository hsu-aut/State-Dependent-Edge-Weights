#!/bin/bash
#SBATCH --job-name=tw_split
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --output=tw_split_%j.log
#SBATCH --partition=small
# Held-out check, step 1: training data of half A (even sweep index) from the mode files (split_modes.py).
#   sbatch job_split.sh
set -euo pipefail
CODE=/beegfs/project/ma-kausalegraphen/m778332/masterarbeit/Code
OUTA=${OUTA:-/beegfs/project/ma-kausalegraphen/tw_modes_A}
module load python/3.11.7
source "$HOME/twenv/bin/activate"
cd "$SLURM_SUBMIT_DIR"
echo "out=$OUTA $(date)"
python split_modes.py --modes-dir "$CODE/Data/mode_parquets_final_dask" --sweep sim_ref/parameter_combination.json \
    --out "$OUTA" --diagnosable diagnosable_v4.csv
du -sh "$OUTA"
echo "=== finished $(date) ==="
