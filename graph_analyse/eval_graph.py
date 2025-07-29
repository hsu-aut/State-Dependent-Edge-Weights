import os
import pandas as pd
import numpy as np
from dbn_constructer import DBNConverter
from graph_copy_for_dbn import IGraphConverter
import Arroyo_DCDG_PLUT as Arroyo_DCDG_PLUT
import GRAPH_CONFIG as GRAPH_CONFIG
from pgmpy.models import LinearGaussianBayesianNetwork
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from pathlib import Path
import argparse
import gc

# 1) AML laden & DBN/Graph-Setup (nur einmal)
aml_file = GRAPH_CONFIG.AML_FILE_PATH
dcdg = Arroyo_DCDG_PLUT.DCDG_Class()
dcdg.generate_graphfromAML(aml_file)
converter = IGraphConverter(dcdg)

# Sub-Graph ohne 'hierarch'-Knoten holen
sub, vid_map_sub, eid_map_sub = converter.get_filtered_subgraph_with_mapping(
    "hierarch", True
)

# Knoten nach Typ aufteilen
param_carrier_list = ["Height", "Area", "Diameter", "Roughness", "HDiff", "PDropNom", "Rotational_Speed", "MFNominal"]
params, sensors = converter.split_nodes_by_carrier(sub, param_carrier_list)

# DBN-Converter erzeugen und DBN bauen
dbn_converter = DBNConverter(sub, vid_map_sub, eid_map_sub, converter)
model, dbn_edge_to_orig_eid_map = dbn_converter.build(sensors, params)


