import os
import pandas as pd
from collections import defaultdict
import PARAMETER_CONFIG  
import MAPPING_DICT 
import gc   

def optimize_df_dtypes(df: pd.DataFrame, df_name: str = "DataFrame") -> pd.DataFrame:
    """
    Optimiert die Datentypen eines Pandas DataFrames, um Speicher zu sparen.
    """
    for col in df.columns:
        col_type = df[col].dtype
        try:
            if col_type == "float64":
                df[col] = pd.to_numeric(df[col], downcast='float') # zu float32
            elif "float" in str(col_type):
                 pass # Belasse float32, wenn es schon float32 ist
            elif col_type == "int64":
                df[col] = pd.to_numeric(df[col], downcast='integer')
            elif col_type == "object":
                if len(df[col]) > 0 and df[col].nunique() / len(df[col]) < 0.5:
                    df[col] = df[col].astype('category')
        except Exception as e:
            print(f"    WARNUNG: Konnte Spalte '{col}' ({col_type}) in {df_name} nicht optimieren. Fehler: {e}")
    return df

def read_changed_param(txt_path: str) -> tuple[str, float]:
    """
    Liest aus einer Datei im Format
      Geändert: <ParamName>
      Wert: <Wert>
    und gibt (ParamName, Wert) zurück.
    """
    param_name = None
    param_val = None
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("Geändert:"):
                param_name = line.split(":", 1)[1].strip()
            elif line.startswith("Wert:"):
                param_val = float(line.split(":", 1)[1].strip())
    if param_name is None or param_val is None:
        raise ValueError(f"Ungültiges Format in {txt_path!r}")
    return param_name, param_val


# ANGEPASSTE Funktion: process_and_save_intermediates
def process_and_save_intermediates(root_dir: str, intermediate_output_dir: str):
    print(f"Starte Stufe 1: Vorverarbeitung und Speichern von Zwischenergebnissen.")
    print(f"Eingabeverzeichnis: {root_dir}")
    print(f"Ausgabe der Zwischendateien nach: {intermediate_output_dir}")

    os.makedirs(intermediate_output_dir, exist_ok=True) # Stelle sicher, dass das Verzeichnis existiert

    sim_to_graph = defaultdict(list)
    for graph, sim in MAPPING_DICT.matching.items():
        sim_to_graph[sim].append(graph)

    sub_folders = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    total_folders = len(sub_folders)
    print(f"Anzahl der zu verarbeitenden Unterordner: {total_folders}")

    for i, sub in enumerate(sub_folders):
        print(f"\nVerarbeite Ordner {i+1}/{total_folders}: {sub}")
        folder = os.path.join(root_dir, sub)
        
        parquet_file = next((f for f in os.listdir(folder) if f.lower().endswith(".parquet")), None)
        txt_file = next((f for f in os.listdir(folder) if f.lower().endswith(".txt")), None)
        
        if not parquet_file or not txt_file:
            print(f"  → Überspringe {sub}: Parquet- oder TXT-Datei fehlt.")
            continue

        parquet_path = os.path.join(folder, parquet_file)
        txt_path = os.path.join(folder, txt_file)

        try:
            df = pd.read_parquet(parquet_path)
            df = optimize_df_dtypes(df, f"df_{sub}")
            gc.collect()

            changed_name, changed_val = read_changed_param(txt_path)

            params_to_assign = {}
            for param, nom_val in PARAMETER_CONFIG.NOMINALS.items():
                params_to_assign[param] = nom_val
            for para, val in PARAMETER_CONFIG.NOMINALS_NOT_FOR_SIMULATION.items():
                params_to_assign[para] = val
            params_to_assign[changed_name] = changed_val
            
            df = df.assign(**params_to_assign)
            gc.collect()

            final_columns_data = {}
            for sim_col, graph_cols_list in sim_to_graph.items():
                if sim_col in df.columns:
                    for graph_col_item in graph_cols_list:
                        final_columns_data[graph_col_item] = df[sim_col].values 
            
            if "time" in df.columns:
                final_columns_data["time"] = df["time"].values
            else:
                print(f"  WARNUNG: Spalte 'time' nicht gefunden in {parquet_path} für {sub}.")

            param_column_names = list(PARAMETER_CONFIG.NOMINALS.keys()) + \
                                 list(PARAMETER_CONFIG.NOMINALS_NOT_FOR_SIMULATION.keys()) + \
                                 [changed_name]
            for p_col in param_column_names:
                if p_col in df.columns:
                    final_columns_data[p_col] = df[p_col].values
            
            original_index = df.index
            del df
            gc.collect()

            df_processed = pd.DataFrame(final_columns_data, index=original_index)
            df_processed = optimize_df_dtypes(df_processed, f"df_processed_{sub}")

            # WICHTIG: Konvertiere ACTUATORS_FOR_MODI Spalten zu int BEVOR sie gespeichert werden
            actuator_cols_to_convert = [col for col in PARAMETER_CONFIG.ACTUATORS_FOR_MODI if col in df_processed.columns]
            if len(actuator_cols_to_convert) == len(PARAMETER_CONFIG.ACTUATORS_FOR_MODI):
                try:
                    df_processed[actuator_cols_to_convert] = df_processed[actuator_cols_to_convert].astype(int)
                except ValueError as e:
                    print(f"WARNUNG ({sub}): Konnte Aktuator-Spalten in df_processed nicht zu int konvertieren. Fehler: {e}.")
            else:
                missing_act_cols = set(PARAMETER_CONFIG.ACTUATORS_FOR_MODI) - set(df_processed.columns)
                print(f"WARNUNG ({sub}): Nicht alle Aktuator-Spalten ({missing_act_cols}) für Typkonvertierung in df_processed gefunden.")
            
            # Speichere das optimierte df_processed als einzelne Parquet-Datei
            # Verwende einen eindeutigen Präfix oder Suffix für diese Zwischendateien
            intermediate_file_path = os.path.join(intermediate_output_dir, f"intermediate__{sub}.parquet")
            df_processed.to_parquet(intermediate_file_path, index=False) # index=False ist üblich
            print(f"  ✓ Zwischenergebnis gespeichert: {intermediate_file_path}")

            del df_processed # Speicher sofort freigeben
            gc.collect()

        except FileNotFoundError:
            print(f"  → Überspringe {sub}: Datei nicht gefunden.")
        except ValueError as e:
            print(f"  → Überspringe {sub}: ValueError beim Verarbeiten: {e}")
        except Exception as e:
            print(f"  → FEHLER beim Verarbeiten von {sub}: {e} (Typ: {type(e).__name__})")

    print("\nStufe 1: Vorverarbeitung und Speichern aller Zwischenergebnisse abgeschlossen.")

