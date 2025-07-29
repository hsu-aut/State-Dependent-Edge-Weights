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


# Funktion, die einen einzelnen Parquet-Datei-Pfad verarbeitet
def process_single_parquet(parquet_path: Path, output_dir: Path):
    """
    Liest eine Parquet-Datei ein, baut df_wide, wandelt DBN in flaches LGBN um, 
    passt das LGBN an und berechnet Kantengewichte. Speichert df_flat und Kantengewichte als CSV.
    """
    file_stem = parquet_path.stem  # z.B. "mode_0_0_0_0_0_0"
    print(f"\n--- Verarbeite Datei: {file_stem}.parquet ---")

    # Rohdaten laden und vorbereiten
    df_raw = pd.read_parquet(parquet_path)
    df_raw = df_raw.set_index("time")
    df_raw.columns = [c.split(" - ")[0] for c in df_raw.columns]

    # Map Tag → Vid im Subgraphen
    tag_to_vid_sub = {v["Tag"]: v.index for v in sub.vs}

    # Sensor- und Parameter-Tags, die im Raw DataFrame vorkommen
    sensor_base_tags_in_model = sorted(list(set(
        tag for tag in df_raw.columns
        if tag in tag_to_vid_sub and tag_to_vid_sub[tag] in sensors
    )))
    param_base_tags_in_model_for_selection = sorted(list(set(
        tag for tag in df_raw.columns
        if tag in tag_to_vid_sub and tag_to_vid_sub[tag] in params
    )))
    param_derived_names_for_cols = [f"{tag}(param)" for tag in param_base_tags_in_model_for_selection]
    
    
    # --- BEGINN: Standardisierung der Rohdaten (df_raw) ---
    print("Beginne Standardisierung der Rohdaten...")
    sensor_scaler = StandardScaler()
    param_scaler = StandardScaler()

    # 2. Sensordaten skalieren
    if not sensor_base_tags_in_model:
        print("WARNUNG: Keine Sensor-Tags zum Skalieren gefunden.")
    else:
        # Stelle sicher, dass nur existierende Spalten ausgewählt werden, falls df_raw nach Filterung leer ist
        sensors_to_scale_cols = [col for col in sensor_base_tags_in_model if col in df_raw.columns]
        if sensors_to_scale_cols:
            sensors_to_scale_data = df_raw[sensors_to_scale_cols].copy()
            if not sensors_to_scale_data.empty:
                scaled_sensor_data = sensor_scaler.fit_transform(sensors_to_scale_data)
                df_scaled_sensors = pd.DataFrame(scaled_sensor_data,
                                                 columns=sensors_to_scale_cols,
                                                 index=sensors_to_scale_data.index)
                
                for col in sensors_to_scale_cols:
                    df_raw[col] = df_scaled_sensors[col]
                print("Sensordaten erfolgreich skaliert.")
            else:
                print("WARNUNG: Keine Daten in den ausgewählten Sensor-Spalten zum Skalieren.")
        else:
            print("WARNUNG: Keine übereinstimmenden Sensor-Spalten in df_raw zum Skalieren.")


    # 3. Parameterdaten skalieren
    if not param_base_tags_in_model_for_selection:
        print("WARNUNG: Keine Parameter-Tags zum Skalieren gefunden.")
    else:
        params_to_scale_cols = [col for col in param_base_tags_in_model_for_selection if col in df_raw.columns]
        if params_to_scale_cols:
            params_to_scale_data = df_raw[params_to_scale_cols].copy()
            if not params_to_scale_data.empty:
                scaled_param_data = param_scaler.fit_transform(params_to_scale_data)
                df_scaled_params = pd.DataFrame(scaled_param_data,
                                                columns=params_to_scale_cols,
                                                index=params_to_scale_data.index)

                for col in params_to_scale_cols:
                    df_raw[col] = df_scaled_params[col]
                print("Parameterdaten erfolgreich skaliert.")
            else:
                print("WARNUNG: Keine Daten in den ausgewählten Parameter-Spalten zum Skalieren.")
        else:
            print("WARNUNG: Keine übereinstimmenden Parameter-Spalten in df_raw zum Skalieren.")
    # --- ENDE: Standardisierung ---

    # --- df_wide Erstellung (inklusive duplizierter Parameter für Slice 1) ---
    # Sensor-Daten slice t0 und t1
    if not sensor_base_tags_in_model:
        print("WARNUNG: Keine Sensor-Tags für das Modell gefunden. df_s_t0 und df_s_t1 werden leer sein.")
        df_s_t0 = pd.DataFrame()
        df_s_t1 = pd.DataFrame()
    else:
        df_s_t0 = df_raw[sensor_base_tags_in_model].iloc[:-1].reset_index(drop=True)
        df_s_t1 = df_raw[sensor_base_tags_in_model].iloc[1:].reset_index(drop=True)
        idx_t0 = pd.MultiIndex.from_tuples(
            [(tag, 0) for tag in sensor_base_tags_in_model],
            names=["var", "time"]
        )
        idx_t1 = pd.MultiIndex.from_tuples(
            [(tag, 1) for tag in sensor_base_tags_in_model],
            names=["var", "time"]
        )
        if not df_s_t0.empty:
            df_s_t0.columns = idx_t0
        if not df_s_t1.empty:
            df_s_t1.columns = idx_t1

    # Parameter-Daten slice t0 und t1
    if not param_base_tags_in_model_for_selection:
        print("WARNUNG: Keine Parameter-Tags für das Modell gefunden. df_p_slice0 und df_p_slice1 werden leer sein.")
        df_p_slice0 = pd.DataFrame()
        df_p_slice1 = pd.DataFrame()
    else:
        # Slice 0 für Parameter
        df_p_selected_slice0 = df_raw[param_base_tags_in_model_for_selection].iloc[:-1].reset_index(drop=True)
        idx_p_slice0 = pd.MultiIndex.from_tuples(
            [(name, 0) for name in param_derived_names_for_cols],
            names=["var", "time"]
        )
        df_p_selected_slice0.columns = idx_p_slice0
        df_p_slice0 = df_p_selected_slice0

        # Slice 1 für Parameter (identisch mit Slice0, da shift um 1)
        df_p_selected_slice1 = df_raw[param_base_tags_in_model_for_selection].iloc[:-1].reset_index(drop=True)
        idx_p_slice1 = pd.MultiIndex.from_tuples(
            [(name, 1) for name in param_derived_names_for_cols],
            names=["var", "time"]
        )
        df_p_selected_slice1.columns = idx_p_slice1
        df_p_slice1 = df_p_selected_slice1

    # Concatenate zu df_wide
    dfs_to_concat = []
    if not df_s_t0.empty:
        dfs_to_concat.append(df_s_t0)
    if not df_s_t1.empty:
        dfs_to_concat.append(df_s_t1)
    if not df_p_slice0.empty:
        dfs_to_concat.append(df_p_slice0)
    if not df_p_slice1.empty:
        dfs_to_concat.append(df_p_slice1)

    if not dfs_to_concat:
        print("FEHLER: Keine Daten zum Zusammenführen für df_wide vorhanden. Überspringe Datei.")
        return

    df_wide = pd.concat(dfs_to_concat, axis=1)
    df_wide = df_wide.loc[:, ~df_wide.columns.duplicated()]

    # --- BEGINN: DBN → flaches LGBN umwandeln und fitten ---
    print("Beginne Abwicklung des DBN zu einem flachen LGBN...")
    flat_edges = []
    node_to_flat_map = {}
    flat_to_node_map = {}

    if not model.nodes():
        print("FEHLER: Das DBN-Modell hat keine Knoten. Überspringe Datei.")
        return

    # Mapping DynamicNode → flacher Name
    for dn_node in model.nodes():
        try:
            var_name = dn_node.node
            time_slice = dn_node.time_slice
        except AttributeError:
            print(f"FEHLER: DynamicNode hat kein .node/.time_slice. Überspringe Datei.")
            return

        flat_name = f"{var_name}_{time_slice}"
        node_to_flat_map[(var_name, time_slice)] = flat_name
        flat_to_node_map[flat_name] = (var_name, time_slice)

    # DBN-Kanten in flache Kanten übersetzen
    for u_dn, v_dn in model.edges():
        try:
            u_var_name, u_slice = u_dn.node, u_dn.time_slice
            v_var_name, v_slice = v_dn.node, v_dn.time_slice
        except AttributeError:
            print(f"WARNUNG: Kante {u_dn} → {v_dn} hat ungültige Attribute. Überspringe Kante.")
            continue

        u_flat = node_to_flat_map.get((u_var_name, u_slice))
        v_flat = node_to_flat_map.get((v_var_name, v_slice))
        if u_flat and v_flat:
            flat_edges.append((u_flat, v_flat))
        else:
            print(f"WARNUNG: Konnte DynamicNode → flachen Namen nicht mappen: ({u_var_name},{u_slice}) → ({v_var_name},{v_slice})")

    # Daten für flaches DataFrame sammeln
    df_flat_data_dict = {}
    for col_tuple, series_data in df_wide.items():
        flat_col_name = node_to_flat_map.get(col_tuple)
        if flat_col_name:
            df_flat_data_dict[flat_col_name] = series_data

    if not df_flat_data_dict:
        print("FEHLER: Keine Daten für df_flat gesammelt. Überspringe Datei.")
        return

    df_flat = pd.DataFrame(df_flat_data_dict, index=df_wide.index)

    # Zielverzeichnis für diese einzelne Datei
    out_subdir = output_dir / file_stem
    out_subdir.mkdir(parents=True, exist_ok=True)

    # Speichere df_flat als CSV
    df_flat_path = out_subdir / f"df_flat_{file_stem}.csv"
    df_flat.to_csv(df_flat_path, index=True, sep=';', decimal=',')
    print(f"df_flat gespeichert: {df_flat_path}")

    # Erstelle das flache LGBN-Modell und fitte
    lg_model = LinearGaussianBayesianNetwork(flat_edges)

    model_was_fitted = False
    print("Versuche, das LGBN-Modell zu fitten...")
    if not df_flat.empty and lg_model.nodes():
        try:
            lg_model.fit(df_flat)
            print("LGB-Modell-Fitting erfolgreich.")
            model_was_fitted = True
        except Exception as e:
            print(f"FEHLER beim LGBN-Fitting: {e}")
            import traceback
            traceback.print_exc()
    else:
        if df_flat.empty:
            print("LGBN-Fitting nicht möglich: df_flat ist leer.")
        if not lg_model.nodes():
            print("LGBN-Fitting nicht möglich: lg_model hat keine Knoten.")

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

            # Standardabweichung des Kindknotens
            child_std_dev = -1.0
            if hasattr(cpd, "std"):
                child_std_dev = cpd.std
            elif hasattr(cpd, "sigma_sq") and cpd.sigma_sq >= 0:
                child_std_dev = np.sqrt(cpd.sigma_sq)
            if child_std_dev < 0:
                print(f"WARNUNG: Keine gültige std_dev für {child_node_flat}. Überspringe CPD.")
                continue
            child_noise_variance = child_std_dev ** 2

            # Elternknoten-Liste für dieses CPD
            if hasattr(cpd, "evidence") and cpd.evidence:
                parent_nodes_flat = cpd.evidence
            elif hasattr(cpd, "variables") and len(cpd.variables) > 1:
                parent_nodes_flat = cpd.variables[1:]
            else:
                parent_nodes_flat = []

            if not parent_nodes_flat:
                continue  # Kein Parent → überspringen

            if not hasattr(cpd, "beta") or len(cpd.beta) != len(parent_nodes_flat) + 1:
                print(f"WARNUNG: Ungültige Beta-Koeffizienten für CPD von {child_node_flat}. Überspringe.")
                continue

            # Für jeden Elternknoten: KL-Divergenz berechnen
            for i, parent_flat in enumerate(parent_nodes_flat):
                beta_ji = cpd.beta[i + 1]

                # Marginale Varianz von Xi
                var_Xi_marginal = node_variances.get(parent_flat, 0.0)

                # Berechne Var(Xi | Z) über lineare Regression, falls mehrere Eltern
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
                else:
                    # Entweder keine Ko-Eltern oder fehlende Spalten → bleibe bei marginal
                    var_Xi_given_Z = var_Xi_marginal

                # KL-Divergenz mit marginaler Varianz
                numerator_marginal = (beta_ji**2) * var_Xi_marginal
                if child_noise_variance < 1e-30:
                    kl_marg = np.inf if numerator_marginal > 1e-30 else 0.0
                else:
                    term_m = 1 + (numerator_marginal / child_noise_variance)
                    if term_m < 1e-9:
                        kl_marg = 0.0
                    elif np.isinf(term_m):
                        kl_marg = np.inf
                    else:
                        kl_marg = 0.5 * np.log(term_m)

                # KL-Divergenz mit bedingter Varianz
                numerator_cond = (beta_ji**2) * var_Xi_given_Z
                if child_noise_variance < 1e-30:
                    kl_cond = np.inf if numerator_cond > 1e-30 else 0.0
                else:
                    term_c = 1 + (numerator_cond / child_noise_variance)
                    if term_c < 1e-9:
                        kl_cond = 0.0
                    elif np.isinf(term_c):
                        kl_cond = np.inf
                    else:
                        kl_cond = 0.5 * np.log(term_c)

                # Originale Edge-ID (sofern verfügbar)
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

    # Speichere Kantengewichte, wenn welche berechnet wurden
    if edge_weights_data:
        df_edge_weights = pd.DataFrame(edge_weights_data)
        edge_weights_path = out_subdir / f"kantengewichte_{file_stem}.csv"
        df_edge_weights.to_csv(edge_weights_path, index=False, sep=';', decimal=',')
        print(f"Kantengewichte gespeichert: {edge_weights_path}")
    else:
        print("Keine Kantengewichte zum Speichern.")


if __name__ == "__main__":
    # Ordner, in dem sich alle Parquet-Dateien befinden
    parquet_folder = Path(r"/beegfs/home/m/m778332/masterarbeit/Code/Data/mode_parquets_final_dask")
    # Ordner, in dem die Ergebnisse abgelegt werden sollen (für jede Parquet-Datei wird ein Unterordner angelegt)
    output_folder = parquet_folder / "weights"
    output_folder.mkdir(parents=True, exist_ok=True)

    # Iteriere über alle .parquet-Dateien im Verzeichnis
    parquet_files = sorted(parquet_folder.glob("*.parquet"))
    if not parquet_files:
        print(f"FEHLER: Keine Parquet-Dateien in '{parquet_folder}' gefunden.")
    else:
        for pq_file in parquet_files:
            process_single_parquet(pq_file, output_folder)