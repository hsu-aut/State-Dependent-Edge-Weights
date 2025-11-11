import sys
import os

# Gehe eine Ebene höher, um den Projekt-Root hinzuzufügen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import igraph as ig
from xml.etree import ElementTree as ET
import time
import re
import numpy as np
import heapq
import networkx as nx
from pyvis.network import Network
#import Config


class Valve:
    """
    Repräsentiert ein Ventil in einem Prozessfluss. 
    Speichert den Zustandsverlauf und berechnet Kanten-Gewichte in igraph anhand von Kernel-Funktionen.
    """
    def __init__(self, Tag) -> None:
        """
        Args:
            Tag (str): Eindeutige Kennung (Tag) des Ventils.
        """
        self.history_length = 3  
        
        # History der Zustände (z.B. Öffnungsgrade), startet mit 0.5 als Beispiel.
        self.state_history = [1.0] * self.history_length
        

        # Eindeutiger Name des Ventils
        self.Tag = Tag

        # Dictionary, welches die zugehörigen Edge-Indizes für jede Größe speichert
        self.relationDict = {
            "Temperature": [],
            "Pressure": [],
            "Flow": [],
            "Level": []
        }
        
        # Kernel-Dictionary für die zeitliche Gewichtung (siehe history_kernel)
        self.kernelDict = {
            "Temperature": self.history_kernel(1, 1, 1, 1),
            "Pressure":    self.history_kernel(1, 1, 1, 1),
            "Flow":        self.history_kernel(1, 1, 1, 1),
            "Level":       self.history_kernel(1, 1, 1, 1)
        }

        # Kernel-Dictionary, um den Ventilzustand (0..1) auf Wertebereiche zu skalieren
        # Test: Skalierung von 0-50 auf 0.01-0.5 gesetzt. Ich glaube irgendwo läuft etwas mit dn /100 falsch
        self.valuekernelDict = {
            "Temperature": self.history_kernel(0.01, 0.99, 1, 2),
            "Pressure":    self.history_kernel(0.01, 0.99, 1, 2),
            "Flow":        self.history_kernel(0.01, 0.99, 1, 2),
            "Level":       self.history_kernel(0.01, 0.99, 1, 2)
        }

    def find_relations(self, igraph):
        """
        Durchsucht den Graphen nach Kanten mit bestimmten 'carrier'-Typen (Temperature, Pressure, Flow, Level),
        die dieses Ventil (self.Tag) betreffen. Speichert die entsprechenden Edge-Indizes in self.relationDict.
        
        Args:
            igraph (igraph.Graph): Der zu durchsuchende Graph.
        """
        valve_index = igraph.vs["Tag"].index(self.Tag)
        child_indices = igraph.successors(valve_index)

        for carriertype in self.relationDict:
            # Für jeden Kind-Knoten prüfen wir die Kanten in beide Richtungen
            for child in child_indices:
                # Alle ausgehenden Kanten vom child
                for edge in igraph.es.select(_source=child):
                    if edge["carrier"] == carriertype:
                        self.relationDict[carriertype].append(edge.index)

                # Alle eingehenden Kanten zum child
                for edge in igraph.es.select(_target=child):
                    if edge["carrier"] == carriertype:
                        self.relationDict[carriertype].append(edge.index)

    def apply_weights(self, igraph):
        """
        Berechnet aus dem Zustandsverlauf (state_history) mithilfe der Kernel-Dictionaries neue 
        Kanten-Gewichte und setzt diese in igraph.es[...]["weight"] ein.

        Args:
            igraph (igraph.Graph): Der Graph, in dem die Kanten angepasst werden.
        """
        
        '''PROBLEM: ES WERDEN NICHT DIE ANGRENZENDEN KANTEN NEU GEWICHTET, DIES WÄRE FÜR UPDATE VALVES NÖTIG'''
        
        for carrier in self.relationDict:
            # Aktueller Verlauf des Ventilzustands
            temp_history = self.state_history

            # Initialisierung der Werte zur Berechnung der Kanten-Gewichte
            temp_value_history = [1] * self.history_length

            # Transfer der state_history auf den Indexbereich des valuekernelDict
            for idx, hist_val in enumerate(temp_history):
                # Skaliere hist_val*history_length, 
                # z.B. wenn hist_val=0.5 und history_length=1 => scaled_val=0.5
                scaled_val = int(np.round(hist_val * self.history_length))
                
                # Skaliere hist_val (0..1 oder 0..50?) auf den Indexbereich des Kernels
                if scaled_val < 0:
                    hist_index = 0
                elif scaled_val <= 0.5: #### Testen, ob es stattdessen mi 0.5 funktioniert
                    # Skaliere (0..50) -> (0..Len(valuekernel)-1)
                    max_idx = len(self.valuekernelDict[carrier]) - 1
                    hist_index = int(np.round(scaled_val / 0.5 * max_idx))
                else:
                    # scaled_val > 50 => letzten Wert nehmen
                    hist_index = len(self.valuekernelDict[carrier]) - 1

                temp_value_history[idx] = self.valuekernelDict[carrier][hist_index]

            # Gewicht berechnen:
            # Kernel aus kernelDict => Zeitliche Gewichtung
            numerator = np.sum(
                np.array(temp_value_history) * np.array(self.kernelDict[carrier])
            )
            denominator = np.sum(self.kernelDict[carrier]) or 1.0  # Schutz vor 0-Division
            current_weight = np.round(numerator / denominator,2)

            # Allen zugehörigen Kanten das Gewicht und Actors zuweisen
            for e_idx in self.relationDict[carrier]:
                igraph.es[e_idx]["weight"] = current_weight
                igraph.es[e_idx]["Actors"] = self.Tag

    def update_state(self, in_state):
        """
        Aktualisiert die state_history um den neuen Zustand in_state.
        Entfernt dafür den ältesten Eintrag.

        Args:
            in_state (float): Neuer Ventilzustand (z.B. Öffnungsgrad).
        """
        self.state_history.append(in_state)
        self.state_history.pop(0)

    def find_relations_old(self, in_carriertype, igraph):
        """
        Alte Logik, die alle edges in child-nodes auf den carrier-Typ in_carriertype prüft.
        Falls nicht mehr benötigt, kann sie entfernt werden.

        Args:
            in_carriertype (str): Z.B. "Temperature", "Pressure", ...
            igraph (igraph.Graph): Der zu durchsuchende Graph.
        """
        valve_index = igraph.vs["Tag"].index(self.Tag)
        child_indices = igraph.successors(valve_index)

        for child in child_indices:
            for relation in igraph.successors(child):
                if igraph.es[relation]["carrier"] == in_carriertype:
                    self.relationDict[in_carriertype].append(relation)

    def history_kernel(self, start_value, stop_value, ramp_startpoint, ramplength):
        """
        Erzeugt einen Kernel-Vektor der Länge self.history_length. Dieser 
        besteht aus einer Phase mit konstantem start_value, einer Rampe 
        von start_value zu stop_value und einer Phase mit konstantem stop_value.

        Args:
            start_value (float): Anfangswert.
            stop_value (float): Endwert.
            ramp_startpoint (int): Index im Kernel, an dem die Rampe beginnt.
            ramplength (int): Länge der Rampe.

        Returns:
            list: Ein Kernel der Länge self.history_length.
        """
        kernellength = self.history_length
        kernel = (
            [start_value] * ramp_startpoint
            + list(np.round(np.linspace(start_value, stop_value, ramplength),2))
            + [stop_value] * max(0, (kernellength - ramp_startpoint - ramplength))
        )
        # Zur Sicherheit auf die tatsächliche Länge beschneiden,
        # falls ramplength & ramp_startpoint größer als history_length sind
        return kernel[:kernellength]


def flatten(nested_list):
    """
    Flatten-Funktion, die eine verschachtelte Liste auf eine Ebene herunterbricht.
    Bleibt hier unverändert, kann aber ggf. ausgelagert werden, wenn du sie öfter brauchst.
    """
    def flatten_helper(nested, flat):
        for item in nested:
            if isinstance(item, int):
                flat[-1].append(item)
            else:
                flat.append([])
                flatten_helper(item, flat)
    result = [[]]
    flatten_helper(nested_list, result)
    return result


