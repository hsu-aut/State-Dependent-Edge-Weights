import os
import argparse
import pandas as pd
import dataset_comparison as dc
from pathlib import Path
import shutil
from typing import Tuple
import multiprocessing


# --- Globale Konfigurationen und Konstanten ---

# Spalten, die bei Sensor-Daten behalten werden sollen
sensor_columns_to_keep = [
    'tank_B201.level',
    'pipe_B201_V201.port_b.p',
    'tank_B202.level',
    'pipe_B202_V202.port_b.p',
    'tank_B203.level',
    'pipe_B203_V203.port_b.p',
    'FI201.V_flow',
    'tank_B204.level',
    'pipe_B204_P202.port_b.p',
    'pipe_V207_Tee4.port_b.m_flow'
]

# Spalten, die bei Aktuator-Daten behalten werden sollen
actuator_columns_to_keep = [
    'V201.opening',
    'V202.opening',
    'V203.opening',
    'P201.N',
    'P202.N',
    'V206.opening',
    'V205.opening',
    'V204.opening'
]

# Spaltennamen für modi_df
ACTUATORS_FOR_MODI = [
    "V201.opening",
    "V202.opening",
    "V203.opening",
    "V206.opening",
    "V205.opening",
    "V204.opening",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parallele Verarbeitung aller Testfall-Ordner"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Hauptordner mit allen Testfall-Unterordnern (jeweils eine .parquet-Datei und evtl. .txt)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Basis-Ausgabeordner, in dem pro Testfall jeweils ein Unterordner mit den Ergebnissen angelegt wird"
    )
    parser.add_argument(
        "--original-csv",
        type=Path,
        required=True,
        help="Pfad zur Original-CSV (Referenzdaten), z. B. ModVA_online_stable_res_original.csv"
    )
    return parser.parse_args()


def load_files_from_testcase_folder(testcase_data_folder: Path) -> Tuple[pd.DataFrame, Path]:
    """
    Lädt eine Parquet-Datei aus testcase_data_folder.
    Gibt das geladene DataFrame und den Pfad zum testcase_data_folder zurück.
    Stellt sicher, dass genau eine .parquet-Datei im Ordner existiert.
    """
    if not testcase_data_folder.is_dir():
        raise FileNotFoundError(f"Der angegebene Testfall-Datenordner existiert nicht oder ist kein Verzeichnis: {testcase_data_folder}")

    parquet_files = list(testcase_data_folder.glob('*.parquet'))
    if not parquet_files:
        raise FileNotFoundError(f"Keine .parquet-Datei im Ordner gefunden: {testcase_data_folder}")
    if len(parquet_files) > 1:
        raise ValueError(f"Erwartet wurde genau eine .parquet-Datei in {testcase_data_folder}, gefunden: {len(parquet_files)} ({[p.name for p in parquet_files]})")

    loaded_df = pd.read_parquet(parquet_files[0])
    return loaded_df, testcase_data_folder


