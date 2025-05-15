import os
import pandas as pd
import PARAMETER_CONFIG


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
                # alles nach dem Doppelpunkt, führende Leerzeichen wegstrippen
                param_name = line.split(":", 1)[1].strip()
            elif line.startswith("Wert:"):
                param_val = float(line.split(":", 1)[1].strip())
    if param_name is None or param_val is None:
        raise ValueError(f"Ungültiges Format in {txt_path!r}")
    return param_name, param_val


def process_all_folders(root_dir: str) -> dict[str, pd.DataFrame]:
    """
    Durchläuft alle direkten Unterordner von root_dir,
    liest CSV + TXT aus, hängt Parameter-Spalten an
    und gibt pro Ordner ein fertiges DataFrame zurück.
    """
    results = {}
    for sub in os.listdir(root_dir):
        folder = os.path.join(root_dir, sub)
        if not os.path.isdir(folder):
            continue

        # a) Pfade ermitteln
        csv_file = next(
            (f for f in os.listdir(folder) if f.lower().endswith(".csv")), None
        )
        txt_file = next(
            (f for f in os.listdir(folder) if f.lower().endswith(".txt")), None
        )
        if not csv_file or not txt_file:
            print(f"  → Überspringe {sub}: CSV oder TXT fehlt.")
            continue

        csv_path = os.path.join(folder, csv_file)
        txt_path = os.path.join(folder, txt_file)

        # b) CSV einlesen
        df = pd.read_csv(csv_path)

        # c) geänderten Parameter auslesen
        changed_name, changed_val = read_changed_param(txt_path)

        # d) Parameter-Spalten erzeugen
        #    - alle Parameter aus nominal_vals
        for param, nom_val in PARAMETER_CONFIG.NOMINALS.items():
            df[param] = nom_val

        #    - überschreibe für den geänderten Parameter
        if changed_name not in df.columns:
            df[changed_name] = changed_val
        else:
            # falls der Param-Name zufällig schon Spalte ist, überschreiben
            df[changed_name] = changed_val

        # e) speichern im Ergebnis-Dict
        results[sub] = df

        print(
            f"  ✓ Verarbeitet: {sub} (geänderter Param: {changed_name} = {changed_val})"
        )

    return results


if __name__ == "__main__":
    # Beispielaufruf
    root_dir = r"C:\Users\Moritz\Desktop\Master\Code\Test_Data"
    results = process_all_folders(root_dir)

    combined = (
        pd.concat(
            results.values(), keys=results.keys(), names=["run"], ignore_index=False
        )
        .reset_index(level="run")
        .reset_index(drop=True)
    )

    mode_dfs = {
        "mode_" + "_".join(str(v) for v in mode_vals): group
        for mode_vals, group in combined.groupby(PARAMETER_CONFIG.ACTUATORS_FOR_MODI)
    }

    print(mode_dfs.keys())

    # und zum Beispiel die Größe einer einzelnen Gruppe abfragen:
    print(mode_dfs['mode_0_0_0_0_0_0'].shape)