class DCDG_Class:
    """
    DCDG_Class erzeugt und erweitert einen gerichteten Graphen (igraph.Graph)
    aus einer AML-Datei, versieht ihn mit diversen Attributen und führt 
    Kausalitäts- bzw. Regel-Verknüpfungen (apply_rule) durch.
    """

    def __init__(self) -> None:
        """
        Initialisiert den Graphen und einige Statusvariablen.
        """
        intVertexNumber = 0
        self.counter = 0
        self.boolInitComplete = False
        self.NumberOfElements = 0
        # Leeren, gerichteten Graphen anlegen
        self.g = ig.Graph(intVertexNumber, directed=True)
        
    def update_edge_weights_from_mode(self, weights_df):
        """
        Aktualisiert die Kantengewichte des Graphen basierend auf einem DataFrame
        für den aktuellen Betriebsmodus.
        """
    
    
        # Iteriere direkt über die Zeilen des Gewichts-DataFrames.
        # 'original_edge_id' ist hier der Index des DataFrames.
        for original_edge_id, row in weights_df.iterrows():
            try:
                # Lese die neuen Gewichte aus der aktuellen Zeile
                new_weight = row['MI_mit_Var_Xi']
                new_mi = row['MI_mit_Var_Xi']
    
                # Greife direkt über den Index auf die Kante im Graphen zu
                # und aktualisiere ihre Attribute.
                edge = self.g.es[original_edge_id]
                edge['weight'] = new_weight
    
            except IndexError:
                # print(f"Warnung: Kanten-ID {original_edge_id} existiert nicht im Graphen.")
                pass
            except KeyError:
                # print(f"Warnung: Spalten für Kante {original_edge_id} nicht vollzählig.")
                pass

    def add_myvertex(self, in_tag, in_carriertype, in_amlID, in_alarmtag, in_alarmstate, in_alarmlimits, in_deviation):
        """
        Fügt dem Graphen einen neuen Vertex mit entsprechenden Attributen hinzu.

        Args:
            in_tag (str): Eindeutiger Tag/Name des Knotens.
            in_carriertype (str): Z.B. "Temperature", "Pressure", "Flow" usw.
            in_amlID (str): AML-ID aus der AML-Datei oder None.
            in_alarmtag (bool): Ob es sich um einen Knoten handelt, der ein Alarm-Tag ist.
            in_alarmstate (bool): Gibt an, ob ein Alarmzustand vorliegt.
            in_alarmlimits (bool): Enthält ggf. Alarm-Grenzwerte.
            in_deviation (float): Numerische Abweichung für diesen Knoten.

        Hinweise:
            - Farbe (color) wird abhängig vom Carrier-Typ festgelegt.
            - parameterlabel=1 wird gesetzt, wenn es sich um einen der Parameter-Typen handelt.
            - sensorlabel=1 wird gesetzt, wenn in_carriertype=="Measurement".
        """
        # Farbe bestimmen
        if in_carriertype == "Temperature":
            color = "red"
        elif in_carriertype == "Pressure":
            color = "green"
        elif in_carriertype == "Flow":
            color = "blue"
        elif in_carriertype == "Level":
            color = "yellow"
        else:
            color = "slategray"
        
        # Parameterlabel: 1, falls in_carriertype zu bestimmten Prozessparametern gehört
        if in_carriertype in [
            "Height", "Rotational_Speed", "PumpVolume", "Area", "Height", "Length", 
            "Diameter", "Roughness", "HDiff", "PDropNom", "MFlowNom"
        ]:
            parameterlabel = 1
        else:
            parameterlabel = 0

        # Sensorlabel: 1, falls Mess-Knoten
        if in_carriertype == "Measurement":
            sensorlabel = 1
        else:
            sensorlabel = 0

        self.g.add_vertex(
            Tag=in_tag,
            Carrier=in_carriertype,
            AMLID=in_amlID,
            AT=in_alarmtag,
            AS=in_alarmstate,
            AL=in_alarmlimits,
            color=color,
            aktorinfluence=False,
            parameterlabel=parameterlabel,
            sensorlabel=sensorlabel,
            deviation=in_deviation
        )

    def find_routes(self, vertex1_id, vertex2_type):
        """
        Sucht alle Pfade von Knoten 'vertex1_id' zu allen Knoten des Typs 'vertex2_type',
        die genau 4 Knoten (3 Kanten) umfassen und die Carrier-Reihenfolge 
        ['hasparent', 'Product', 'haschild'] einhalten.

        Args:
            vertex1_id (int): Index des Startknotens im Graphen.
            vertex2_type (str): Gesuchter Ziel-Typ des Knotens (z.B. "Temperature").

        Returns:
            list[tuple]: Liste von (start_vertex_id, end_vertex_id)-Tupeln, 
                         die den Kriterien entsprechen.
        """
        vertices2_ids = [v.index for v in self.g.vs if v['Carrier'] == vertex2_type]
        valid_routes = []
        edge_order = ['hasparent', 'Product', 'haschild']

        # Prüfe alle potentiellen Zielknoten vom Typ vertex2_type
        for vertex2_id in vertices2_ids:
            all_paths = self.g.get_all_simple_paths(vertex1_id, to=vertex2_id)
            for path in all_paths:
                if len(path) != 4:
                    continue
                edges = [(path[i], path[i+1]) for i in range(len(path) - 1)]
                edge_types = [self.g.es[self.g.get_eid(*edge_pair)]["Carrier"] for edge_pair in edges]

                if edge_types == edge_order:
                    vertices = [self.g.vs[vid]["Carrier"] for vid in path]
                    # Beispiel: Prüft, ob start und end 'Temperature' sind und 
                    # an Position path[1] == 'Any Type'
                    if vertices[0] == vertices[3] == 'Temperature' and vertices[1] == 'Any Type':
                        valid_routes.append((path[0], path[3]))
        return valid_routes

    def change_edge_hierarchieparents(self):
        """
        Durchsucht alle Knoten und prüft, ob sie eine Kante vom Typ 'Product' 
        besitzen. Falls ja, wird die erste Kante mit 'hasparent' umbenannt in 'hashierarchieparent'.
        """
        for vertex in self.g.vs:
            edges = self.g.es.select(_source=vertex.index)
            target_edges = self.g.es.select(_target=vertex.index)
            # Prüfen, ob 'Product' in ausgehenden oder eingehenden Kanten auftaucht
            if any(e['carrier'] == "Product" for e in edges) or any(e['carrier'] == "Product" for e in target_edges):
                hasparent_edges = [edge for edge in edges if edge['carrier'] == "hasparent"]
                if len(hasparent_edges) > 0:
                    hasparent_edges[0]['carrier'] = "hashierarchieparent"

    def generate_graphfromAML(self, amlfilepath):
        """
        Liest eine AML-Datei (amlfilepath) ein und erstellt entsprechend 
        der AML-Struktur Knoten und Kanten im Graphen (self.g). 
        Anschließend werden Kantenhierarchien angepasst und einige Standard-Routen gesucht.

        Args:
            amlfilepath (str): Pfad zur AML-Datei.
        """
        tree = ET.parse(amlfilepath)
        root = tree.getroot()

        node_list = [
            "Temperature", "Pressure", "Flow", "Level", "Power",
            "Measurement_Power", "Measurement_Temperature", "Measurement_Pressure",
            "Measurement_Flow", "Measurement_Level", "State", "Measurement_State",
            "Height", "Rotational_Speed", "PumpVolume", "Area", "Length", 
            "Diameter", "Roughness", "HDiff", "PDropNom", "MFNominal"
        ]
        node_list_with_ = ['_' + element for element in node_list]

        parent_map = {}
        attribute_map = {}
        elementsID = {}
        interface_map = {}

        # -------------------------------------------------
        # Hilfsfunktion, die die AML-Struktur rekursiv liest
        # -------------------------------------------------
        def process_element(parent):
            for child in parent:
                try:
                    if child.tag == "{http://www.dke.de/CAEX}InternalElement":
                        elementsID[child.attrib['Name']] = child.attrib['ID']
                        # Verknüpfen parent -> child in parent_map
                        if parent.attrib['Name'] != child.attrib['Name']:
                            parent_map[child.attrib['Name']] = parent.attrib['Name']
                            process_element(child)

                    elif child.tag == "{http://www.dke.de/CAEX}Attribute":
                        # Prüfen, ob es sich um einen zulässigen Node (Param o.ä.) handelt
                        if child.attrib['Name'] in node_list or "Concentration" in child.attrib['Name']:
                            temp_str = parent.attrib['Name'] + '_' + child.attrib['Name']
                            attribute_map[temp_str] = True

                    elif child.tag == "{http://www.dke.de/CAEX}ExternalInterface":
                        # ExternalInterface sammeln, noch keine Kanten
                        if parent.attrib['Name'] not in interface_map:
                            interface_map[parent.attrib['Name']] = {}
                        interface_map[parent.attrib['Name']][child.attrib['ID']] = child.attrib['Name']

                except Exception as e:
                    print(f"Error processing element: {e}")

        # Starte das Einlesen für alle InternalElements
        for elem in root.iter('{http://www.dke.de/CAEX}InternalElement'):
            process_element(elem)

        # Erstelle 'hierarch'-Knoten basierend auf parent_map
        for key in parent_map:
            self.add_myvertex(key, 'hierarch', elementsID[key], False, False, False, False)
            # Ausnahme: Knoten "Plant" wird hier nicht weiter verknüpft
            if key != 'Plant':
                if parent_map[key] in elementsID:
                    if len(self.g.vs.select(Tag=parent_map[key])) == 0:
                        self.add_myvertex(parent_map[key], 'hierarch', elementsID[parent_map[key]], False, False, False)

                    # Füge Kanten hasparent/haschild hinzu
                    self.g.add_edge(
                        self.g.vs["Tag"].index(key), 
                        self.g.vs["Tag"].index(parent_map[key]),
                        carrier='hasparent',
                        weight=0
                    )
                    self.g.add_edge(
                        self.g.vs["Tag"].index(parent_map[key]),
                        self.g.vs["Tag"].index(key),
                        carrier='haschild',
                        weight=0
                    )

        # Attribute einfügen (Parameterknoten etc.)
        remove_list = node_list_with_
        pattern = '|'.join(remove_list)

        for attr in attribute_map:
            # z.B. if attr="Pump_Height" -> key="Pump"
            key = re.sub(pattern, '', attr)
            if key in elementsID:
                carrierstring = attr.replace(key + '_', '')
                self.add_myvertex(attr, carrierstring, None, False, False, False, False)
                self.g.add_edge(
                    self.g.vs["Tag"].index(attr),
                    self.g.vs["Tag"].index(key),
                    carrier='hasparent',
                    weight=0
                )
                self.g.add_edge(
                    self.g.vs["Tag"].index(key),
                    self.g.vs["Tag"].index(attr),
                    carrier='haschild',
                    weight=0
                )

        # Erstelle Kanten anhand von 'ExternalInterface'-Verbindungen in AML
        for connect in root.iter('{http://www.dke.de/CAEX}InternalLink'):
            name_partnerA = next((n for n, ifaces in interface_map.items() if connect.attrib['RefPartnerSideA'] in ifaces), None)
            name_partnerB = next((n for n, ifaces in interface_map.items() if connect.attrib['RefPartnerSideB'] in ifaces), None)

            if name_partnerA is not None and name_partnerB is not None:
                connect_partnerA = interface_map[name_partnerA][connect.attrib['RefPartnerSideA']]
                connect_partnerB = interface_map[name_partnerB][connect.attrib['RefPartnerSideB']]

                # Einige Cases unterscheiden zwischen *_OUT, INOUT, IN usw.
                if '_OUT' in connect_partnerA and not 'OUT' in connect_partnerB:
                    self.g.add_edge(
                        self.g.vs["Tag"].index(name_partnerA),
                        self.g.vs["Tag"].index(name_partnerB),
                        carrier=connect_partnerA.replace("_OUT", ''),
                        weight=0
                    )
                else:
                    if 'INOUT' in connect_partnerA:
                        if 'INOUT' in connect_partnerB:
                            # Bidirektionale Kante
                            self.g.add_edge(
                                self.g.vs["Tag"].index(name_partnerA),
                                self.g.vs["Tag"].index(name_partnerB),
                                carrier=connect_partnerA.replace("_INOUT", ''),
                                weight=0
                            )
                            self.g.add_edge(
                                self.g.vs["Tag"].index(name_partnerB),
                                self.g.vs["Tag"].index(name_partnerA),
                                carrier=connect_partnerA.replace("_INOUT", ''),
                                weight=0
                            )
                        elif 'IN' in connect_partnerB:
                            self.g.add_edge(
                                self.g.vs["Tag"].index(name_partnerA),
                                self.g.vs["Tag"].index(name_partnerB),
                                carrier=connect_partnerA.replace("_INOUT", ''),
                                weight=0
                            )
                        else:
                            print('ERROR: Case3 NOT IMPLEMENTED')

                    else:
                        if '_OUT' in connect_partnerA and 'OUT' in connect_partnerB:
                            self.g.add_edge(
                                self.g.vs["Tag"].index(name_partnerA),
                                self.g.vs["Tag"].index(name_partnerB),
                                carrier=connect_partnerA.replace("_OUT", ''),
                                weight=0
                            )
                        else:
                            if '_IN' in connect_partnerA and '_OUT' in connect_partnerB:
                                self.g.add_edge(
                                    self.g.vs["Tag"].index(name_partnerB),
                                    self.g.vs["Tag"].index(name_partnerA),
                                    carrier=connect_partnerA.replace("_IN", ''),
                                    weight=0
                                )
                            else:
                                print('ERROR: Case4 NOT IMPLEMENTED')

        # Korrigiere Kanten, falls 'Product'-Kanten existieren
        self.change_edge_hierarchieparents()

        # Bestimmte Pfade suchen
        self.vertexpaths, loop1length = self.find_paths(['hasparent', 'Product', 'haschild'], [3,1,3])
        alarmpaths, loop2length = self.find_paths(['hasparent', 'haschild'], [3,3])
        cooling_loops = self.find_paths(['hasparent', 'Product_ThermalContact', 'haschild'], [5,1,5])[0:-1]
        cooling_loops = flatten(cooling_loops)[2:-1]

        # 1) Beispiel: Flow -> ...
        # 2) Forward/Backward Propagation definieren
        self.apply_rule("Temperature", "Temperature", strength=0.95, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=1)
        self.apply_rule("Flow", "Flow", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=2)
        self.apply_rule("Flow", "Level", strength=0.99, time_constant=0.1, effect_factor=1, findValves=False, rulenumber=3)
        self.apply_rule("Level", "Flow", strength=0.5, time_constant=0.1, effect_factor=1, findValves=False, rulenumber=4)
        self.apply_rule("Pressure", "Temperature", strength=0.1, effect_factor=-1, findValves=False, rulenumber=5)
        self.apply_rule("State", "Flow", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=6, apply_carrier='State')

        # Backward
        self.apply_rule("Temperature", "Temperature", strength=0.95, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=7, inverse=True)
        self.apply_rule("Pressure", "Pressure", strength=0.95, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=8, inverse=True)
        self.apply_rule("Flow", "Flow", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=9, inverse=True)
        # self.apply_rule("Flow", "Level", strength=0.99, time_constant=0.1, effect_factor=-1, findValves=False, rulenumber=10, inverse=True)
        self.apply_rule("Level", "Flow", strength=0.99, time_constant=0.1, effect_factor=-1, findValves=False, rulenumber=11, inverse=True)
        # Anlage fungiert nahezu Drucklos und ohne Temperaturgradienten
        #self.apply_rule("Temperature", "Pressure", strength=0.1, effect_factor=-1, findValves=False, rulenumber=7, inverse=True)

        # Zusätzliche Statevariable-Regeln
        self.apply_rule("Pressure", "Flow", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=12, inverse=False)
        self.apply_rule("Flow", "Pressure", strength=0.99, time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=13, inverse=True)

        # Alarm Rules - Sensors
        self.apply_rule("Measurement_Temperature", "Temperature", strength=1.00, time_constant=0.0, effect_factor=1,
                        apply_carrier='isalarm', searchpath=alarmpaths, shortest=True, findValves=False, rulenumber=15)
        self.apply_rule("Measurement_Pressure", "Pressure", strength=1.00, time_constant=0.0, effect_factor=1,
                        apply_carrier='isalarm', searchpath=alarmpaths, shortest=True, findValves=False, rulenumber=16)
        self.apply_rule("Measurement_Flow", "Flow", strength=1.00, time_constant=0.0, effect_factor=1,
                        apply_carrier='isalarm', searchpath=alarmpaths, shortest=True, findValves=False, rulenumber=17)
        self.apply_rule("Measurement_Level", "Level", strength=1.00, time_constant=0.0, effect_factor=1,
                        apply_carrier='isalarm', searchpath=alarmpaths, shortest=True, findValves=False, rulenumber=18)
        self.apply_rule("Measurement_State", "State", strength=1.00, time_constant=0.0, effect_factor=1,
                        apply_carrier='isalarm', searchpath=alarmpaths, shortest=True, findValves=False, rulenumber=19)
        self.apply_rule("Measurement_Power", "Power", strength=1.00, time_constant=0.0, effect_factor=1,
                        apply_carrier='isalarm', searchpath=alarmpaths, shortest=True, findValves=False, rulenumber=20)

        # Umgedrehte Kanten für Alarme
        for edge in self.g.es:
            if edge['carrier'] == 'isalarm':
                self.g.add_edge(edge.target, edge.source, carrier="hasalarm", weight=1, tau=0, lambda_factor=1)

        # # Parameters:
        
        # Probabilities:
        high_probability = 0.99
        medium_probability = 0.7
        low_probability = 0.3
        
        probability_indexes = {
            "Diameter": high_probability,
            "Length": high_probability,               
            "Roughness": high_probability,
            "HDiff": low_probability,
            "PDropNom": high_probability,
            "MFNominal": low_probability,
            "Rotational_Speed": low_probability,
            "Area": low_probability
        }
        
        
        
        
        
        
        # Paramter Rules:
        # # Druckverlust: P(k) - P(k+1) oder P(k-1) - P(k) : Höherer Druckverlust: senke P(k+1) oder P(k) oder erhöhe P(k) oder P(k-1)
        # # Rohrleitung: 
        # ## Durchmesser:
        # # D(k) -> Q(k) +0.99: Ein größerer Durchmesser erhöht den Durchfluss durch reduzierte Reibungsverluste (Darcy-Weisbach)
        # self.apply_rule("Diameter", "Flow", strength=probability_indexes["Diameter"], time_constant=0.0, effect_factor=1, searchpath=alarmpaths,
        #                  findValves=False, rulenumber=8, inverse=False, apply_carrier='Diameter')
        # # D(k-1) -> P(k) +0.99: Ein größerer Durchmesser verringert den Druckverlust (=erhöht den Druck in der Nachfolgerkomponente).
        self.apply_rule("Diameter", "Pressure", strength=probability_indexes["Diameter"], time_constant=0.0, effect_factor=1, findValves=False, rulenumber=21, inverse=False, apply_carrier='Diameter')
        # # D(k-1) -> P(k) -0.99: Ein größerer Durchmesser verringert den Druckverlust (=senkt den Druck in der Vorgängerkomponente).
        self.apply_rule("Pressure", "Diameter", strength=probability_indexes["Diameter"], time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=22, inverse=True, apply_carrier='Diameter')
        # ##Länge
        # # L(k) -> Q(k) -0.99: Eine längere Rohrleitung senkt den Durchfluss durch erhöhte Reibungsverluste (Darcy-Weisbach)
        # self.apply_rule("Length", "Flow", strength=probability_indexes["Length"], time_constant=0.0, effect_factor=-1, searchpath=alarmpaths,
        #                  findValves=False, rulenumber=8, inverse=False, apply_carrier='Length')
        # # L(k-1) -> P(k) -0.99: Eine längere Rohrleitung erhöht den Druckverlust (=Senkt den Druck in der Nachfolgerkomponente).
        self.apply_rule("Length", "Pressure", strength=probability_indexes["Length"], time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=23, inverse=False, apply_carrier='Length')
        # # L(k) -> P(k-1) +0.99: Eine längere Rohrleitung erhöht den Druckverlust (=Erhöht den Druck in der Vorgängerkomponente).
        self.apply_rule("Pressure", "Length", strength=probability_indexes["Length"], time_constant=0.0, effect_factor=1, findValves=False,
                        rulenumber=24, inverse=True, apply_carrier='Length')
        # # Rohrleitungslänge führt zu Abkühlung: Erst relevant für RAG
        # ##Rauigkeit
        # R(k) -> Q(k) -0.99: Eine rauere Rohrleitung senkt den Durchfluss durch erhöhte Reibungsverluste (Darcy-Weisbach)
        # self.apply_rule("Roughness", "Flow", strength=probability_indexes["Roughness"], time_constant=0.0, effect_factor=-1, searchpath=alarmpaths,
        #                  findValves=False, rulenumber=8, inverse=False, apply_carrier='Roughness')
        # # R(k-1) -> P(k) -0.99: Eine rauere Rohrleitung erhöht den Druckverlust (= senkt den Druck in der Nachfolgerkomponente).
        self.apply_rule("Roughness", "Pressure", strength=probability_indexes["Roughness"], time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=25, inverse=False, apply_carrier='Roughness')
        # # R(k-1) -> P(k) -0.99: Eine rauere Rohrleitung erhöht den Druckverlust (= erhöht den Druck in der Vorgängerkomponente).
        self.apply_rule("Pressure", "Roughness", strength=probability_indexes["Roughness"], time_constant=0.0, effect_factor=1, findValves=False, rulenumber=26, inverse=True, apply_carrier='Roughness')
        ## Höhendifferenz
        # # HD(k) -> P(K) +0.99: Eine größere Höhendifferenz erhöht den Druck in der Komponente (hydrostatischer Druck)
        self.apply_rule("HDiff", "Pressure", strength=probability_indexes["HDiff"], time_constant=0.0, effect_factor=1, searchpath=alarmpaths,
                         findValves=False, rulenumber=27, inverse=False, apply_carrier='HeightDifference')
        # # HD(k-1) -> P(k) -0.99: Eine größere Höhendifferenz erhöht den Druckverlust (= senkt den Druck in der Nachfolgerkomponente).
        self.apply_rule("HDiff", "Pressure", strength=probability_indexes["HDiff"], time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=28, inverse=False, apply_carrier='HeightDifference')
        # # HD(k+1) -> P(K) +0.99: Eine größere Höhendifferenz erhöht den Druckverlust (= erhöht den Druck in der Vorgängerkomponente).
        self.apply_rule("Pressure", "HDiff", strength=probability_indexes["HDiff"], time_constant=0.0, effect_factor=1, findValves=False, rulenumber=29,
                        inverse=True, apply_carrier='HeightDifference')
        # # HD(k+1) -> Q(k) -0.99: Eine größere Höhendifferenz senkt den Durchfluss.
        # self.apply_rule("HDiff", "Flow", strength=probability_indexes["HDiff"], time_constant=0.0, effect_factor=-1, searchpath=alarmpaths,
        #                 findValves=False, rulenumber=8, inverse=False, apply_carrier='HeightDifference')
        ## Ventile: 
        # PDropNominal(k) -> Q(k) -0.99: Ein höherer Druckverlust in der Komponente senkt den Durchfluss.
        # self.apply_rule("PDropNom", "Flow", strength=probability_indexes["PDropNom"], time_constant=0.0, effect_factor=-1, searchpath=alarmpaths,
        #                 findValves=False, rulenumber=18, inverse=False, apply_carrier='PressureDropNominal')
        # PDropNominal(k-1) -> P(k) +0.99: Ein höherer Druckverlust senkt den Druck in der Nachfolgerkomponente.
        self.apply_rule("PDropNom", "Pressure", strength=probability_indexes["PDropNom"], time_constant=0.0, effect_factor=-1, 
                        findValves=False, searchpath=alarmpaths, rulenumber=30, inverse=False, apply_carrier='PressureDropNominal')
        # PDropNominal(k) -> P(k+1) -0.99: Ein höherer Druckverlust erhöht den Druck in der Vorgängerkomponente.
        self.apply_rule("Pressure", "PDropNom", strength=probability_indexes["PDropNom"], time_constant=0.0, effect_factor=1, findValves=False, rulenumber=31,
                        inverse=True, apply_carrier="PressureDropNominal")
        # MFlowNominal(k) -> Q(k) +0.99: Ein höherer Durchfluss erhöht den Durchfluss.
        self.apply_rule("Flow", "MFNominal", strength=probability_indexes["MFNominal"], time_constant=0.0, effect_factor=1, searchpath=alarmpaths,
                        findValves=False, rulenumber=32, inverse=True, apply_carrier='MFlowNominal')        
        ## Pumpen
        # Rotationsgeschwindigkeit(k) -> Q(k) +0.99: Eine höhere Rotationsgeschwindigkeit erhöht den Durchfluss.
        self.apply_rule("Rotational_Speed", "Flow", strength=probability_indexes["Rotational_Speed"], time_constant=0.0, effect_factor=1, searchpath=alarmpaths,
                        findValves=False, rulenumber=33, inverse=False, apply_carrier='RotationalSpeed')
        # Rotationsgeschwindigkeit(k-1) -> P(k) +0.99: Eine höhere Rotationsgeschwindigkeit erhöht den Druck in der nachfolgenden Komponente.
        self.apply_rule("Rotational_Speed", "Pressure", strength=probability_indexes["Rotational_Speed"], time_constant=0.0, effect_factor=1, findValves=False, rulenumber=34, inverse=False, apply_carrier='RotationalSpeed')
        ## Tanks
        #H(k)-> L(k) +0 Höhe hat keinen Einfluss auf den Füllstand
        #A(k) -> L(k) -0.99: Eine größere Fläche senkt den Füllstand.
        self.apply_rule("Area", "Level", strength=probability_indexes["Area"], time_constant=0.0, effect_factor=-1, searchpath=alarmpaths,
                        findValves=False, rulenumber=35, inverse=False, apply_carrier='Area')
        
        
        
        # # NEUES REGELSET:
        # # State Variables:
        # # Forward Propagation:
        # # Flow: 
        # # Q(k-1) -> Q(k) + 0.99: Kontinuitätsgleichung: Der Durchfluss bleibt erhalten, solange keine Verluste durch Leckagen oder Speicherungen auftreten (Massenerhaltung)
        # self.apply_rule("Flow", "Flow", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=1, inverse=False)
        # # S(k-1) -> Q(k) + 0.99: Der Zustand des Ventils / einer Pumpe ermöglicht den Durchfluss, wenn das Ventil geöffnet ist.
        # self.apply_rule("State", "Flow", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=8, apply_carrier='State')
        # # P(k-1) -> Q(k) + 0.98: Ein höherer Druck in der Vorgängerkomponente treibt den Durchfluss an.
        # self.apply_rule("Pressure", "Flow", strength=0.98, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=2, inverse=False)
        # # P(k+1) -> Q(k) -0.98: Ein geringerer Druck in der Nachfolgerkomponente erhöht den Durchfluss.
        # self.apply_rule("Flow", "Pressure", strength=0.98, time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=2, inverse=True)
        # # L(k-1) -> Q(k) + 0.99: Ein höherer Füllstand in der Vorgängerkomponente treibt den Durchfluss an.
        # self.apply_rule("Level", "Flow", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=5, inverse=False)
        # # Level:
        # # Q(k-1) -> L(k) + 0.99: Der Durchfluss in die Komponente erhöht den Füllstand.
        # self.apply_rule("Flow", "Level", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=6, inverse=False)
        # # Q(k+1) -> L(k) -0.99: Der Durchfluss aus der Komponente verringert den Füllstand.
        # self.apply_rule("Level", "Flow", strength=0.99, time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=6, inverse=True)
        # # Pressure:
        # # Q(k-1) -> P(k) -0.95: Der statische Druck in der Komponente wird durch den Durchfluss verringert.
        # self.apply_rule("Flow", "Pressure", strength=0.95, time_constant=0.0, effect_factor=-1, findValves=False, rulenumber=7, inverse=False)
        # # P(k-1) -> P(k) + 0.95: Der Druck in der Vorgängerkomponente erhöht den Druck in der aktuellen Komponente.
        # self.apply_rule("Pressure", "Pressure", strength=0.95, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=2, inverse=False)
        # # Temperature:
        # #T(k-1) -> T(k) +0.99: Eine höhere Temperatur in der Vorgängerkomponente erhöht die Temperatur in der aktuellen Komponente.
        # self.apply_rule("Temperature", "Temperature", strength=0.99, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=1, inverse=False)
        # # T(k-1) -> Q(k) +0.95: Eine höhere Temperatur senkt die Viskosität - dies führt zu einem höheren Durchfluss.
        # self.apply_rule("Temperature", "Flow", strength=0.95, time_constant=0.0, effect_factor=1, findValves=False, rulenumber=3, inverse=False)
        
        
        
        # Knoten vom Typ State => Ventile anlegen und Gewichtungen einpflegen
        self.valves = []
        for v in self.g.vs:
            if v['Carrier'] == 'State':
                temp_name = v['Tag'].replace("_State", "")
                self.valves.append(Valve(temp_name))  

        # Ventile nach graph-Anlage initialisieren
        for valve in self.valves:
            valve.find_relations(self.g)
            valve.apply_weights(self.g)

        print("Graph created")
            
        
        

    def update_valves(self, in_valvedict):
        """
        Aktualisiert den Zustand der Ventile (self.valves) anhand eines Dictionary in_valvedict.
        Dabei wird für jedes Ventil, dessen Tag im Dictionary vorhanden ist,
        'update_state' aufgerufen und im Anschluss 'apply_weights'.

        Args:
            in_valvedict (dict): 
                Key: Ventilname (Tag), 
                Value: neuer Zustandswert (z.B. Öffnungsgrad).
        """
        for valve in self.valves:
            if valve.Tag in in_valvedict:
                valve.update_state(in_valvedict[valve.Tag])
                # Gewichte werden falsch berechnet: 
                # eigentlich müsste es so sein, dass alle Kanten der Flow-Knoten und Pressure-Knoten auf 0.01 gesetzt werden, wenn valve geschlossen und auf 0.99 wenn offen,
                # mit einer Rampenfunktion dazwischen.
                
                valve.apply_weights(self.g) 

    def evaluate_valvestate(self, in_valuedict):
        """
        Funktional ähnlich wie update_valves, nur dass sie evtl. 
        zur Analyse oder Bewertung genutzt wird. 
        Auch hier werden die Zustände aktualisiert und Gewichte neu berechnet.

        Args:
            in_valuedict (dict):
                Key: Ventilname (Tag),
                Value: neuer Zustand (z.B. Öffnungsgrad).
        """
        for valve in self.valves:
            valve.update_state(in_valuedict[valve.Tag])
            valve.apply_weights(self.g)

    ###################################################################################################################
    # Erweiterte Funktionen für Pfadsuche, Dijkstra-Variante und Alarme
    ###################################################################################################################

    def modified_dijkstra(self, source_vertex_id, target_vertex_id, print_paths=True, dijkstra_type="Variable"):
        """
        Eine angepasste Dijkstra-Variante, die sowohl positive als auch negative 
        Einflüsse im Graph berücksichtigt und bestimmte Strafterme anwendet.
        
        Args:
            source_vertex_id (int): Index des Startknotens.
            target_vertex_id (int): Index des Zielknotens.
            print_paths (bool): Ob Pfade debug-ausgegeben werden sollen (derzeit nicht aktiv genutzt).
            dijkstra_type (str): "Variable" oder "parameter", um den Modus festzulegen.

        Returns:
            float: Die berechnete 'Distanz'. (Bei dijkstra_type="parameter" zusätzlich Pfad als zweites Rückgabewert-Element.)
        """

        def has_duplicate_pattern(path):
            """
            Prüft, ob sich im path ein Muster von 2 Knoten direkt wiederholt (A->B->A->B).
            Dies soll unnötige Schleifen verhindern.
            """
            for i in range(len(path) - 3):
                # Gleiche Teilsegmente A->B an zwei aufeinanderfolgenden Stellen
                if path[i:i+2] == path[i+2:i+4] or path[i] == path[i+2]:
                    return True
            return False

        edge_details = []

        # Unterscheide, ob der Quellknoten ein Parameterknoten ("parameter") oder ein Variablenknoten ("Variable") ist.
        if dijkstra_type == "parameter":
            source_vertex_value = self.g.vs[source_vertex_id]["parameterlabel"]
        elif dijkstra_type == "Variable":
            source_vertex_value = self.g.vs[source_vertex_id]['AS']
        else:
            print("something went wrong with the type of dijkstra")
            source_vertex_value = 0  # Fallback

        # Definiere Zielwert
        target_vertex_value = self.g.vs[target_vertex_id]['AS']

        # Positive und negative Distanz-Arrays + Pfadtracking
        positive_dist = [np.inf] * len(self.g.vs)
        negative_dist = [np.inf] * len(self.g.vs)
        positive_path = [[] for _ in range(len(self.g.vs))]
        negative_path = [[] for _ in range(len(self.g.vs))]

        # Falls Startknoten-Wert > 0 => positive_dist=0, sonst negative_dist=0
        if source_vertex_value > 0:
            positive_dist[source_vertex_id] = 0
        elif source_vertex_value < 0:
            negative_dist[source_vertex_id] = 0

        # Initialisiere Queue mit (distance, current_node, sign, pathlist)
        queue = [(0, source_vertex_id, source_vertex_value, [source_vertex_id])]

        while queue:
            (d, v, sign, path_so_far) = heapq.heappop(queue)

            # Betrachte alle Nachfolger von v
            for u in self.g.successors(v):
                edge_id = self.g.get_eid(v, u)
                edge_weight = self.g.es[edge_id]['weight']
                edge_lambda = self.g.es[edge_id]["lambda_factor"]

                # Abbruchbedingungen: 
                #  - edge_weight zu klein 
                #  - lambda_factor nicht definiert
                #  - Pfad wird zu lang
                if edge_weight <= 0.01 or edge_lambda is None or len(path_so_far) > 20:
                    continue

                # Log-Transformation der Kanten
                edge_weight_logged = edge_weight  # für Protokollierung
                edge_weight = -np.log(edge_weight_logged)

                # Aktualisiertes sign
                new_sign = sign * edge_lambda
                new_path = path_so_far + [u]

                # Schleifen/Patterns vermeiden
                if has_duplicate_pattern(new_path):
                    continue

                # Protokollierung der Kantendetails
                edge_details.append({
                    'source': self.g.vs[v]['Tag'],
                    'target': self.g.vs[u]['Tag'],
                    'weight': edge_weight,
                    'log_weight': edge_weight_logged,
                })

                # Aktualisiere positive_dist/negative_dist
                new_dist = d + edge_weight
                if new_sign >= 0 and new_dist < positive_dist[u]:
                    positive_dist[u] = new_dist
                    positive_path[u] = new_path
                    heapq.heappush(queue, (new_dist, u, 1, new_path))
                if new_sign <= 0 and new_dist < negative_dist[u]:
                    negative_dist[u] = new_dist
                    negative_path[u] = new_path
                    heapq.heappush(queue, (new_dist, u, -1, new_path))

        # Ermittlung der finalen Distanz/Pfad
        path = []
        distance = np.inf

        if target_vertex_value > 0:
            # Ziel > 0 => mögliche Pfade in positive_dist oder negative_dist
            if positive_dist[target_vertex_id] >= negative_dist[target_vertex_id] and negative_dist[target_vertex_id] < np.inf:
                distance = positive_dist[target_vertex_id]
                path = positive_path[target_vertex_id]
            else:
                distance = -negative_dist[target_vertex_id]
                path = negative_path[target_vertex_id]

        elif target_vertex_value < 0:
            # Ziel < 0 => ebenfalls Abgleich, aber ggf. negativ
            if positive_dist[target_vertex_id] > negative_dist[target_vertex_id] and positive_dist[target_vertex_id] < np.inf:
                distance = -positive_dist[target_vertex_id]
                path = positive_path[target_vertex_id]
            else:
                distance = negative_dist[target_vertex_id]
                path = negative_path[target_vertex_id]

        else:
            # target_vertex_value == 0 => Sonderfall
            # No Alarm etc. oder wir bewerten die Pfade evtl. als -np.inf
            if (positive_dist[target_vertex_id] < np.inf or negative_dist[target_vertex_id] < np.inf):
                # Es existieren Pfade
                if negative_path[target_vertex_id] and not positive_path[target_vertex_id]:
                    path = negative_path[target_vertex_id]
                elif not negative_path[target_vertex_id] and positive_path[target_vertex_id]:
                    path = positive_path[target_vertex_id]
                elif negative_path[target_vertex_id] and positive_path[target_vertex_id]:
                    # Suche kürzesten Pfad
                    min_path = [0]*100
                    if positive_path[target_vertex_id] and len(positive_path[target_vertex_id]) < len(min_path):
                        min_path = positive_path[target_vertex_id]
                    if negative_path[target_vertex_id] and len(negative_path[target_vertex_id]) < len(min_path):
                        min_path = negative_path[target_vertex_id]
                    path = min_path
                distance = -np.inf if len(path) > 0 else np.inf
            else:
                distance = np.inf
                # Falls Pfade existieren, wähle ggf. den kürzesten aus
                if negative_path[target_vertex_id] and not positive_path[target_vertex_id]:
                    path = negative_path[target_vertex_id]
                elif not negative_path[target_vertex_id] and positive_path[target_vertex_id]:
                    path = positive_path[target_vertex_id]
                elif negative_path[target_vertex_id] and positive_path[target_vertex_id]:
                    min_path = [0]*100
                    if positive_path[target_vertex_id] and len(positive_path[target_vertex_id]) < len(min_path):
                        min_path = positive_path[target_vertex_id]
                    if negative_path[target_vertex_id] and len(negative_path[target_vertex_id]) < len(min_path):
                        min_path = negative_path[target_vertex_id]
                    path = min_path

        # Bei "parameter" -> (distance, path)
        if dijkstra_type == "parameter":
            return (distance, path if path else [""])
        else:
            return distance

    def dfs(self, source_vertex_id, target_vertex_id, visited, weight):
        """
        Depth-First Search mit Multiplikation von 'weight'.
        Best_path & max_weight werden zurückgegeben, falls der Pfad 
        (source_vertex_id -> target_vertex_id) gefunden wird.

        Args:
            source_vertex_id (int): Startknoten
            target_vertex_id (int): Zielknoten
            visited (list[bool]): Gesehen-Markierung für Knoten, um Zyklen zu vermeiden
            weight (float): Aktuelles Gewicht (z.B. 1.0 am Anfang)

        Returns:
            (list[int], float): (bester Pfad, maximaler Pfadwert)
        """
        visited[source_vertex_id] = True
        path = [source_vertex_id]
        if source_vertex_id == target_vertex_id:
            return path, weight
        else:
            max_weight = weight
            best_path = []

            # Kanten, die ignoriert werden sollen (z.B. hierarchische Verknüpfungen)
            exclude_carriers = ["hasparent", "haschild", "Product"]

            for v in self.g.successors(source_vertex_id):
                edge_id = self.g.get_eid(source_vertex_id, v)
                edge_weight = self.g.es[edge_id]['weight']
                edge_carrier = self.g.es[edge_id]['carrier']

                # Nur Kanten mit Gewicht != 0, die nicht in exclude_carriers sind
                # und deren neuer Weight >= 0.1
                if edge_weight != 0 and edge_carrier not in exclude_carriers:
                    new_weight = weight * edge_weight
                    if not visited[v] and abs(new_weight) >= 0.1:
                        new_path, new_weight = self.dfs(v, target_vertex_id, visited, new_weight)
                        if new_weight > max_weight:
                            max_weight = new_weight
                            best_path = path + new_path

            visited[source_vertex_id] = False
            return best_path, max_weight

    def evaluate_alarm(self, source_vertex_id, target_vertex_id):
        """
        Ruft einen DFS-Aufruf auf (source_vertex_id -> target_vertex_id) 
        und gibt den besten Pfad und sein Gesamtgewicht zurück.

        Args:
            source_vertex_id (int)
            target_vertex_id (int)

        Returns:
            (list[int], float): Pfad (Knoten-IDs) und maximaler gefundener weight
        """
        visited = [False] * self.g.vcount()
        best_path, max_weight = self.dfs(source_vertex_id, target_vertex_id, visited, 1.0)
        return best_path, max_weight

    def generate_alarmPLUT(self):
        """
        Baut eine einfache Lookup-Tabelle (Matrix) aus allen aktiven Alarmen (AS != 0).
        Für jedes Alarm-Paar i, j wird ein Distanzwert via modified_dijkstra berechnet, 
        gewichtet mit dem jeweiligen AS-Wert.

        Returns:
            list[list[float]]: 2D-Liste (Matrix) mit Gewichten 
                               (z.B. alarm1 -> alarm2).
        """
        # Liste aller Vertex-Objekte, deren AS != 0
        vertices = [v for v in self.g.vs if v["AS"] != 0]

        # Initialisiere Matrix (Quadratisch: NxN, wobei N = len(vertices))
        weight_matrix = [[0]*len(vertices) for _ in range(len(vertices))]

        # Fülle die Matrix
        for i in range(len(vertices)):
            for j in range(len(vertices)):
                if i != j:
                    dist = self.modified_dijkstra(vertices[i].index, vertices[j].index)
                    weight_matrix[i][j] = vertices[i]["AS"] * dist * vertices[j]["AS"]

        return weight_matrix  # , path_matrix (falls du Pfade je Eintrag bräuchtest)

    def find_paths(self, carriercondition, carriermax):
        """
        Sucht Pfade im Graphen, die bestimmte carriercondition (z.B. ['hasparent','Product','haschild']) 
        mit maximalen Nutzungen carriermax (z.B. [3,1,3]) erfüllen.

        Returns:
            (list[list[int]], int): 
                - Liste von Pfaden (als Liste von Vertex-IDs),
                - totale Länge aller gefundenen Pfade
        """
        def check_path(g, path, carrier):
            carrier_count = 0
            for i in range(1, len(path)):
                edge_id = g.get_eid(path[i-1], path[i])
                if g.es[edge_id]['carrier'] == carrier:
                    carrier_count += 1
            # Zum Debuggen: if carrier_count > 1: print("...", path)
            return carrier_count if carrier_count > 1 else 0

        totallength = 0
        list_of_all_paths = []

        # Durchlaufe alle Vertices als Startpunkt
        for i in range(len(self.g.vs)):
            paths = self.explore_edges(i, carriercondition, carriermax)
            if paths:
                for path in paths:
                    # Optional: check_path zur Erkennung besonderer 'Product'-Kanten
                    if check_path(self.g, path, "Product"):
                        pass
                    totallength += len(path)
                    list_of_all_paths.append(path)

        # Filter: Pfade, bei denen nicht Start=Zielknoten
        return [p for p in list_of_all_paths if p[0] != p[-1]], totallength

    def explore_edges(self, source_vertex_id, carrierlist, carriermax,
                      used_carriers=None, vertex_path=None, carrier_index=0, carrier_count=0):
        """
        Rekursive Suche im Graphen nach Pfaden, die carrierlist in bestimmtem Maß (carriermax) nutzt.
        
        Args:
            source_vertex_id (int): Startknoten.
            carrierlist (list[str]): Liste der erwarteten carrier, z.B. ['hasparent','Product','haschild'].
            carriermax (list[int]): Liste der max. Nutzungsanzahl je carrier im Pfad.
            used_carriers (list[str]): Welche carrier bisher genutzt wurden.
            vertex_path (list[int]): Aktueller Pfad an Knoten-IDs.
            carrier_index (int): Index in carrierlist, welcher carrier gerade geprüft wird.
            carrier_count (int): wie oft dieser carrier bereits im Pfad genutzt wurde.

        Returns:
            list[list[int]]: Liste aller passenden Pfade (als Liste von Knoten-IDs).
        """
        all_paths = []
        if vertex_path is None:
            vertex_path = []
        if used_carriers is None:
            used_carriers = []

        vertex_path.append(source_vertex_id)

        # Wenn alle erwarteten carrier gebraucht wurden, ist Pfad gültig
        if set(used_carriers) == set(carrierlist):
            all_paths.append(list(vertex_path))

        # Selektiere alle Kanten vom aktuellen Knoten
        for edge in self.g.es.select(_source=source_vertex_id):
            if edge['carrier'] == carrierlist[carrier_index] and carrier_count < carriermax[carrier_index]:
                # Kopien von used_carriers und vertex_path zum Rekursionsaufruf
                new_used_carriers = used_carriers.copy()
                new_used_carriers.append(edge['carrier'])

                new_paths = self.explore_edges(
                    edge.target, carrierlist, carriermax,
                    new_used_carriers, vertex_path.copy(),
                    carrier_index, carrier_count + 1
                )
                if new_paths:
                    all_paths.extend(new_paths)

            # Erlaube Übergang zum nächsten Carrier in der Liste, wenn der jetzige bereits mindestens einmal genutzt wurde
            if carrier_count >= 1 and carrier_index + 1 < len(carrierlist) and edge['carrier'] == carrierlist[carrier_index + 1]:
                new_used_carriers = used_carriers.copy()
                new_used_carriers.append(edge['carrier'])

                new_paths = self.explore_edges(
                    edge.target, carrierlist, carriermax,
                    new_used_carriers, vertex_path.copy(),
                    carrier_index + 1, 1  # Da wir jetzt gerade zum nächsten carrier übergehen, count=1
                )
                if new_paths:
                    all_paths.extend(new_paths)

        return all_paths

    def apply_rule(self, source_type: str, target_type: str, rulenumber: int,
                   strength=0.99, effect_factor=1, time_constant=0,
                   rationale=None, apply_carrier=None, searchpath=None,
                   shortest=False, findValves=False, inverse=False):
        """
        Legt neue Kanten von source_type -> target_type anhand eines searchpaths an 
        und versieht sie mit carrier, weight=strength, rulenumber usw.

        Args:
            source_type (str): Carrier-Typ des Startknotens (z.B. "Temperature").
            target_type (str): Carrier-Typ des Zielknotens (z.B. "Flow").
            rulenumber (int): ID oder Nummer der Regel.
            strength (float): Grundgewicht der neu erzeugten Kante.
            effect_factor (float): lambda_factor.
            time_constant (float): tau, Zeitkonstante.
            rationale (str): Freitext-Begründung, falls gewünscht.
            apply_carrier (str): Falls eine bestimmte Carrier-Bezeichnung verwendet werden soll.
            searchpath (list[list[int]]): Liste von Pfaden, in denen gesucht wird (default: self.vertexpaths).
            shortest (bool): Ob nur der kürzeste Pfad betrachtet werden soll.
            findValves (bool): Ob während der Pfadkonstruktion "State"-Knoten gesucht und hinterlegt werden.
            inverse (bool): Ob die Kante rückwärts eingetragen wird (Ziel->Quelle statt Quelle->Ziel).

        Returns:
            int: Anzahl der erzeugten Kanten.
        """
        def determine_carrier(source_vertex, target_vertex, applied_carrier):
            # Falls Quelle und Ziel identischen Carrier haben, nimm diesen, sonst applied_carrier (default: "mixed")
            if source_vertex["Carrier"] == target_vertex["Carrier"]:
                return source_vertex["Carrier"]
            elif applied_carrier is not None:
                return applied_carrier
            else:
                return "mixed"

        if searchpath is None:
            # Falls kein Pfad übergeben, verwende self.vertexpaths (wird z.B. nach generate_graphfromAML gefüllt)
            searchpath = self.vertexpaths

        num_edges_added = 0

        # Selektiere alle Knoten, deren Carrier == source_type
        for source_vertex in self.g.vs.select(Carrier_eq=source_type):
            written = False
            valid_paths = [p for p in searchpath if p and p[0] == source_vertex.index]
            if not valid_paths:
                continue

            # Falls shortest=True => sortiere Pfade nach Länge
            if shortest:
                valid_paths.sort(key=len)

            # Selektiere alle Ziel-Knoten, deren Carrier == target_type
            for target_vertex in self.g.vs.select(Carrier_eq=target_type):
                for path in valid_paths:
                    if path and path[-1] == target_vertex.index:
                        # Falls findValves=True => Suche "State"-Knoten unterwegs
                        actors = []
                        if findValves:
                            for vertex_id in path[1:-1]:
                                vertex = self.g.vs[vertex_id]
                                # Prüfe alle Nachfolger
                                for child_id in self.g.successors(vertex_id):
                                    edge = self.g.es[self.g.get_eid(vertex_id, child_id)]
                                    if edge["carrier"] == "haschild":
                                        child = self.g.vs[child_id]
                                        if "State" in child["Tag"]:
                                            actors.append(child["Tag"])
                        else:
                            actors = None

                        current_carrier = determine_carrier(source_vertex, target_vertex, apply_carrier)

                        # Erzeuge neue Kante (rückwärts oder vorwärts)
                        if inverse:
                            self.g.add_edge(
                                path[-1], path[0],
                                carrier=current_carrier,
                                weight=strength,
                                rulenumber=rulenumber,
                                tau=time_constant,
                                lambda_factor=effect_factor,
                                rationale=rationale,
                                Actors=actors
                            )
                        else:
                            self.g.add_edge(
                                path[0], path[-1],
                                carrier=current_carrier,
                                weight=strength,
                                rulenumber=rulenumber,
                                tau=time_constant,
                                lambda_factor=effect_factor,
                                rationale=rationale,
                                Actors=actors
                            )
                        num_edges_added += 1
                        written = True
                        # Wenn shortest=True => nur den ersten passenden Pfad pro Zielknoten verwenden
                        if shortest:
                            break
                if shortest and written:
                    break

        return num_edges_added

