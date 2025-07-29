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


def process_all_folders(root_dir: str, output_base_dir: str):
    print(f"Starte globale Verarbeitung der Ordner in: {root_dir}")
    all_processed_dfs = [] # Liste für die optimierten DataFrames jedes Unterordners

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

            # --- ANPASSUNG HIER: Parameter effizient hinzufügen ---
            params_to_assign = {}
            for param, nom_val in PARAMETER_CONFIG.NOMINALS.items():
                params_to_assign[param] = nom_val
            for para, val in PARAMETER_CONFIG.NOMINALS_NOT_FOR_SIMULATION.items():
                params_to_assign[para] = val
            params_to_assign[changed_name] = changed_val
            df = df.assign(**params_to_assign)
            gc.collect() 
            # --- ENDE ANPASSUNG --- 

            # Spaltenauswahl und -umbenennung basierend auf MAPPING_DICT
            # Ziel: Nur die absolut notwendigen Daten für df_processed extrahieren
            final_columns_data = {}
            # 1. Gemappte Simulationsdaten
            for sim_col, graph_cols in sim_to_graph.items():
                if sim_col in df.columns:
                    for graph_col in graph_cols:
                        # .values extrahiert NumPy Array, Typ sollte von optimiertem df stammen
                        final_columns_data[graph_col] = df[sim_col].values 
            
            # 2. Zeitspalte
            if "time" in df.columns:
                final_columns_data["time"] = df["time"].values
            else:
                print(f"  WARNUNG: Spalte 'time' nicht gefunden in {parquet_path} für {sub}.")

            # 3. Parameter-Spalten
            param_column_names = list(PARAMETER_CONFIG.NOMINALS.keys()) + \
                                 list(PARAMETER_CONFIG.NOMINALS_NOT_FOR_SIMULATION.keys()) + \
                                 [changed_name]
            for p_col in param_column_names:
                if p_col in df.columns: # Stellt sicher, dass Spalte existiert
                    final_columns_data[p_col] = df[p_col].values
            
            # Index für das neue DataFrame
            original_index = df.index

            # Ursprüngliches df wird nun nicht mehr direkt benötigt
            del df
            gc.collect()

            # Erzeuge das "schlanke" df_processed DataFrame
            # Die Typen der Arrays in final_columns_data sollten bereits optimiert sein.
            df_processed = pd.DataFrame(final_columns_data, index=original_index)
            
            df_processed = optimize_df_dtypes(df_processed, f"df_processed_{sub}")
            gc.collect()

            all_processed_dfs.append(df_processed)
            print(f"  ✓ Verarbeitet und für Kombination optimiert: {sub}")

        except FileNotFoundError:
            print(f"  → Überspringe {sub}: Datei nicht gefunden.")
        except ValueError as e:
            print(f"  → Überspringe {sub}: ValueError beim Verarbeiten: {e}")
        except Exception as e:
            print(f"  → Überspringe {sub}: Unerwarteter Fehler: {e}")

    if not all_processed_dfs:
        print("Keine Daten verarbeitet, nichts zu kombinieren und speichern.")
        return

    print(f"\nKombiniere {len(all_processed_dfs)} optimierte DataFrames...")
    try:
        combined = pd.concat(all_processed_dfs, ignore_index=True, copy=False)
    except MemoryError:
        print("FATAL: MemoryError während pd.concat! Nicht genügend Speicher, um alle DataFrames zu kombinieren.")
        del all_processed_dfs
        gc.collect()
        return # Abbruch
    except Exception as e:
        print(f"FATAL: Unerwarteter Fehler während pd.concat: {e}")
        del all_processed_dfs
        gc.collect()
        return # Abbruch

    del all_processed_dfs
    gc.collect()

    print("Optimiere Datentypen des finalen kombinierten DataFrames...")
    combined = optimize_df_dtypes(combined, "combined_df_final")
    gc.collect()

    print("Konvertiere Aktuator-Spalten zu Integer im kombinierten DataFrame...")
    actuator_cols_to_convert = [col for col in PARAMETER_CONFIG.ACTUATORS_FOR_MODI if col in combined.columns]
    if len(actuator_cols_to_convert) != len(PARAMETER_CONFIG.ACTUATORS_FOR_MODI):
        missing = set(PARAMETER_CONFIG.ACTUATORS_FOR_MODI) - set(actuator_cols_to_convert)
        print(f"WARNUNG: Nicht alle Aktuator-Spalten ({missing}) für Typkonvertierung im kombinierten DataFrame gefunden.")
    
    if actuator_cols_to_convert:
        try:
            combined[actuator_cols_to_convert] = combined[actuator_cols_to_convert].astype(int)
        except ValueError as e:
            print(f"WARNUNG: Konnte Aktuator-Spalten nicht zu int konvertieren. Fehler: {e}. Sind NaNs oder nicht-numerische Werte vorhanden?")
        except Exception as e:
            print(f"FEHLER beim Konvertieren der Aktuator-Spalten zu int: {e}")
    else:
        print("Keine Aktuator-Spalten zum Konvertieren gefunden.")


    print("Gruppiere nach Modes und speichere Ergebnisse...")
    os.makedirs(output_base_dir, exist_ok=True)
    
    grouping_cols = [col for col in PARAMETER_CONFIG.ACTUATORS_FOR_MODI if col in combined.columns]
    if not grouping_cols or len(grouping_cols) != len(PARAMETER_CONFIG.ACTUATORS_FOR_MODI):
        print(f"WARNUNG: Grouping-Spalten ({PARAMETER_CONFIG.ACTUATORS_FOR_MODI}) nicht (vollständig) im kombinierten DataFrame vorhanden. Vorhanden: {grouping_cols}. Speichere ungruppiert.")
        file_path = os.path.join(output_base_dir, "combined_ungrouped_data.parquet")
        combined.to_parquet(file_path, index=False)
        print(f"✓ Ungruppierte kombinierte Daten gespeichert in {file_path!r}")
    else:
        try:
            for mode_vals, group_df in combined.groupby(grouping_cols, dropna=False):
                mode_name = "mode_"
                if isinstance(mode_vals, tuple): # Mehrere Grouping-Spalten
                    mode_name += "_".join(str(v) for v in mode_vals)
                else: # Eine Grouping-Spalte
                    mode_name += str(mode_vals)
                
                file_path = os.path.join(output_base_dir, f"{mode_name}.parquet")
                group_df.to_parquet(file_path, index=False)
                print(f"✓ {mode_name} gespeichert in {file_path!r}")
        except KeyError as e:
            print(f"FEHLER beim Grouping (KeyError): {e}. Überprüfen Sie die Spaltennamen in PARAMETER_CONFIG.ACTUATORS_FOR_MODI.")
            # Speichere das ungruppierte DataFrame als Fallback
            fallback_path = os.path.join(output_base_dir, "combined_grouping_key_error.parquet")
            combined.to_parquet(fallback_path, index=False)
            print(f"✓ Kombinierte Daten (KeyError beim Grouping) gespeichert in {fallback_path!r}")
        except Exception as e:
            print(f"FEHLER beim Grouping oder Speichern der Modes: {e}")
            fallback_path = os.path.join(output_base_dir, "combined_grouping_processing_error.parquet")
            combined.to_parquet(fallback_path, index=False)
            print(f"✓ Kombinierte Daten (Allg. Fehler beim Grouping) gespeichert in {fallback_path!r}")

    del combined
    gc.collect()
    print("Globale Verarbeitung abgeschlossen.")


if __name__ == "__main__":
    root_dir_to_process = r"C:\Users\Moritz\Desktop\Master\Code\Test_Data"
    
    output_directory = r"C:\Users\Moritz\Desktop\Master\Code\Data\mode_parquets"

    print(f"Starte Verarbeitung der Ordner in: {root_dir_to_process}")
    print(f"Ausgabe erfolgt nach: {output_directory}")
    
    processed_results = process_all_folders(root_dir_to_process, output_directory)
    
    print("Verarbeitung abgeschlossen.")