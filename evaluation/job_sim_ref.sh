#!/bin/bash
#SBATCH --job-name=tw_simref
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=01:00:00
#SBATCH --output=tw_simref_%j.log
#SBATCH --partition=dev
# Simulates (1) one existing fault run again and (2) the fault-free reference with the settings of simulate.py,
# inside the OpenModelica container (openmodelica.sif, see the pull command in the chat / memory).
#   sbatch --export=ALL,SIF=$HOME/hsuper_eval/openmodelica_1.25.0.sif job_sim_ref.sh
set -euo pipefail
CODE=/beegfs/project/ma-kausalegraphen/m778332/masterarbeit/Code
SIF=${SIF:-$HOME/hsuper_eval/openmodelica_1.25.0.sif}
RUN=${RUN:-/beegfs/project/ma-kausalegraphen/V201.dp_nominal_00196}
OUT=${OUT:-$HOME/hsuper_eval/sim_ref}
NPY=${NPY:-$CODE/Data/parameter_combination.npy}
cd "$SLURM_SUBMIT_DIR"
mkdir -p "$OUT"
echo "sif=$SIF run=$RUN npy=$NPY out=$OUT  $(date)"
module load python/3.11.7
source "$HOME/twenv/bin/activate"
python npy_to_json.py "$NPY" "$OUT/parameter_combination.json"
# container python explicitly (the venv in the bound home directory would otherwise come first in PATH)
apptainer exec --bind /beegfs "$SIF" /usr/bin/python3 "$SLURM_SUBMIT_DIR/sim_reference.py" \
    --model "$CODE/Data/models/ModVA_online_stable_V6.mo" --npy "$OUT/parameter_combination.json" \
    --validate-run "$RUN" --out "$OUT"

python compare_runs.py --stored-run "$RUN" --reproduced "$OUT/reproduce_$(basename "$RUN").csv" \
    --nominal "$OUT/ModVA_online_stable_V6_nominal.csv"
python check_reference.py --ref "$OUT/ModVA_online_stable_V6_nominal.csv" --raw-dir /beegfs/project/ma-kausalegraphen --n 4
echo "=== finished $(date) ==="
