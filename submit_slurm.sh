#!/bin/bash
#SBATCH --job-name=simSweep
#SBATCH --array=0-53%10
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=16:00:00
#SBATCH --output=logs/sim_%A_%a.out

module load USER-SPACK
module load squashfuse
module load apptainer
module load miniforge3
eval "$(conda shell.bash hook)"
conda activate sim_env

cd /beegfs/home/m/m778332/masterarbeit/Code
export PYTHONPATH="$PWD:$PYTHONPATH"
export PROJECT_PATH="$SLURM_TMPDIR/results"
mkdir -p "$PROJECT_PATH"

SIF="/beegfs/home/m/m778332/masterarbeit/openmodelica-full.sif"
srun apptainer exec --userns "$SIF" python3 simulation/simulate.py

DEST="/beegfs/home/m/m778332/masterarbeit/Results/job_$SLURM_JOB_ID"
mkdir -p "$DEST"
cp -r "$PROJECT_PATH" "$DEST"