######################################################################################################################################################################################################################################################################################
    def generate_distancematrix(self):
        """
        Erstellt eine Distanzmatrix zwischen allen aktiven Alarmen (AS != 0).
        Mit self.modified_dijkstra(...) wird der Distance-Wert bestimmt; 
        anschließend wird exp(-distance) in die Matrix eingetragen.
        
        Returns:
            tuple: (distance_matrix, edge_details_matrix)
               - distance_matrix: N x N numpy-Array der transformierten Distanzen
               - edge_details_matrix: N x N Liste, die zugehörige Edge-Details (Pfade) speichert
        """
        # Liste aller aktiven Alarmknoten
        active_alarm_list = [v for v in self.g.vs if v["AS"] != 0]

        # Separater Use Case: könnte man später nutzen
        possible_alarm_list = [v for v in self.g.vs if v["AS"] in (0, 1, -1)]

        # Init der Matrixen
        distance_matrix = np.zeros((len(active_alarm_list), len(active_alarm_list)))
        edge_details_matrix = [[[] for _ in range(len(active_alarm_list))] for _ in range(len(active_alarm_list))]

        for i in range(len(active_alarm_list)):
            for j in range(len(active_alarm_list)):
                if i != j:
                    # Verwende hier modified_dijkstra, das distance+edge_details+path zurückgibt
                    distance, edge_details, path = self.modified_dijkstra(active_alarm_list[i].index,
                                                                          active_alarm_list[j].index)
                    distance_matrix[i, j] = np.exp(-distance)
                    edge_details_matrix[i][j] = edge_details
                else:
                    # Diagonale = 0
                    distance_matrix[i, j] = 0

        self.current_distancematrix = distance_matrix
        self.current_activealarmlist = active_alarm_list
        return distance_matrix, edge_details_matrix

    def generate_statevariable_influence_matrix(self):
        """
        Erstellt eine quadratische Influence-Matrix zwischen allen Sensor-Knoten 
        (sensorlabel == 1). Falls sowohl Quell- als auch Zielknoten aktiv sind (AS != 0), 
        wird der Wert aus modified_dijkstra eingetragen (exp(-distance) bzw. 0).
        
        Returns:
            numpy.ndarray: Die NxN-Matrix statevariable_influence_matrix
        """
        # Alle Sensor-Knoten
        possible_alarm_list = [v for v in self.g.vs if v["sensorlabel"] == 1]
        # Nur die aktiven Sensor-Knoten (Alarmzustand != 0)
        active_alarm_list = [v for v in possible_alarm_list if v["AS"] != 0]

        # NxN Matrix (N = # sensorlabel-Knoten)
        statevariable_influence_matrix = np.zeros((len(possible_alarm_list), len(possible_alarm_list)))

        for i in range(len(possible_alarm_list)):
            for j in range(len(possible_alarm_list)):
                if i != j:
                    # Prüfen, ob beide Knoten überhaupt aktiv sind
                    if possible_alarm_list[i]["AS"] != 0 and possible_alarm_list[j]["AS"] != 0:
                        distance = self.modified_dijkstra(possible_alarm_list[i].index,
                                                          possible_alarm_list[j].index)
                        # Logik für negative oder -∞ Distanzen
                        if distance == -np.inf:
                            statevariable_influence_matrix[i, j] = 0
                        elif distance > 0:
                            statevariable_influence_matrix[i, j] = np.exp(-distance)
                        else:
                            statevariable_influence_matrix[i, j] = 0
                else:
                    # Diagonale = 1
                    statevariable_influence_matrix[i, j] = 1

        self.current_statevariable_influence_matrix = statevariable_influence_matrix
        self.current_activealarmlist = active_alarm_list
        return statevariable_influence_matrix

    def generate_parameterinfluence_matrix(self):
        """
        Erstellt eine (parameter_list x possible_alarm_list)-Matrix. Jeder Eintrag
        basiert auf der modified_dijkstra-Distanz von einem Parameter-Knoten 
        zu einem Alarm-Knoten (sensorlabel != 0) im Modus dijkstra_type="parameter". 
        
        Berücksichtigt außerdem: 
        - pathlänge => exponentieller Faktor 
        - Abweichung (deviation) => Skaliert den Wert
        
        Returns:
            numpy.ndarray: 2D-Matrix [#Parameter x #Sensor]
        """
        # Aktive Alarme (AS != 0)
        active_alarm_list = [v for v in self.g.vs if v["AS"] != 0]

        # Alle Knoten mit sensorlabel != 0 (muss nicht zwingend AS != 0 sein)
        possible_alarm_list = [v for v in self.g.vs if v["sensorlabel"] != 0]

        # Parameter-Knoten (parameterlabel != 0)
        parameter_list = [v for v in self.g.vs if v["parameterlabel"] != 0]

        # Matrix: Zeilen = Parameter, Spalten = Sensor/Alarm-Knoten
        parameter_influence_matrix = np.zeros((len(parameter_list), len(possible_alarm_list)))
        parameter_pathlength_matrix = np.zeros((len(parameter_list), len(possible_alarm_list)))

        # List für "neutrale" Parameter, die kaum Einfluss haben
        parameter_neutral_influencelist = [0] * len(parameter_list)

        # 1) Fülle raw distance
        for i in range(len(parameter_list)):
            for j in range(len(possible_alarm_list)):
                # Nur wenn Knoten existiert
                if possible_alarm_list[j]["AS"] is not None:
                    # dijkstra_type="parameter" => modified_dijkstra liefert (distance, path)
                    distance, path = self.modified_dijkstra(parameter_list[i].index,
                                                            possible_alarm_list[j].index,
                                                            dijkstra_type="parameter")
                    parameter_pathlength_matrix[i, j] = len(path) if len(path) > 0 else 1

                    # Fälle für distance
                    if distance == -np.inf:
                        parameter_neutral_influencelist[i] += 1
                        parameter_influence_matrix[i, j] = 0
                    elif distance > 0:
                        parameter_influence_matrix[i, j] = np.exp(-distance)
                    else:
                        parameter_influence_matrix[i, j] = -np.exp(distance)

            # factor_influence = Summe der absoluten Spaltenwerte => später zur Normalisierung
            factor_influence = [0] * len(possible_alarm_list)
            for col_idx in range(len(possible_alarm_list)):
                factor_influence[col_idx] = sum(abs(parameter_influence_matrix[:, col_idx]))
                if factor_influence[col_idx] <= 1:
                    factor_influence[col_idx] = 1

            # range_from_sensor_factor = mittlere Pfadlänge der Parameter-Reihe
            range_from_sensor_factor = [0] * len(parameter_list)
            for pi in range(len(parameter_list)):
                range_from_sensor_factor[pi] = np.mean(parameter_pathlength_matrix[pi, :])

        # 2) Multiplikation mit Deviation, NeutralFactor usw.
        for j in range(len(possible_alarm_list)):
            for i in range(len(parameter_list)):
                # possible_alarm_list[j]["deviation"] => Skaliert den Wert
                dev = abs(possible_alarm_list[j]["deviation"]) 
                param_influence = parameter_influence_matrix[i, j]

                # exponent. Faktoren:
                #   - 0.9^(count neutral) => je öfter neutral, desto kleiner
                #   - 1.1^(range_mean)   => je weiter entfernt, desto größer
                param_influence *= dev
                param_influence *= np.power(0.9, parameter_neutral_influencelist[i])
                param_influence *= np.power(1.1, range_from_sensor_factor[i])
                param_influence /= factor_influence[j]

                parameter_influence_matrix[i, j] = param_influence

        # Setze Klassen-Attribute für Weiterverarbeitung
        self.current_parameter_influence_matrix = parameter_influence_matrix
        self.current_activealarmlist = active_alarm_list
        self.current_parameter_list = parameter_list
        self.possible_alarm_list = possible_alarm_list
        self.current_parameter_neutral_influencelist = parameter_neutral_influencelist
        
        return parameter_influence_matrix

    def generate_distance(self, i, active_alarm_list, distance_matrix):
        """
        Worker-Funktion für Multithreading. 
        Berechnet exp(-distance) von active_alarm_list[i].index zu allen j 
        (falls i != j).

        Args:
            i (int): Zeilenindex im distance_matrix.
            active_alarm_list (list[igraph.Vertex]): Liste aller aktiven Alarmknoten.
            distance_matrix (np.ndarray): Gemeinsame Distanzmatrix zum Befüllen.
        """
        for j in range(len(active_alarm_list)):
            if i != j:
                dist = self.modified_dijkstra(active_alarm_list[i].index, 
                                              active_alarm_list[j].index)
                distance_matrix[i, j] = np.exp(-dist)
            else:
                distance_matrix[i, j] = 0

    def evaluate_distance_matrix(self, distance_limit, update_distance=False):
        """
        Erzeugt zuerst State-Variable- und Parameter-Influence-Matrizen und 
        kombiniert sie anschließend in self.current_combined_distance_matrix.
        
        Args:
            distance_limit (float): Schwellwert für Distanzvergleiche (aktuell nicht verwendet).
            update_distance (bool): Falls True, könnte ggf. generate_distancematrix_multithreaded() aufgerufen werden.

        Returns:
            tuple: (distance_matrix, parameter_influence_matrix, parameter_names_total, 
                    statevariable_names_total, parameter_names_with_influence, statevariable_names_with_influence)
        """
        # STEP 1: Influence Matrix für Statevariablen
        self.generate_statevariable_influence_matrix()

        # STEP 2: Influence Matrix für Parameter auf State-Variablen
        self.generate_parameterinfluence_matrix()
        # Optional: self.generate_distancematrix() oder self.generate_distancematrix_multithreaded()

        parameter_influence_matrix = self.current_parameter_influence_matrix
        statevariable_influence_matrix = self.current_statevariable_influence_matrix

        # Kombinierte Distance Matrix (Zeilen = Parameter, Spalten = Sensor/Alarm)
        combined_distance_matrix = np.zeros((parameter_influence_matrix.shape[0], 
                                             parameter_influence_matrix.shape[1]))

        ratio = [0]*statevariable_influence_matrix.shape[1]
        for j in range(statevariable_influence_matrix.shape[1]):
            sum_col = np.sum(statevariable_influence_matrix[:, j])
            sum_row = np.sum(statevariable_influence_matrix[j, :])
            # Falls sum_col zu klein => Erhöhe manuell, damit Division nicht 0 wird
            if sum_col < 0.1:
                sum_col = 0.1
            ratio[j] = sum_row / sum_col

            # Summation: ratio[j] * param_influence + param_influence
            # => param_influence * (ratio[j] + 1)
            combined_distance_matrix[:, j] = parameter_influence_matrix[:, j] * (ratio[j] + 1)

        self.current_combined_distance_matrix = combined_distance_matrix
        distance_matrix = self.current_combined_distance_matrix

        if distance_matrix is None:
            return "Invalid distance matrix"

        # Bestimme, welche Parameter Namen haben und ob sie in Summe != 0 aufweisen
        parameter_names_total = []
        parameter_names_with_influence = []
        parameter_names_without_influence = []

        for row_idx in range(distance_matrix.shape[0]):
            param_tag = self.current_parameter_list[row_idx]["Tag"]
            parameter_names_total.append(param_tag)
            row_sum = sum(distance_matrix[row_idx, :])
            if row_sum != 0:
                parameter_names_with_influence.append(param_tag)
            else:
                parameter_names_without_influence.append(param_tag)

        # Bestimme Sensor-/Alarm-Knotennamen
        statevariable_names_total = []
        statevariable_names_with_influence = []
        statevariable_names_without_influence = []

        for col_idx in range(distance_matrix.shape[1]):
            sensor_tag = self.possible_alarm_list[col_idx]["Tag"]
            statevariable_names_total.append(sensor_tag)
            column_sum = sum(distance_matrix[:, col_idx])
            if column_sum != 0:
                statevariable_names_with_influence.append(sensor_tag)
            else:
                statevariable_names_without_influence.append(sensor_tag)

        return (distance_matrix,
                parameter_influence_matrix,
                parameter_names_total,
                statevariable_names_total,
                parameter_names_with_influence,
                statevariable_names_with_influence)

    def add_sensorlabels(self, alarmstates_dict):
        """
        Setzt für alle in alarmstates_dict enthaltenen Knoten das Attribut sensorlabel=1.
        
        Args:
            alarmstates_dict (dict): key=Tag, value=AS-Wert (o.ä.) 
        """
        for key in alarmstates_dict:
            idx = self.g.vs["Tag"].index(key)
            self.g.vs[idx]["sensorlabel"] = 1

    def set_alarmstates(self, alarmstates_dict):
        """
        Weist jedem Knoten aus alarmstates_dict["Tag"] den AS-Wert zu.
        
        Args:
            alarmstates_dict (dict): key=Tag, value=AS (Alarmstatus).
        """
        for key in alarmstates_dict:
            idx = self.g.vs["Tag"].index(key)
            self.g.vs[idx]["AS"] = alarmstates_dict[key]

    def set_deviations(self, deviation_dict):
        """
        Setzt das "deviation"-Attribut für alle Knoten, die im deviation_dict enthalten sind.
        
        Args:
            deviation_dict (dict): key=Tag, value=Abweichung
        """
        for key in deviation_dict:
            idx = self.g.vs["Tag"].index(key)
            self.g.vs[idx]["deviation"] = deviation_dict[key]
    
    def generate_interactive_graph(self, output_file="interactive_graph.html", height="1100px"):
        # Konvertieren des igraph-Graphen in einen networkx-Graphen
        G_nx = nx.DiGraph()
        # Knoten hinzufügen
        for v in self.g.vs:
            G_nx.add_node(v.index, label=v["Tag"], carrier=v["Carrier"])
        # Kanten hinzufügen mit Gewicht als Attribut
        for e in self.g.es:
            source = e.source
            target = e.target
            G_nx.add_edge(source, target, carrier=e["carrier"], weight=e["weight"])
        # Interaktive Visualisierung mit PyVis
        net = Network(notebook=False, directed=True, width="100%", height=height, cdn_resources='in_line', select_menu=True, filter_menu=True)
        # Physik-Layout aktivieren
        net.force_atlas_2based()
        # Farbzuordnung für Knoten
        color_dict = {
            "Temperature": "red",
            "Pressure": "green",
            "Flow": "blue",
            "Level": "yellow",
            "State": "gray",
            "hierarch": "lightgray",
            "hasparent": "orange",
            "haschild": "purple",
            "Product": "cyan",
            "hasalarm": "pink",
            "isalarm": "brown",
            "thermal_connection": "olive",
            "control": "navy",
            "PumpRotationalSpeed": "teal",
            "PressureDropNominal": "gold",
            "Diameter": "darkgreen",
            "HeightDifference": "darkred",
            "Roughness": "darkblue",
            "Length": "darkorange",
            "Area": "darkviolet",
            "MFlowNominal": "darkgray",
        }
        # Knoten hinzufügen
        for node, data in G_nx.nodes(data=True):
            net.add_node(
                node,
                label=data["label"],
                title=f"Carrier: {data['carrier']}",
                color=color_dict.get(data["carrier"], "lightgray")
            )
        # Kanten hinzufügen mit Gewicht als Label und Farbe basierend auf dem Gewicht
        for source, target, data in G_nx.edges(data=True):
            weight = data.get('weight', 1)  # Standardwert 1, falls kein Gewicht vorhanden
            edge_color = 'green' if weight >= 0 else 'red'
            net.add_edge(
                source,
                target,
                title=f"Carrier: {data['carrier']}<br>Gewicht: {weight}",
                label=str(weight),
                color=edge_color
            )

        # Kanten glätten
        net.set_edge_smooth('dynamic')

        # Erstellen der HTML-Datei mit UTF-8 Encoding
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(net.generate_html())

        print(f"Der interaktive Graph wurde in '{output_file}' gespeichert.")

