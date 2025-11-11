import dask.dataframe as dd
import pandas as pd # Wird hier nur für kleine Teile oder Typ-Annotationen benötigt
import os
import shutil # Optional, zum Aufräumen
import PARAMETER_CONFIG 
import gc

def create_final_modes_with_dask(intermediate_dir: str, final_output_dir: str):
    print(f"\nStarte Stufe 2: Dask-Verarbeitung der Zwischenergebnisse.")
    print(f"Lese Zwischendateien aus: {intermediate_dir}")
    print(f"Finale Modus-Dateien werden gespeichert in: {final_output_dir}")

    if not os.path.exists(intermediate_dir) or not os.listdir(intermediate_dir):
        print(f"FEHLER: Zwischenverzeichnis '{intermediate_dir}' existiert nicht oder ist leer.")
        print("Bitte zuerst das Skript der Stufe 1 (prepare_data_for_graph.py) ausführen.")
        return

    os.makedirs(final_output_dir, exist_ok=True)

    # 1. Lese alle zwischengespeicherten Parquet-Dateien als Dask DataFrame
    # Dask ist "lazy" und lädt die Daten nicht sofort komplett in den Speicher.
    print("Lese Parquet-Dateien aus dem Zwischenverzeichnis mit Dask...")
    try:
        # Das Schema der Zwischendateien sollte durch Stufe 1 konsistent sein.
        # Das Muster "intermediate__*.parquet" passt zu den in Stufe 1 gespeicherten Dateien.
        ddf = dd.read_parquet(os.path.join(intermediate_dir, "intermediate__*.parquet"), engine='pyarrow')
    except Exception as e:
        print(f"FEHLER beim Lesen der Parquet-Dateien aus '{intermediate_dir}' mit Dask: {e} (Typ: {type(e).__name__})")
        return
        
    print(f"Dask DataFrame erfolgreich geladen. Spalten: {list(ddf.columns)}")
    print(f"Dask DataFrame hat geschätzt {ddf.npartitions} Partitionen.")


    # 2. Definiere die Spalten für das Grouping
    # Die ACTUATORS_FOR_MODI Spalten sollten bereits Integer sein (aus Stufe 1).
    grouping_cols = [col for col in PARAMETER_CONFIG.ACTUATORS_FOR_MODI if col in ddf.columns]

    if not grouping_cols or len(grouping_cols) != len(PARAMETER_CONFIG.ACTUATORS_FOR_MODI):
        missing_cols_str = list(set(PARAMETER_CONFIG.ACTUATORS_FOR_MODI) - set(ddf.columns))
        print(f"FEHLER: Nicht alle für das Grouping benötigten Spalten ({PARAMETER_CONFIG.ACTUATORS_FOR_MODI}) sind im Dask DataFrame vorhanden.")
        print(f"Fehlende Spalten: {missing_cols_str}. Vorhandene Spalten für Grouping: {grouping_cols}.")
        # Fallback: Speichere das ungruppierte (aber via Dask kombinierte) DataFrame
        print("Versuche, das gesamte Dask DataFrame ungruppiert zu speichern...")
        try:
            # Dask's to_parquet kann ein Verzeichnis mit mehreren Parquet-Dateien erstellen
            ddf.to_parquet(os.path.join(final_output_dir, "dask_combined_ungrouped_data"), write_index=False, overwrite=True)
            print(f"  ✓ Ungruppiertes Dask DataFrame gespeichert in '{final_output_dir}/dask_combined_ungrouped_data'")
        except Exception as e_save:
            print(f"  FEHLER beim Speichern des ungruppierten Dask DataFrames: {e_save} (Typ: {type(e_save).__name__})")
        return
    
    print(f"Globale Gruppierung mit Dask anhand der Spalten: {grouping_cols}")

    # 3. Führe das globale Groupby durch und speichere jede Gruppe
    # Wir berechnen zuerst die eindeutigen Kombinationen der Grouping-Spalten.
    # Diese Liste von Kombinationen sollte in den Speicher passen.
    print("Berechne eindeutige Mode-Kombinationen für das Grouping...")
    try:
        # .drop_duplicates().compute() holt die eindeutigen Kombinationen als Pandas DataFrame
        unique_mode_combinations = ddf[grouping_cols].drop_duplicates().compute()
        print(f"  {len(unique_mode_combinations)} eindeutige Mode-Kombinationen gefunden.")
        if len(unique_mode_combinations) == 0:
            print("WARNUNG: Keine eindeutigen Mode-Kombinationen gefunden. Es werden keine Mode-Dateien erstellt.")
            return
    except Exception as e:
        print(f"FEHLER beim Berechnen der eindeutigen Mode-Kombinationen mit Dask: {e} (Typ: {type(e).__name__})")
        return

    for _, row in unique_mode_combinations.iterrows():
        mode_values_for_name = []
        filter_conditions = [] # Liste für die Filterbedingungen für Dask

        # Baue die Filterbedingungen für die aktuelle Mode-Kombination
        for col_name in grouping_cols:
            value = row[col_name]
            mode_values_for_name.append(str(value))
            filter_conditions.append((ddf[col_name] == value)) # Dask Series Vergleich
        
        # Kombiniere alle Filterbedingungen mit einem logischen UND
        current_filter_condition = filter_conditions[0]
        for cond in filter_conditions[1:]:
            current_filter_condition = current_filter_condition & cond
        
        mode_name = "mode_" + "_".join(mode_values_for_name)
        output_file_path = os.path.join(final_output_dir, f"{mode_name}.parquet")
        
        print(f"  Filtere Dask DataFrame und speichere Gruppe: {mode_name} ...")
        
        try:
            # Filtere das Dask DataFrame, um nur die aktuelle Gruppe zu erhalten
            group_ddf = ddf[current_filter_condition]
            
            if not group_ddf.map_partitions(len).compute().sum() == 0: # Prüfen, ob die Gruppe Daten enthält
                group_pdf = group_ddf.compute() # Holt die Gruppe als Pandas DataFrame
                # Optional: optimize_df_dtypes(group_pdf.copy(), f"group_pdf_{mode_name}")
                group_pdf.to_parquet(output_file_path, index=False, engine='pyarrow')
                print(f"    ✓ {mode_name} (als Pandas DF) gespeichert in {output_file_path}")
                del group_pdf # Speicher der Pandas Gruppe freigeben
            else:
                print(f"    INFO: Gruppe {mode_name} ist leer und wird nicht gespeichert.")

            del group_ddf # Speicher des Dask-Gruppen-Views freigeben
            gc.collect()

        except MemoryError:
            print(f"  FATAL: MemoryError beim Berechnen (.compute()) oder Speichern der Gruppe {mode_name}.")
            print(f"  Diese einzelne Mode-Gruppe ist zu groß für den verfügbaren Speicher ({mode_name}).")
        except Exception as e:
            print(f"  FEHLER beim Verarbeiten oder Speichern der Gruppe {mode_name}: {e} (Typ: {type(e).__name__})")

    # Optional: Aufräumen des Zwischenverzeichnisses nach erfolgreicher Verarbeitung
    # print(f"\nOptional: Lösche das Zwischenverzeichnis '{intermediate_dir}'...")
    # try:
    #     shutil.rmtree(intermediate_dir)
    #     print(f"  ✓ Zwischenverzeichnis erfolgreich gelöscht.")
    # except Exception as e:
    #     print(f"  FEHLER beim Löschen des Zwischenverzeichnisses: {e}")

    print("\nStufe 2: Dask-Verarbeitung und Speicherung der finalen Modes abgeschlossen.")

if __name__ == '__main__':
    # Pfade für den Cluster (Beispiele, bitte anpassen)
    
    # Das Verzeichnis, in das Stufe 1 die optimierten Parquet-Dateien geschrieben hat
    intermediate_files_directory = "/beegfs/home/m/m778332/masterarbeit/Code/Data/intermediate_parquets/"
    
    # Das finale Ausgabeverzeichnis für die mode_*.parquet Dateien
    final_modes_output_directory = "/beegfs/home/m/m778332/masterarbeit/Code/Data/mode_parquets_final_dask/"

    create_final_modes_with_dask(intermediate_files_directory, final_modes_output_directory)

    print("Dask-basiertes Mode-Erstellungsprogramm beendet.")