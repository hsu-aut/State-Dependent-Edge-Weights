Temporal Weighting for Causal Graphs

Dieses Projekt implementiert einen Workflow zur Erstellung und Analyse von zeitlich gewichteten kausalen Graphen. Das System liest eine Topologie aus einer AML-Datei, verarbeitet Simulationsdaten und nutzt ein Dynamisches Bayes'sches Netzwerk (DBN), um die Kausalzusammenhänge in Form von Kantengewichten zu quantifizieren.

Funktionsweise

Der Prozess gliedert sich in mehrere Hauptschritte:

    Graph-Erstellung: Aus einer AML-Datei wird ein kausaler Graph der Systemtopologie erstellt. Hierarchische und prozesstechnische Verbindungen werden dabei berücksichtigt.

    Datenaufbereitung: Simulations-Rohdaten aus Parquet-Dateien werden aufbereitet. Dies umfasst das Einlesen, die Harmonisierung von Zeitstempeln und die Auswahl relevanter Sensor- und Aktuatordaten.

    DBN-Konstruktion: Der statische Graph wird in ein Dynamisches Bayes'sches Netzwerk umgewandelt. Dabei werden Sensor- und Parameterknoten auf zwei Zeitebenen (t-1 und t) abgebildet, um zeitliche Abhängigkeiten zu modellieren.

    Modell-Fitting und Gewichtung: Ein LinearGaussianBayesianNetwork wird auf die aufbereiteten Daten gefittet. Anschließend werden die Kantengewichte, unter anderem mittels KL-Divergenz, berechnet, um die Stärke der kausalen Einflüsse zu quantifizieren.

Projektstruktur

Das Projekt ist in mehrere Module unterteilt:

    graph_building/: Enthält Skripte zur Erstellung des Graphen aus der AML-Datei (Arroyo_DCDG_PLUT.py) und zur Konstruktion des DBN (dbn_constructer.py).

    graph_operations/: Beinhaltet die Logik zum Fitten des Modells und zur Berechnung der Kantengewichte (eval_graph.py).

    data_preparation/: Skripte zur Aufbereitung, Konfiguration (PARAMETER_CONFIG.py) und zum Mapping (MAPPING_DICT.py) der Rohdaten.

    simulation/: Enthält Konfigurationen und Skripte zur Durchführung von Simulationen, die als Datengrundlage dienen.