######################################################################################################################################################################################################################################################################################


######################### MAIN #########################
"""
if __name__ == "__main__":
    t0 = time.time()
    # Beispiel
    aml_file = Config.aml_file
    graph_output_path = r"D:/WMA/06 Implementierungen/git_Projekte/AVEDAS/Scripts/Artefact_2/Resources/Testcases/ModVA_Testcases/Testcase_1/graph_output.html"
    dcdg = DCDG_Class()
    dcdg.generate_graphfromAML(aml_file)
    dcdg.generate_interactive_graph(output_file=graph_output_path)

    # Konvertieren des igraph-Graphen in einen networkx-Graphen
    G_nx = nx.DiGraph()

    # Knoten hinzufügen
    for v in dcdg.g.vs:
        G_nx.add_node(v.index, label=v["Tag"], carrier=v["Carrier"])

    # Kanten hinzufügen mit Gewicht als Attribut
    for e in dcdg.g.es:
        source = e.source
        target = e.target
        G_nx.add_edge(source, target, carrier=e["carrier"], weight=e["weight"])

    # Interaktive Visualisierung mit PyVis
    net = Network(notebook=False, directed=True, width="100%", height="1100px", cdn_resources='in_line', select_menu=True, filter_menu=True)

    # Physik-Layout aktivieren
    net.force_atlas_2based()

    # Farbzuordnung für Knoten
    color_dict = {
    "Temperature": "red",
    "Pressure": "green",
    "Flow": "blue",
    "Level": "yellow",
    "State": "gray",
    "hierarch": "lightgray",
    "hasparent": "orange",
    "haschild": "purple",
    "Product": "cyan",
    "hasalarm": "pink",
    "isalarm": "brown",
    "thermal_connection": "olive",
    "control": "navy",
    "PumpRotationalSpeed": "teal",
    "PressureDropNominal": "gold",
    "Diameter": "darkgreen",
    "HeightDifference": "darkred",
    "Roughness": "darkblue",
    "Length": "darkorange",
    "Area": "darkviolet",
    "MFlowNominal": "darkgray",
    # Weitere Carrier-Typen hinzufügen, falls vorhanden
}

    # Knoten hinzufügen
    for node, data in G_nx.nodes(data=True):
        net.add_node(
            node,
            label=data["label"],
            title=f"Carrier: {data['carrier']}",
            color=color_dict.get(data["carrier"], "lightgray")
        )

    # Kanten hinzufügen mit Gewicht als Label und Farbe basierend auf dem Gewicht
    for source, target, data in G_nx.edges(data=True):
        # Extrahieren des Gewichts
        weight = data.get('weight', 1)  # Standardwert 1, falls kein Gewicht vorhanden
        # Festlegen der Kantenfarbe basierend auf dem Gewicht
        if weight >= 0:
            edge_color = 'green'  # Positive Gewichte
        else:
            edge_color = 'red'    # Negative Gewichte
        # Kante hinzufügen mit Label
        net.add_edge(
            source,
            target,
            title=f"Carrier: {data['carrier']}<br>Gewicht: {weight}",
            label=str(weight),
            color=edge_color
        )

    # Kanten glätten
    net.set_edge_smooth('dynamic')

    # Erstellen der HTML-Datei mit UTF-8 Encoding
    with open("interactive_graph.html", "w", encoding="utf-8") as f:
        f.write(net.generate_html())

    t1 = time.time()
    totaltime = t1 - t0
    print(f"Code-Ausführung dauerte: {totaltime} Sekunden")
    print("Der interaktive Graph wurde in 'interactive_graph.html' gespeichert.")
    """