def process_single_parquet(parquet_path: Path, output_dir: Path):
    """
    Liest eine Parquet-Datei ein und verarbeitet sie "Out-of-Core" mit NumPy Memmap,
    um den RAM-Bedarf zu minimieren.
    """
    file_stem = parquet_path.stem
    print(f"\n--- Verarbeite Datei: {file_stem}.parquet ---")

    # Temporärer Dateiname für das Memmap-Array
    memmap_filename = f'temp_flat_array_{file_stem}.mmap'
    
    # Variablen für den finally-Block vor dem try-Block deklarieren
    df_flat = None
    flat_array_on_disk = None

    try:
        # 1. Rohdaten laden und vorbereiten
        df_raw = pd.read_parquet(parquet_path)
        
        float64_cols = list(df_raw.select_dtypes(include='float64'))
        if float64_cols:
            df_raw[float64_cols] = df_raw[float64_cols].astype('float32')
            print(f"Speicheroptimierung: {len(float64_cols)} Spalten zu float32 konvertiert.")

        df_raw = df_raw.set_index("time")
        df_raw.columns = [c.split(" - ")[0] for c in df_raw.columns]

        # Sensor- und Parameter-Tags identifizieren
        tag_to_vid_sub = {v["Tag"]: v.index for v in sub.vs}
        sensor_base_tags_in_model = sorted([tag for tag in df_raw.columns if tag in tag_to_vid_sub and tag_to_vid_sub[tag] in sensors])
        param_base_tags_in_model_for_selection = sorted([tag for tag in df_raw.columns if tag in tag_to_vid_sub and tag_to_vid_sub[tag] in params])

        # 2. Daten skalieren (operiert auf df_raw)
        print("Beginne Standardisierung der Rohdaten...")
        if sensor_base_tags_in_model:
            df_raw[sensor_base_tags_in_model] = StandardScaler().fit_transform(df_raw[sensor_base_tags_in_model])
            print("Sensordaten erfolgreich skaliert.")
        if param_base_tags_in_model_for_selection:
            df_raw[param_base_tags_in_model_for_selection] = StandardScaler().fit_transform(df_raw[param_base_tags_in_model_for_selection])
            print("Parameterdaten erfolgreich skaliert.")

        # =================================================================
        # === START: AUFBAU VON df_flat ÜBER NUMPY MEMMAP (OUT-OF-CORE) ===
        # =================================================================
        
        print("Beginne den Aufbau von df_flat über ein NumPy-Memmap auf der Festplatte...")
        
        # Metadaten für das flache Array vorbereiten
        num_rows_flat = len(df_raw) - 1
        sensor_cols = [f"{tag}_{s}" for tag in sensor_base_tags_in_model for s in ('0', '1')]
        param_derived_names = [f"{tag}(param)" for tag in param_base_tags_in_model_for_selection]
        param_cols = [f"{name}_{s}" for name in param_derived_names for s in ('0', '1')]
        final_column_names = sensor_cols + param_cols
        num_cols_flat = len(final_column_names)
        
        # Leere Memmap-Datei auf der Festplatte erstellen
        print(f"Erstelle temporäre Memmap-Datei '{memmap_filename}' mit Shape ({num_rows_flat}, {num_cols_flat})...")
        flat_array_on_disk = np.memmap(memmap_filename, dtype='float32', mode='w+', shape=(num_rows_flat, num_cols_flat))
        
        # Memmap-Array Spalte für Spalte füllen
        current_col_idx = 0
        for tag in sensor_base_tags_in_model:
            flat_array_on_disk[:, current_col_idx] = df_raw[tag].iloc[:-1].values
            current_col_idx += 1
            flat_array_on_disk[:, current_col_idx] = df_raw[tag].iloc[1:].values
            current_col_idx += 1
        print(f"{len(sensor_base_tags_in_model)*2} Sensor-Spalten in Memmap-Datei geschrieben.")

        for tag in param_base_tags_in_model_for_selection:
            param_val = df_raw[tag].iloc[0]
            flat_array_on_disk[:, current_col_idx] = param_val
            current_col_idx += 1
            flat_array_on_disk[:, current_col_idx] = param_val
            current_col_idx += 1
        print(f"{len(param_base_tags_in_model_for_selection)*2} Parameter-Spalten in Memmap-Datei geschrieben.")
            
        # df_raw wird nicht mehr benötigt -> Speicher freigeben
        print("Gebe Speicher von df_raw frei...")
        del df_raw
        gc.collect()

        # Finalen DataFrame aus dem Memmap-Array erstellen
        print("Erstelle finalen df_flat aus der Memmap-Datei...")
        df_flat = pd.DataFrame(flat_array_on_disk, columns=final_column_names)
        print("df_flat erfolgreich erstellt.")
        
        # ===============================================================
        # === ENDE: AUFBAU ÜBER NUMPY MEMMAP --- ###
        # ===============================================================

        # 3. Modell fitten und Kantengewichte berechnen
        print("Beginne Abwicklung des DBN zu einem flachen LGBN...")
        
        # DBN-Kanten in "flache" Kantennamen für das LGBN umwandeln
        flat_edges = []
        node_to_flat_map = {}
        flat_to_node_map = {}

        for dn_node in model.nodes():
            var_name, time_slice = dn_node.node, dn_node.time_slice
            flat_name = f"{var_name}_{time_slice}"
            node_to_flat_map[(var_name, time_slice)] = flat_name
            flat_to_node_map[flat_name] = (var_name, time_slice)

        for u_dn, v_dn in model.edges():
            u_flat = node_to_flat_map.get((u_dn.node, u_dn.time_slice))
            v_flat = node_to_flat_map.get((v_dn.node, v_dn.time_slice))
            
            if u_flat in df_flat.columns and v_flat in df_flat.columns:
                flat_edges.append((u_flat, v_flat))

        if not flat_edges:
            print("WARNUNG: Keine gültigen Kanten für das LGBN-Modell nach Filterung gefunden. Breche ab.")
            # Die Funktion hier verlassen, damit der finally-Block ausgeführt wird
            return

        # Zielverzeichnis für diese einzelne Datei erstellen
        out_subdir = output_dir / file_stem
        out_subdir.mkdir(parents=True, exist_ok=True)
            
        # Erstelle das flache LGBN-Modell und fitte
        lg_model = LinearGaussianBayesianNetwork(flat_edges)
        
        model_was_fitted = False
        print("Versuche, das LGBN-Modell zu fitten...")
        if not df_flat.empty:
            try:
                lg_model.fit(df_flat)
                print("LGB-Modell-Fitting erfolgreich.")
                model_was_fitted = True
            except Exception as e:
                print(f"FEHLER beim LGBN-Fitting: {e}")
                import traceback
                traceback.print_exc()

        # --- BEGINN: Berechnung der Kantengewichte mittels KL-Divergenz ---
        print("Beginne Berechnung der Kantengewichte...")
        edge_weights_data = []
        node_variances = {}

        # 1. Marginale Varianzen aller Knoten berechnen (falls modelliert)
        if model_was_fitted and not df_flat.empty:
            for node_name in lg_model.nodes():
                if node_name in df_flat.columns:
                    var_val = df_flat[node_name].var()
                    node_variances[node_name] = var_val if not pd.isna(var_val) else 0.0
                else:
                    node_variances[node_name] = 0.0
        else:
            print("INFO: Kein erfolgreiches Modell-Fitting – überspringe Varianz-Berechnung.")

        # 2. Über alle CPDs im LGBN iterieren (falls gefittet)
        if model_was_fitted and hasattr(lg_model, "get_cpds") and lg_model.get_cpds():
            for cpd in lg_model.get_cpds():
                child_node_flat = cpd.variable
                child_std_dev = -1.0
                if hasattr(cpd, "std"):
                    child_std_dev = cpd.std
                elif hasattr(cpd, "sigma_sq") and cpd.sigma_sq >= 0:
                    child_std_dev = np.sqrt(cpd.sigma_sq)
                if child_std_dev < 0:
                    print(f"WARNUNG: Keine gültige std_dev für {child_node_flat}. Überspringe CPD.")
                    continue
                child_noise_variance = child_std_dev ** 2

                if hasattr(cpd, "evidence") and cpd.evidence:
                    parent_nodes_flat = cpd.evidence
                elif hasattr(cpd, "variables") and len(cpd.variables) > 1:
                    parent_nodes_flat = cpd.variables[1:]
                else:
                    parent_nodes_flat = []

                if not parent_nodes_flat:
                    continue

                if not hasattr(cpd, "beta") or len(cpd.beta) != len(parent_nodes_flat) + 1:
                    print(f"WARNUNG: Ungültige Beta-Koeffizienten für CPD von {child_node_flat}. Überspringe.")
                    continue

                for i, parent_flat in enumerate(parent_nodes_flat):
                    beta_ji = cpd.beta[i + 1]
                    var_Xi_marginal = node_variances.get(parent_flat, 0.0)
                    var_Xi_given_Z = var_Xi_marginal
                    co_parents = [p for p in parent_nodes_flat if p != parent_flat]
                    if co_parents and parent_flat in df_flat.columns and all(z in df_flat.columns for z in co_parents):
                        try:
                            X_i = df_flat[parent_flat]
                            Z = df_flat[co_parents]
                            if not Z.empty and Z.shape[0] >= max(2, Z.shape[1] + 1) and not Z.isnull().values.any() and (Z.nunique() != 1).all():
                                lr = LinearRegression().fit(Z, X_i)
                                resid = X_i - lr.predict(Z)
                                var_Xi_given_Z = np.var(resid, ddof=1)
                                if var_Xi_given_Z < 0:
                                    var_Xi_given_Z = var_Xi_marginal
                        except Exception as e_reg:
                            print(f"WARNUNG: Regression für Var({parent_flat}|Z) fehlgeschlagen: {e_reg}. Verwende marginale Varianz.")
                            var_Xi_given_Z = var_Xi_marginal
                    
                    numerator_marginal = (beta_ji**2) * var_Xi_marginal
                    if child_noise_variance < 1e-30:
                        kl_marg = np.inf if numerator_marginal > 1e-30 else 0.0
                    else:
                        term_m = 1 + (numerator_marginal / child_noise_variance)
                        if term_m < 1e-9: kl_marg = 0.0
                        elif np.isinf(term_m): kl_marg = np.inf
                        else: kl_marg = 0.5 * np.log(term_m)

                    numerator_cond = (beta_ji**2) * var_Xi_given_Z
                    if child_noise_variance < 1e-30:
                        kl_cond = np.inf if numerator_cond > 1e-30 else 0.0
                    else:
                        term_c = 1 + (numerator_cond / child_noise_variance)
                        if term_c < 1e-9: kl_cond = 0.0
                        elif np.isinf(term_c): kl_cond = np.inf
                        else: kl_cond = 0.5 * np.log(term_c)

                    orig_edge_id = None
                    dbn_par = flat_to_node_map.get(parent_flat)
                    dbn_child = flat_to_node_map.get(child_node_flat)
                    if dbn_par and dbn_child:
                        orig_edge_id = dbn_edge_to_orig_eid_map.get((dbn_par, dbn_child))

                    edge_weights_data.append({
                        "Elternknoten": parent_flat,
                        "Kindknoten": child_node_flat,
                        "Original_Edge_ID": orig_edge_id if orig_edge_id is not None else "N/A",
                        "Beta_Absolut": abs(beta_ji),
                        "Var_Xi_Marginal": var_Xi_marginal,
                        "Var_Xi_Given_Z": var_Xi_given_Z,
                        "MI_mit_Var_Xi": kl_marg,
                        "MI_mit_Var_Xi_given_Z": kl_cond
                    })

        elif model_was_fitted:
            print("WARNUNG: LGBN hat nach dem Fit keine CPDs. Keine Gewichte berechnet.")
        else:
            print("INFO: LGBN wurde nicht gefittet. Keine Gewichte berechnet.")

        if edge_weights_data:
            df_edge_weights = pd.DataFrame(edge_weights_data)
            edge_weights_path = out_subdir / f"kantengewichte_{file_stem}.csv"
            df_edge_weights.to_csv(edge_weights_path, index=False, sep=';', decimal=',')
            print(f"Kantengewichte gespeichert: {edge_weights_path}")
        else:
            print("Keine Kantengewichte zum Speichern.")
            
    finally:
        # 4. Aufräumen: Temporäre Memmap-Datei wird immer gelöscht
        # Dieser Block wird auch dann ausgeführt, wenn im try-Block ein Fehler auftritt.
        # Wichtig, um die Festplatte nicht mit temporären Dateien zu füllen.
        if df_flat is not None: del df_flat
        if flat_array_on_disk is not None: del flat_array_on_disk
        gc.collect()
        
        if os.path.exists(memmap_filename):
            try:
                os.remove(memmap_filename)
                print(f"Temporäre Memmap-Datei '{memmap_filename}' erfolgreich gelöscht.")
            except OSError as e:
                print(f"WARNUNG: Fehler beim Löschen der Memmap-Datei: {e}")

if __name__ == "__main__":
    # Ordner, in dem sich alle Parquet-Dateien befinden
    parquet_folder = Path(r"/beegfs/home/m/m778332/masterarbeit/Code/Data/mode_parquets_final_dask")
    # Ordner, in dem die Ergebnisse abgelegt werden sollen
    output_folder = parquet_folder / "weights"
    output_folder.mkdir(parents=True, exist_ok=True)

    # Iteriere über alle .parquet-Dateien im Verzeichnis
    parquet_files = sorted(parquet_folder.glob("*.parquet"))
    if not parquet_files:
        print(f"FEHLER: Keine Parquet-Dateien in '{parquet_folder}' gefunden.")
    else:
        for pq_file in parquet_files:
            process_single_parquet(pq_file, output_folder)