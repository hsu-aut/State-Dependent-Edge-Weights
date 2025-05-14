import os
from pathlib import Path

ROOT_DIR = Path("/beegfs/home/m/m778332/masterarbeit/Code")
TEMP_PATH = os.environ.get("SLURM_TMPDIR", r"C:/Users/Moritz/AppData/Local/Temp")
PROJECT_PATH = str(Path("/beegfs/home/m/m778332/masterarbeit/Code", "Results"))
MODELICAFILELOCATION = str(ROOT_DIR / "Data" / "models")
MODELICAMODELNAME = "ModVA_online_stable"
MODELICAFILENAME = f"{MODELICAMODELNAME}_V6.mo"

START_TIME = 0
STOP_TIME = 600
STEP_NUMBER = 12645
SOLVER = "ida"
OUT_FORMAT = "csv"
