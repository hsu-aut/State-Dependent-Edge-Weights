import os
import time
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from mpi4py import MPI

# Eigene Module/Klassen
from Arroyo_DCDG_PLUT import DCDG_Class
from MySQL_OPCUA_Datahistorian import createNameList
from MAPPING_DICT import matching

def load_dynamic_weights(modes_base_path):
    """
    Liest alle Gewichts-CSVs aus den Modus-Unterordnern ein, bereinigt die ID-Spalte
    und gibt ein Dictionary mit sauberen DataFrames zurück.
    """
    print(f"Lese dynamische Kantengewichte aus: {modes_base_path}")
    all_weights = {}
    if not os.path.isdir(modes_base_path):
        print(f"WARNUNG: Verzeichnis für dynamische Gewichte nicht gefunden: {modes_base_path}")
        return all_weights

    for mode_folder in os.listdir(modes_base_path):
        mode_path = os.path.join(modes_base_path, mode_folder)
        if os.path.isdir(mode_path):
            try:
                csv_file_name = next((f for f in os.listdir(mode_path) if f.endswith('.csv')), None)
                if csv_file_name:
                    csv_path = os.path.join(mode_path, csv_file_name)

                    df = pd.read_csv(csv_path, delimiter=';', decimal=',')

                    df.dropna(subset=['Original_Edge_ID'], inplace=True)

                    if not df.empty:
                        df['Original_Edge_ID'] = df['Original_Edge_ID'].astype(int)

                    df.set_index('Original_Edge_ID', inplace=True)

                    all_weights[mode_folder] = df
                else:
                    print(f"WARNUNG: Keine CSV-Datei im Modus-Ordner gefunden: {mode_path}")
            except Exception as e:
                print(f"FEHLER beim Lesen und Bereinigen des Modus {mode_folder}: {e}")
    
    print(f"{len(all_weights)} Gewichts-Modi erfolgreich geladen.")
    return all_weights

