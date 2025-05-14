import igraph as ig
import Arroyo_DCDG_PLUT as arroyo

class IGraphConverter:
    """
    Wrappt einen existierenden DCDG_Class-Graph oder igraph.Graph und legt eine saubere Kopie an.
    Behandelt bidirektionale Mappings zwischen Original- und Converter-Indizes für Vertices und Edges.
    """

    def __init__(self, source):
        if hasattr(source, 'g') and isinstance(source.g, ig.Graph):
            orig_graph = source.g
        elif isinstance(source, ig.Graph):
            orig_graph = source
        else:
            raise TypeError("Source must be a DCDG_Class instance or an igraph.Graph")

        self.orig     = orig_graph
        self.directed = orig_graph.is_directed()

        self.vid_map     = {}
        self.inv_vid_map = {}
        self.eid_map     = {}
        self.inv_eid_map = {}

        # Neuer, leerer Graph
        self.g = ig.Graph(n=orig_graph.vcount(), directed=self.directed)

        # Vertex‐Attribute kopieren und mapping füllen
        for attr in orig_graph.vs.attribute_names():
            self.g.vs[attr] = orig_graph.vs[attr]
        for vid in range(orig_graph.vcount()):
            self.vid_map[vid]    = vid
            self.inv_vid_map[vid] = vid

        # Edge‐Kopie inkl. Attribute und mapping
        for orig_eid in range(orig_graph.ecount()):
            orig_e = orig_graph.es[orig_eid]
            src, dst = orig_e.tuple

            added = self.g.add_edge(self.vid_map[src], self.vid_map[dst])
            if isinstance(added, ig.Edge):
                new_eid = added.index
            else:
                new_eid = self.g.ecount() - 1

            for attr in orig_graph.es.attribute_names():
                self.g.es[new_eid][attr] = orig_e[attr]

            self.eid_map[orig_eid]    = new_eid
            self.inv_eid_map[new_eid] = orig_eid

        self.g.vs['converter_vid'] = list(range(self.g.vcount()))
        self.g.es['converter_eid'] = list(range(self.g.ecount()))

    # ————— Hilfsmethoden für Mapping —————

    def orig_vid(self, new_vid: int) -> int:
        return self.inv_vid_map[new_vid]

    def new_vid(self, orig_vid: int) -> int:
        return self.vid_map[orig_vid]

    def orig_eid(self, new_eid: int) -> int:
        return self.inv_eid_map[new_eid]

    def new_eid(self, orig_eid: int) -> int:
        return self.eid_map[orig_eid]

    # ————— Attribute ändern in beiden Graphen —————

    def update_vertex_attr(self, orig_vid: int, attr: str, value):
        new_vid = self.new_vid(orig_vid)
        self.orig.vs[orig_vid][attr] = value
        self.g.vs[new_vid][attr]     = value

    def update_edge_attr(self, orig_eid: int, attr: str, value):
        new_eid = self.new_eid(orig_eid)
        self.orig.es[orig_eid][attr] = value
        self.g.es[new_eid][attr]     = value

    # ————— Attribute abfragen in beiden Graphen —————
    def get_all_vertex_attributes(self) -> dict[int, dict]:
        """
        Gibt zurück: { new_vid: {attr_name: attr_value, ...}, ... }
        """
        result = {}
        for vid in range(self.g.vcount()):
            result[vid] = {attr: self.g.vs[vid][attr] for attr in self.g.vs.attribute_names()}
        return result

    def get_all_edge_attributes(self) -> dict[int, dict]:
        """
        Gibt zurück: { new_eid: {attr_name: attr_value, ...}, ... }
        """
        result = {}
        for eid in range(self.g.ecount()):
            result[eid] = {attr: self.g.es[eid][attr] for attr in self.g.es.attribute_names()}
        return result
    
    # ————— Graph-View ohne Carrier —————
    def get_filtered_subgraph_with_mapping(self, carrier: str, remove_isolated:bool = True) -> tuple[ig.Graph, dict[int, int], dict[int, int]]:
        """
        Erzeugt einen echten Subgraph (copy), in dem alle
        Vertices mit Vertex['Carrier']==carrier und alle
        inzidenten Edges wegfallen – liefert zusätzlich
        zwei Dicts zum Zurück-Mapping auf converter.g:

          - vid_map_sub: new_vid (im Subgraph) → old_vid (in self.g)
          - eid_map_sub: new_eid (im Subgraph) → old_eid (in self.g)
        """
        keep_vs = [v.index for v in self.g.vs if v['Carrier'] != carrier]

        sub = self.g.induced_subgraph(keep_vs)

        vid_map_sub = {new: old for new, old in enumerate(keep_vs)}

        eid_map_sub = {
            new_eid: sub.es[new_eid]['converter_eid']
            for new_eid in range(sub.ecount())
        }

        if remove_isolated:
            isolates = [v.index for v in sub.vs if sub.degree(v.index) == 0]
            if isolates:
                final_vs = [i for i in range(sub.vcount()) if i not in isolates]
                final_sub = sub.induced_subgraph(final_vs)

                base_map = vid_map_sub

                vid_map_sub = {
                    new: base_map[old]
                    for new, old in enumerate(final_vs)
                }

                eid_map_sub = {
                    new_eid: final_sub.es[new_eid]['converter_eid']
                    for new_eid in range(final_sub.ecount())
                }

                sub = final_sub


        return sub, vid_map_sub, eid_map_sub
    
    def split_nodes_by_carrier(self, graph, parameter_carriers: list[str]) -> tuple[list[int], list[int]]:
        """
        Trennt Parameter- von Sensor-Knoten anhand ihres 'Carrier'-Attributs.

        :param parameter_carriers: Liste von Carrier-Strings, die Parameter-Knoten kennzeichnen.
        :return: Tuple (parameter_nodes, sensor_nodes), je Liste der neuen_vids graph
        """
        # alle Vertices sammeln
        param_nodes = []
        sensor_nodes = []
        for v in graph.vs:
            carrier = v.attributes().get('Carrier', None)
            if carrier in parameter_carriers:
                param_nodes.append(v.index)
            else:
                sensor_nodes.append(v.index)
        return param_nodes, sensor_nodes

    # ————— Übersicht —————

    def summary(self):
        print("--- Converter Graph Summary ---")
        print(self.g.summary())

        vattrs = set(self.g.vs.attribute_names())
        has_tag = 'Tag' in vattrs

        print("Vertices (new_vid <-> orig_vid <-> Tag):")
        for new_vid, orig_vid in self.inv_vid_map.items():
            tag = self.g.vs[new_vid]['Tag'] if has_tag else '<no Tag>'
            print(f"  new {new_vid:2d} <-> orig {orig_vid:2d} : Tag={tag}")

        print("Edges (new_eid <-> orig_eid <-> src->dst):")
        for new_eid, orig_eid in self.inv_eid_map.items():
            src, dst     = self.g.es[new_eid].tuple
            o_src, o_dst = self.orig.es[orig_eid].tuple
            print(f"  new {new_eid:2d} <-> orig {orig_eid:2d} : {src}->{dst} (orig {o_src}->{o_dst})")


if __name__ == "__main__":
    # 1) AML laden
    aml_file = r'ModVA_Mixer_incl_SensorNamingConvention_reduced.aml'
    dcdg = arroyo.DCDG_Class()
    dcdg.generate_graphfromAML(aml_file)

    # 2) Converter erzeugen
    converter = IGraphConverter(dcdg)

    # 2) Sub-Graph ohne 'hierarch'-Knoten holen
    sub, vid_map_sub, eid_map_sub = converter.get_filtered_subgraph_with_mapping('hierarch', True)

    param_carrier_list = ["Height", "Area", "Diameter", "Roughness", "HDiff"]
    params, sensors = converter.split_nodes_by_carrier(sub, param_carrier_list)
    
    layout = converter.g.layout(layout="auto")
    ig.plot(converter.g, layout=layout, bbox=(0,0,5600,5600), vertex_label=converter.g.vs["Tag"], vertex_size=20, edge_width=0.5, target="myfile.pdf")

    layout = sub.layout(layout="auto")
    ig.plot(sub, layout=layout, bbox=(0,0,5600,5600), vertex_label=sub.vs["Tag"], vertex_size=20, edge_width=0.5, target="myfile_sub.pdf")