def process_test_case(args_tuple: Tuple[Path, Path, Path]) -> Tuple[int, int]:
    """
    Bearbeitet einen einzelnen Testfall-Ordner (Parquet + TXT kopieren, Vergleiche, Harmonisierung, ...)
    Gibt (1, 0) zurück, wenn erfolgreich verarbeitet, oder (0, 1), wenn übersprungen (Fehler).
    """
    test_case_container_path, output_base_folder, df_original_path_csv = args_tuple
    test_case_name = test_case_container_path.name

    print(f"\n--- ({multiprocessing.current_process().name}) Bearbeite Testfall-Ordner: '{test_case_name}' ---")

    # 1) Original-CSV laden (Referenzdaten)
    try:
        df_original_loaded = pd.read_csv(df_original_path_csv)
    except FileNotFoundError:
        print(f"FEHLER: Originaldatei (Referenz) '{df_original_path_csv}' nicht gefunden. Breche Verarbeitung von '{test_case_name}' ab.")
        return (0, 1)
    except Exception as e:
        print(f"FEHLER beim Lesen der Originaldatei (Referenz) '{df_original_path_csv}' für '{test_case_name}': {e}. Überspringe.")
        return (0, 1)

    # 2) Parquet-Datei aus dem Testfall-Ordner laden
    try:
        df_faulty, data_files_folder_path = load_files_from_testcase_folder(test_case_container_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"FEHLER beim Laden der Parquet-Datei für '{test_case_name}': {e}. Überspringe diesen Testfall.")
        return (0, 1)

    # 3) Vorverarbeitung der Originaldaten: 'level'-Spalten differenzieren
    df_original_for_processing = df_original_loaded.copy()
    df_copy_orig = df_original_for_processing.copy()
    for column in df_copy_orig.columns:
        if 'level' in column:
            df_copy_orig[column] = df_copy_orig[column] - df_copy_orig[column].shift(-1)
    df_original_for_processing = df_copy_orig

    # 4) Vorverarbeitung der fehlerhaften Daten für 'level'-Berechnung
    df_faulty_for_level_calc = df_faulty.copy()
    for column in df_faulty_for_level_calc.columns:
        if 'level' in column:
            df_faulty_for_level_calc[column] = df_faulty_for_level_calc[column] - df_faulty_for_level_calc[column].shift(-1)
    df_faulty_processed_for_comparison = df_faulty_for_level_calc.copy()

    # 5) Sicherstellen, dass die Zeitspalte existiert
    name_of_time_column = 'time'
    if name_of_time_column not in df_original_for_processing.columns or \
       name_of_time_column not in df_faulty_processed_for_comparison.columns:
        print(f"FEHLER: Zeitspalte '{name_of_time_column}' nicht in einem der DataFrames für '{test_case_name}' gefunden. Überspringe.")
        return (0, 1)

    # 6) Zeit konvertieren, harmonisieren und vergleichen
    try:
        df_original_conv = dc.convert_time_of_df(df_original_for_processing.copy(), name_of_time_column)
        df_faulty_conv = dc.convert_time_of_df(df_faulty_processed_for_comparison.copy(), name_of_time_column)

        df_original_harm, df_faulty_harm = dc.harmonize_time(
            df_original_conv, df_faulty_conv,
            name_of_time_column, name_of_time_column,
            '1s'
        )
        df_residual, df_deviation = dc.compare_dataframes(df_original_harm, df_faulty_harm, threshold=0.05)
    except Exception as e:
        print(f"FEHLER während der Zeit-/Vergleichs-Verarbeitung für '{test_case_name}': {e}. Überspringe.")
        return (0, 1)

    # 7) Aktuator-Daten normalisieren
    actuator_df = df_original_harm[actuator_columns_to_keep].copy()
    actuator_df = actuator_df.round(3)
    actuator_max_value = actuator_df.max()
    actuator_max_value[actuator_max_value == 0] = 1
    actuator_df = (actuator_df / actuator_max_value) * 100

    # 8) Sensorabweichung und -residual erstellen
    sensor_deviation_df = df_deviation[sensor_columns_to_keep].copy()
    sensor_residual_df = df_residual[sensor_columns_to_keep].copy()

    # 9) Erstellen und Speichern von modi_df (falls relevanten Spalten vorhanden)
    modi_df_source_columns = [col for col in ACTUATORS_FOR_MODI if col in df_faulty.columns]
    modi_df = None
    if modi_df_source_columns:
        modi_df_intermediate = df_faulty[modi_df_source_columns].copy()
        if df_original_harm is not None:
            modi_df = modi_df_intermediate.reindex(df_original_harm.index)
            print(f"INFO: modi_df mit Spalten {modi_df_source_columns} für Testfall '{test_case_name}' erstellt.")
            modi_df = modi_df.reset_index(drop=True)
        else:
            print(f"FEHLER: df_original_harm nicht verfügbar für Reindizierung von modi_df für '{test_case_name}'.")
    else:
        print(f"INFO: Keine Spalten aus ACTUATORS_FOR_MODI im df_faulty für '{test_case_name}' gefunden. modi_df wird nicht erstellt.")

    # 10) Ausgabeordner für diesen Testfall anlegen
    output_testcase_specific_folder = output_base_folder / test_case_name
    output_testcase_specific_folder.mkdir(parents=True, exist_ok=True)

    # 11) Speichere modi_df, falls vorhanden
    if modi_df is not None:
        try:
            modi_df.to_parquet(output_testcase_specific_folder / 'modi_df.parquet', index=False)
            print(f"modi_df.parquet für Testfall '{test_case_name}' gespeichert.")
        except Exception as e:
            print(f"FEHLER beim Speichern von modi_df.parquet für '{test_case_name}': {e}")

    # 12) Index zurücksetzen für andere DataFrames
    sensor_deviation_df = sensor_deviation_df.reset_index(drop=True)
    sensor_residual_df = sensor_residual_df.reset_index(drop=True)
    actuator_df = actuator_df.reset_index(drop=True)

    # 13) Speichern der verarbeiteten Parquet-Dateien (Deviation, Residual, XMV)
    try:
        sensor_deviation_df.to_parquet(
            output_testcase_specific_folder / 'ModVA_deviation_adjusted.parquet',
            index=False
        )
        sensor_residual_df.to_parquet(
            output_testcase_specific_folder / 'ModVA_residual_adjusted.parquet',
            index=False
        )
        actuator_df.to_parquet(
            output_testcase_specific_folder / 'XMV.parquet',
            index=False
        )
        print(f"Verarbeitete DataFrames (deviation, residual, XMV) für '{test_case_name}' gespeichert.")
    except Exception as e:
        print(f"FEHLER beim Speichern der DataFrames (deviation, residual, XMV) für '{test_case_name}': {e}")

    # 14) Kopiere .txt-Datei (falls vorhanden)
    if data_files_folder_path:
        txt_files_in_data_dir = list(data_files_folder_path.glob('*.txt'))
        if txt_files_in_data_dir:
            if len(txt_files_in_data_dir) > 1:
                print(f"WARNUNG: Mehrere .txt-Dateien im Ordner '{data_files_folder_path.name}' für '{test_case_name}' gefunden. Kopiere die erste: {txt_files_in_data_dir[0].name}")
            source_txt_path = txt_files_in_data_dir[0]
            destination_txt_path = output_testcase_specific_folder / source_txt_path.name
            try:
                shutil.copy2(source_txt_path, destination_txt_path)
                print(f"Textdatei '{source_txt_path.name}' nach '{destination_txt_path}' kopiert.")
            except Exception as e:
                print(f"FEHLER beim Kopieren der Textdatei '{source_txt_path.name}' für '{test_case_name}': {e}")

    # Erfolgreich abgeschlossen
    return (1, 0)