if __name__ == "__main__":
    # Pfade für den Cluster
    root_dir_to_process = "/beegfs/project/ma-kausalegraphen/"
    # NEU: Ein Verzeichnis für die zwischengespeicherten, optimierten Parquet-Dateien
    intermediate_directory = "/beegfs/home/m/m778332/masterarbeit/Code/Data/intermediate_parquets/"
    
    # Das finale Ausgabeverzeichnis wird dann vom Dask-Skript verwendet
    # final_output_directory = "/beegfs/home/m/m778332/masterarbeit/Code/Data/mode_parquets_final/"

    print(f"Starte Skript prepare_data_for_graph.py (Stufe 1 - Zwischenergebnisse)")
    
    # Rufe die modifizierte Funktion auf
    process_and_save_intermediates(root_dir_to_process, intermediate_directory)
    
    print("Skript prepare_data_for_graph.py (Stufe 1) beendet.")


if __name__ == "__main__":
    # Pfade für den Cluster
    root_dir_to_process = "/beegfs/project/ma-kausalegraphen/"
    # NEU: Ein Verzeichnis für die zwischengespeicherten, optimierten Parquet-Dateien
    intermediate_directory = "/beegfs/home/m/m778332/masterarbeit/Code/Data/intermediate_parquets/"
    
    # Das finale Ausgabeverzeichnis wird dann vom Dask-Skript verwendet
    # final_output_directory = "/beegfs/home/m/m778332/masterarbeit/Code/Data/mode_parquets_final/"

    print(f"Starte Skript prepare_data_for_graph.py (Stufe 1 - Zwischenergebnisse)")
    
    # Rufe die modifizierte Funktion auf
    process_and_save_intermediates(root_dir_to_process, intermediate_directory)
    
    print("Skript prepare_data_for_graph.py (Stufe 1) beendet.")