def process_testcase(case_path, aml_file, dList, dNumbers, reverse_mapping, abort_time, testcase_files):
    """
    Diese Funktion kapselt die gesamte Logik zur Verarbeitung eines EINZIGEN Testfalls.
    Sie wird von jedem parallelen Prozess aufgerufen.
    """
    try:
        t0 = time.time()
        # 1. Jeder Prozess initialisiert seine eigene DCDG-Instanz
        dcdg = DCDG_Class()
        dcdg.generate_graphfromAML(aml_file)

        # 2. Lade die spezifischen Parquet-Dateien des Testfalls
        path_alarms = os.path.join(case_path, testcase_files['alarms'])
        path_xmv = os.path.join(case_path, testcase_files['xmv'])
        path_residuals = os.path.join(case_path, testcase_files['residuals'])
        path_parameters = os.path.join(case_path, testcase_files['parameters'])
        path_modi_df = os.path.join(case_path, testcase_files['modi_df'])

        # Lese die Parquet-Dateien in Pandas DataFrames
        df_alarms = pd.read_parquet(path_alarms)
        df_xmv = pd.read_parquet(path_xmv)
        df_residuals = pd.read_parquet(path_residuals)
        df_modi = pd.read_parquet(path_modi_df)
        
        # 3. Verarbeitungslogik angepasst für Pandas DataFrames
        xmv_dict, alarm_dict, deviation_dict = {}, {}, {}
        accumulated_combined_influence_matrix = None

        # Iteriere über die Zeilen der DataFrames (Annahme: alle haben die gleiche Länge)
        for tc in range(len(df_alarms)):
        
            # 1. Hole den aktuellen Modus (die Zeile mit Nullen und Einsen) aus der modi_df
            current_mode_values = df_modi.iloc[tc].astype(int).tolist()
            
            # 2. Baue den passenden Ordnernamen, z.B. "mode_0_1_0_0_1_0"
            mode_folder_name = f"mode_{'_'.join(map(str, current_mode_values))}"
            
            # 3. Wähle das richtige Gewichts-DataFrame aus dem globalen Dictionary aus
            if mode_folder_name in all_mode_weights:
                current_weights_df = all_mode_weights[mode_folder_name]
                dcdg.update_edge_weights_from_mode(current_weights_df)

            else:
                # Fallback, falls ein Modus auftritt, für den keine Gewichte geladen wurden
                print(f"WARNUNG: Modus '{mode_folder_name}' nicht in den geladenen Gewichten gefunden.")
                
            # Aktor-Werte aus df_xmv lesen
            for i in range(8): # number_of_actuators
                # .iloc[zeile, spalte] für 0-basierten Zugriff
                # dNumbers ist 1-basiert, daher dNumbers[i] - 1
                val = df_xmv.iloc[tc, dNumbers[i] - 1]
                xmv_dict[dList[10 + i].replace("_State", "")] = (0 if val is None else val) / 100
            dcdg.update_valves(xmv_dict)

            # Alarm-Daten aus df_alarms lesen
            for j in range(10): # number_of_sensors
                if "AIR" not in dList[j]:
                    alarm_dict[dList[j].replace("V", "YIC").replace("_", "_Measurement_")] = df_alarms.iloc[tc, j]
            dcdg.add_sensorlabels(alarm_dict)
            dcdg.set_alarmstates(alarm_dict)

            # Residual-Werte aus df_residuals lesen
            for k in range(10): # number_of_sensors
                if "AIR" not in dList[k]:
                    deviation_dict[dList[k].replace("V", "YIC").replace("_", "_Measurement_")] = df_residuals.iloc[tc, k]
            dcdg.set_deviations(deviation_dict)

            if not any(alarm_dict.values()):
                continue

            (combined_influence_matrix, _, parameter_names_total, _, _, _,) = dcdg.evaluate_distance_matrix(0.5, update_distance=True)

            if accumulated_combined_influence_matrix is None:
                accumulated_combined_influence_matrix = combined_influence_matrix.copy()
            else:
                accumulated_combined_influence_matrix += combined_influence_matrix

            if tc >= abort_time:
                break
        
        if accumulated_combined_influence_matrix is None:
            return None

        # 4. Ergebnisberechnung
        row_sums = np.sum(accumulated_combined_influence_matrix, axis=1)
        sorted_indices = np.argsort(np.abs(row_sums))[::-1]

        current_changed_params = []
        if os.path.exists(path_parameters):
            with open(path_parameters, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith("Geändert:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            param_name = parts[1].strip()
                            current_changed_params.append(param_name)
                            
        rank, scaled_error = np.nan, np.nan
        if current_changed_params:
            ground_truth_param_name = current_changed_params[0]
            code_param_gt = reverse_mapping.get(ground_truth_param_name)
            if code_param_gt and code_param_gt in parameter_names_total:
                param_index_gt = parameter_names_total.index(code_param_gt)
                rank = list(sorted_indices).index(param_index_gt) + 1
                
                influence_gt = row_sums[param_index_gt]
                influence_top1 = row_sums[sorted_indices[0]]
                influence_range = np.max(row_sums) - np.min(row_sums)
                if influence_range > 1e-9:
                    scaled_error = abs(influence_top1 - influence_gt) / influence_range
        
        processing_time = time.time() - t0
        return (rank, scaled_error, processing_time, os.path.basename(case_path))

    except Exception as e:
        error_message = f"Fehler bei der Verarbeitung von {os.path.basename(case_path)}: {e}"
        return (np.nan, np.nan, 0, error_message)


if __name__ == "__main__":
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # ###########################################################################
    # ### ZENTRALE KONFIGURATION DER PFADE - BITTE HIER ANPASSEN               ###
    # ###########################################################################
    
    # Pfade werden nur von rank 0 gelesen und dann an alle verteilt.
    if rank == 0:
        # --- 1. Pfade zu den globalen Konfigurationsdateien ---
        
        # Pfad zur zentralen AML-Datei, welche die Systemtopologie beschreibt.
        path_aml_file = "/beegfs/home/m/m778332/masterarbeit/Code/Data/models/ModVA_Mixer_incl_SensorNamingConvention_reduced_V2.aml"

        # Pfad zur Excel-Datei mit den Bezeichnungen und Mappings.
        path_designations_file = "/beegfs/home/m/m778332/masterarbeit/Code/Data/models/ModVA_Designations.xlsx"
        
        # Pfad zum Verzeichnis, das ALLE Modus-Ordner enthält
        dir_dynamic_weights = "/beegfs/home/m/m778332/masterarbeit/Code/Data/mode_parquets_final_dask/weights"

        # --- 2. Pfad zum Hauptverzeichnis, das alle Testfall-Ordner enthält ---
        
        # Dies ist das rootverzeichnis, in dem die Ordner 'Testcase1', 'Testcase2' usw. liegen.
        dir_testcases_root = "/beegfs/home/m/m778332/masterarbeit/Code/Data/data_for_aroyyo"

        # --- 3. Namen der Dateien, die in JEDEM Testfall-Ordner erwartet werden ---
        
        # Diese Namen sind für alle Testfälle gleich und werden an die process_testcase Funktion übergeben.
        testcase_filenames = {
            "alarms":    "ModVA_deviation_adjusted.parquet",
            "xmv":       "XMV.parquet",
            "residuals": "ModVA_residual_adjusted.parquet",
            "parameters": "parameters.txt",
            "modi_df":    "modi_df.parquet"
        }

    # ###########################################################################
    # ### ENDE DER KONFIGURATION                                              ###
    # ###########################################################################
    
    init_data = None
    if rank == 0:
        print(f"--- Start der parallelen Verarbeitung mit {size} Prozessen ---")
        start_time_total = time.time()
        
        # Überprüfe, ob die Konfigurationspfade existieren
        for path in [path_aml_file, path_designations_file, dir_testcases_root]:
            if not os.path.exists(path):
                # Programm mit Fehlermeldung beenden, wenn wichtige Pfade nicht gefunden werden.
                print(f"FEHLER: Der konfigurierte Pfad '{path}' wurde nicht gefunden. Bitte die Konfiguration prüfen.")
                comm.Abort() # Beendet alle MPI-Prozesse
                
        all_mode_weights = load_dynamic_weights(dir_dynamic_weights)

        # Lade globale Daten
        wb = load_workbook(filename=path_designations_file)
        ws = wb.active
        d = {}
        for row in list(ws.rows)[1:]:
            if str(row[1].value) != "None" and str(row[2].value) != "None":
                d[row[0].value] = [str(c.value) for c in row[1:]]
        
        dList = createNameList(list(d.values()), [0, 1, 4])
        dNumbers = list(range(1, 9))
        reverse_mapping = {v: k for k, v in matching.items() if v != "none"}
        abort_time = 300
        
        # Erstelle Liste aller zu verarbeitenden Testfall-Pfade
        testcase_dir_list = [
            os.path.join(dir_testcases_root, folder)
            for folder in os.listdir(dir_testcases_root)
            if os.path.isdir(os.path.join(dir_testcases_root, folder))
        ]
        
        init_data = {
            "path_aml_file": path_aml_file,
            "dList": dList,
            "dNumbers": dNumbers,
            "reverse_mapping": reverse_mapping,
            "abort_time": abort_time,
            "testcase_dir_list": testcase_dir_list,
            "testcase_filenames": testcase_filenames,
            "all_mode_weights": all_mode_weights
        }
    
    # 2. Verteile die initialisierten Daten an alle Prozesse
    init_data = comm.bcast(init_data, root=0)
    
    # Jeder Prozess entpackt die Daten für sich
    path_aml_file = init_data["path_aml_file"]
    dList = init_data["dList"]
    dNumbers = init_data["dNumbers"]
    reverse_mapping = init_data["reverse_mapping"]
    abort_time = init_data["abort_time"]
    testcase_dir_list = init_data["testcase_dir_list"]
    testcase_filenames = init_data["testcase_filenames"]
    all_mode_weights = init_data["all_mode_weights"]
    
    my_cases_to_process = testcase_dir_list[rank::size]
    
    print(f"Prozess {rank}/{size} verarbeitet {len(my_cases_to_process)} Testfälle.")

    # 3. Parallele Verarbeitung
    local_results = []
    for case_path in my_cases_to_process:
        # Übergabe der Dateinamen-Konfiguration an die Funktion
        result = process_testcase(case_path, path_aml_file, dList, dNumbers, reverse_mapping, abort_time, testcase_filenames)
        if result:
            local_results.append(result)

    # 4. Sammeln der Ergebnisse
    all_results_nested = comm.gather(local_results, root=0)

    # 5. Finale Aggregation und Ausgabe (nur auf Master-Prozess)
    if rank == 0:
        print("\n--- Alle Prozesse beendet. Sammle und verarbeite Ergebnisse. ---")
        
        all_results = [item for sublist in all_results_nested for item in sublist]
        valid_ranks = [r[0] for r in all_results if r and not np.isnan(r[0])]
        valid_scaled_errors = [r[1] for r in all_results if r and not np.isnan(r[1])]
        
        total_time = time.time() - start_time_total
        print(f"\nGesamte Verarbeitungszeit: {total_time:.2f} Sekunden")
        print(f"Anzahl erfolgreich verarbeiteter Testfälle: {len(valid_ranks)}")
        
        failed_cases = [r[3] for r in all_results if r and np.isnan(r[0])]
        if failed_cases:
            print(f"\nFehler bei {len(failed_cases)} Testfällen:")
            for case_info in failed_cases:
                print(f"  - {case_info}")
                
        print("\n--- Overall Statistics ---")
        if valid_ranks:
            overall_avg_rank = sum(valid_ranks) / len(valid_ranks)
            print(f"Gesamtmittelwert der Ränge: {overall_avg_rank:.2f}")
        else:
            print("Keine gültigen Ränge für die Gesamtstatistik verfügbar.")

        if valid_scaled_errors:
            overall_avg_scaled_error = sum(valid_scaled_errors) / len(valid_scaled_errors)
            print(f"Durchschnittlicher skalierter absoluter Fehler (SAE): {overall_avg_scaled_error:.4f}")
        else:
            print("Keine gültigen skalierten Fehler für die Gesamtstatistik verfügbar.")