def main():
    """
    Hauptfunktion, die alle Testfall-Ordner parallel verarbeitet.
    """
    args = parse_args()
    HAUPTORDNER_PARQUET_INPUTS: Path = args.input_dir
    output_base_folder: Path = args.output_dir
    df_original_path_csv: Path = args.original_csv

    # Erstelle Ausgabe-Basisordner, falls er noch nicht existiert
    output_base_folder.mkdir(parents=True, exist_ok=True)

    if not HAUPTORDNER_PARQUET_INPUTS.is_dir():
        print(f"FEHLER: Der Hauptordner für Parquet-Inputs '{HAUPTORDNER_PARQUET_INPUTS}' wurde nicht gefunden oder ist kein Verzeichnis.")
        return

    # Liste aller Unterordner (Testfall-Container) ermitteln
    test_case_paths = [
        item_path
        for item_path in HAUPTORDNER_PARQUET_INPUTS.iterdir()
        if item_path.is_dir()
    ]

    if not test_case_paths:
        print(f"INFO: Keine Unterordner im Hauptordner '{HAUPTORDNER_PARQUET_INPUTS}' gefunden. Nichts zu tun.")
        return

    # Anzahl der CPUs aus SLURM_CPUS_PER_TASK oder CPU-Anzahl des Systems übernehmen
    try:
        cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", multiprocessing.cpu_count()))
    except ValueError:
        cpus = multiprocessing.cpu_count()

    print(f"Starte parallele Verarbeitung von {len(test_case_paths)} Testfall-Ordnern "
          f"mit {cpus} Worker-Prozessen im '{multiprocessing.current_process().name}'...")

    # Bereite eine Liste von Argument-Tuples für jeden Testfall vor
    # Jeder Eintrag: (Path zu Testfall-Ordner, Basis-Ausgabeordner, Pfad zur Original-CSV)
    args_for_pool = [
        (tc_path, output_base_folder, df_original_path_csv)
        for tc_path in test_case_paths
    ]

    # Paralleles Mapping: process_test_case mit genau `cpus` parallelen Prozessen
    with multiprocessing.Pool(processes=cpus) as pool:
        results = pool.map(process_test_case, args_for_pool)

    # Ergebnisse zusammenfassen
    total_processed = sum(r[0] for r in results)
    total_skipped = sum(r[1] for r in results)

    print("\n--- Zusammenfassung ---")
    print(f"Verarbeitung abgeschlossen.")
    print(f"Erfolgreich verarbeitete Testfall-Ordner: {total_processed}")
    print(f"Übersprungene Testfall-Ordner (Fehler): {total_skipped}")


if __name__ == '__main__':
    main()