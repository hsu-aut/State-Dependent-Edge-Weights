import igraph as ig
from pgmpy.models import DynamicBayesianNetwork as DBN
from graph_copy_for_dbn import IGraphConverter
import Arroyo_DCDG_PLUT as arroyo
import GRAPH_CONFIG as GRAPH_CONFIG
from typing import Dict, List, Tuple, Optional



class DBNConverter:
    def __init__(
        self,
        sub_graph: ig.Graph,
        vid_map_sub: Dict[int, int],
        eid_map_sub: Dict[int, int],
        converter: "IGraphConverter",
    ):
        self.sub = sub_graph
        self.vid_map_sub = vid_map_sub 
        self.eid_map_sub = eid_map_sub 
        self.converter = converter

        self.original_graph_node_count = sub_graph.vcount()

        self.sensor_nodes_t0: List[Tuple[str, int]] = []
        self.sensor_nodes_t1: List[Tuple[str, int]] = []
        self.param_node_tuples_map: Dict[int, Tuple[str, int]] = {} # Maps original sub_graph v_id to param DBN node tuple

        self.inter_eid_map: Dict[int, Tuple[int, int]] = {} # For original edge ID mapping (optional)
        self.param_eid_map: Dict[int, int] = {}            # For original edge ID mapping (optional)
        
        self._all_dbn_edges_collected: List[Tuple[Tuple[str, int], Tuple[str, int]]] = []
        self.dbn_edge_to_original_graph_eid_map: Dict[Tuple[Tuple[str, int], Tuple[str, int]], int] = {}


        # Store original sensor and parameter vertex IDs from the subgraph for plotting
        self._sensor_vids_in_sub: List[int] = []
        self._param_vids_in_sub: List[int] = []
        
        # Layout related attributes
        self._raw_layout: Optional[ig.Layout] = None
        self._layout2d: Optional[List[List[float]]] = None

        if self.sub.vcount() > 0:
            self._raw_layout = self.sub.layout("fr")
        else:
            self._raw_layout = ig.Layout([])


    def _prepare_node_definitions(self, sensor_vids: List[int], param_vids: List[int]):
        """
        Prepares DBN node definitions (base_tag for sensors, tag(param) for parameters)
        and stores them in class attributes.
        `sensor_vids` and `param_vids` are vertex indices from self.sub.
        """
        self.sensor_nodes_t0 = []
        self.sensor_nodes_t1 = []
        self.param_node_tuples_map = {}

        vid_to_tag_map = {v.index: v["Tag"] for v in self.sub.vs if "Tag" in v.attributes()}

        for v_id in sensor_vids:
            if v_id not in vid_to_tag_map: continue # Skip if tag is missing
            base_tag = vid_to_tag_map[v_id]
            self.sensor_nodes_t0.append((base_tag, 0))
            self.sensor_nodes_t1.append((base_tag, 1))

        for v_id in param_vids:
            if v_id not in vid_to_tag_map: continue # Skip if tag is missing
            base_tag = vid_to_tag_map[v_id]
            param_name = f"{base_tag}(param)"
            self.param_node_tuples_map[v_id] = (param_name, 0)

    def _get_original_graph_eid(self, sub_edge_idx: int) -> Optional[int]:
        """Hilfsmethode, um die original_graph_eid für eine sub_edge_idx zu bekommen."""
        converter_g_eid = self.eid_map_sub.get(sub_edge_idx)
        if converter_g_eid is not None:
            # converter.orig_eid() erwartet die ID aus converter.g
            return self.converter.orig_eid(converter_g_eid)
        return None

    def _collect_interslice_edges(self, sensor_vids: List[int]):
        vid_to_tag_map = {v.index: v["Tag"] for v in self.sub.vs if "Tag" in v.attributes()}
        sensor_vids_set = set(sensor_vids)

        for edge_obj in self.sub.es: # edge_obj.index ist die sub_eid
            u_vid, v_vid = edge_obj.tuple

            if u_vid in sensor_vids_set and v_vid in sensor_vids_set:
                if u_vid not in vid_to_tag_map or v_vid not in vid_to_tag_map: continue

                tag_u = vid_to_tag_map[u_vid]
                tag_v = vid_to_tag_map[v_vid]
                
                src_node = (tag_u, 0)
                dst_node = (tag_v, 1)
                dbn_edge = (src_node, dst_node)
                self._all_dbn_edges_collected.append(dbn_edge)
                
                # NEU: Original Edge ID speichern
                original_graph_eid = self._get_original_graph_eid(edge_obj.index)
                if original_graph_eid is not None and dbn_edge not in self.dbn_edge_to_original_graph_eid_map:
                    self.dbn_edge_to_original_graph_eid_map[dbn_edge] = original_graph_eid
        
        # Selbst-Transitionen für Sensoren haben keine direkte Entsprechung
        for v_id in sensor_vids:
            if v_id not in vid_to_tag_map: continue
            tag_u = vid_to_tag_map[v_id]
            src_node = (tag_u, 0)
            dst_node = (tag_u, 1)
            dbn_edge = (src_node, dst_node)
            if dbn_edge not in self._all_dbn_edges_collected: # vermeide Duplikate falls u_vid == v_vid oben
                self._all_dbn_edges_collected.append(dbn_edge)


    def _collect_parameter_edges(self, param_vids: List[int], sensor_vids: List[int]):
        vid_to_tag_map = {v.index: v["Tag"] for v in self.sub.vs if "Tag" in v.attributes()}
        param_vids_set = set(param_vids)
        sensor_vids_set = set(sensor_vids)

        for edge_obj in self.sub.es: # edge_obj.index ist die sub_eid
            u_vid, v_vid = edge_obj.tuple

            if u_vid in param_vids_set and v_vid in sensor_vids_set:
                param_node_tuple = self.param_node_tuples_map.get(u_vid)
                if not param_node_tuple or v_vid not in vid_to_tag_map:
                    continue 
                
                sensor_base_tag_v = vid_to_tag_map[v_vid]
                original_graph_eid = self._get_original_graph_eid(edge_obj.index) # Hole die orig_eid

                # a) Kante zu Sensor in Slice t-1 (slice 0)
                sensor_node_t0 = (sensor_base_tag_v, 0)
                dbn_edge_t0 = (param_node_tuple, sensor_node_t0)
                self._all_dbn_edges_collected.append(dbn_edge_t0)
                if original_graph_eid is not None and dbn_edge_t0 not in self.dbn_edge_to_original_graph_eid_map:
                    self.dbn_edge_to_original_graph_eid_map[dbn_edge_t0] = original_graph_eid

                # b) Kante zu Sensor in Slice t (slice 1)
                sensor_node_t1 = (sensor_base_tag_v, 1)
                dbn_edge_t1 = (param_node_tuple, sensor_node_t1)
                self._all_dbn_edges_collected.append(dbn_edge_t1)
                if original_graph_eid is not None and dbn_edge_t1 not in self.dbn_edge_to_original_graph_eid_map:
                    # Dieselbe original_graph_eid mappt hier zu einer *anderen* DBN Kante
                    self.dbn_edge_to_original_graph_eid_map[dbn_edge_t1] = original_graph_eid

    def build(self, sensor_vids: List[int], param_vids: List[int]) -> Tuple[DBN, Dict, Dict]:
        """
        Builds the DBN model.
        `sensor_vids` and `param_vids` are vertex indices from `self.sub`.
        """
        self._all_dbn_edges_collected = []
        self.inter_eid_map = {} 
        self.param_eid_map = {}
        self.dbn_edge_to_original_graph_eid_map = {} # Zurücksetzen für jeden Build

        # Store original vids for plotting reference
        self._sensor_vids_in_sub = sensor_vids[:]
        self._param_vids_in_sub = param_vids[:]

        self._prepare_node_definitions(sensor_vids, param_vids)
        self._collect_interslice_edges(sensor_vids)
        self._collect_parameter_edges(param_vids, sensor_vids)
        
        # Remove duplicate edges before creating DBN, as pgmpy might handle them but it's cleaner.
        unique_edges = sorted(list(set(self._all_dbn_edges_collected)))
        self._all_dbn_edges_collected = unique_edges

        dbn_model = DBN()
        if self._all_dbn_edges_collected:
            dbn_model.add_edges_from(self._all_dbn_edges_collected)
        else:
            all_nodes = self.sensor_nodes_t0 + self.sensor_nodes_t1 + list(self.param_node_tuples_map.values())
            if all_nodes:
                dbn_model.add_nodes_from(list(set(all_nodes)))


        return dbn_model, self.dbn_edge_to_original_graph_eid_map

    # --------------------- Plotting --------------------
    def _compute_scaled_layout(self, bbox: Tuple[float, float]):
        if self._raw_layout is None:
            if self.sub.vcount() > 0:
                self._raw_layout = self.sub.layout("fr")
            else: # Handle empty graph case
                self._layout2d = []
                return
        
        # Create a mutable copy for fit_into
        layout_copy = self._raw_layout.copy()
        
        # Check if layout has coordinates
        if not layout_copy.coords or len(layout_copy.coords[0])==0 : # no coords or empty coords
             if self.sub.vcount() > 0: # if there are vertices, attempt to generate coords
                 # Fallback if raw_layout was somehow empty despite vertices
                 layout_copy = self.sub.layout("fr").copy() 
                 if not layout_copy.coords and self.sub.vcount() > 0: # Still no coords
                     # Create dummy coordinates if layout fails for a non-empty graph
                     layout_copy.coords = [[i * 10, i * 10] for i in range(self.sub.vcount())]
             else: # No vertices, no coords
                 self._layout2d = []
                 return

        layout_copy.fit_into(bbox, keep_aspect_ratio=False)
        self._layout2d = layout_copy.coords


    def plot_interactive(
        self,
        filename: str = "dbn_plot.html",
        z_step: float = 1.0,
        marker_size: int = 6,
        bbox: tuple[float, float] = (5000, 5000),
    ):
        import plotly.graph_objects as go

        if self.sub.vcount() == 0:
            print("Subgraph is empty, cannot generate plot.")
            # Create an empty plot or just return
            fig = go.Figure()
            fig.update_layout(title_text="Empty DBN (No nodes in subgraph)", scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Time"))
            fig.write_html(filename)
            print(f"Empty plot saved: {filename}")
            return

        if self._layout2d is None or not self._layout2d: # Ensure layout is computed using the passed bbox
            self._compute_scaled_layout(bbox)
        
        if not self._layout2d: # If layout computation failed or graph is empty
            print("Layout not available, cannot plot.")
            return


        xs, ys, zs = [], [], []
        node_labels = [] # Renamed from 'labels' to avoid conflict
        node_plot_types = []  # 'param' or 'sensor'
        pos_index: Dict[Tuple[str, int], int] = {} # Maps DBN node tuple to index in xs,ys,zs

        # 1. Prepare DBN node coordinates and attributes for plotting
        vid_to_tag_map = {v.index: v["Tag"] for v in self.sub.vs if "Tag" in v.attributes()}

        # Parameters (only in slice 0)
        for orig_v_id in self._param_vids_in_sub:
            dbn_param_node = self.param_node_tuples_map.get(orig_v_id)
            if dbn_param_node and orig_v_id < len(self._layout2d):
                x, y = self._layout2d[orig_v_id]
                current_plot_idx = len(xs)
                pos_index[dbn_param_node] = current_plot_idx
                
                xs.append(x)
                ys.append(y)
                zs.append(0.0) # Parameters are at z=0
                node_labels.append(dbn_param_node[0]) # e.g., "Height(param)"
                node_plot_types.append("param")

        # Sensors (in slice 0 and slice 1)
        for orig_v_id in self._sensor_vids_in_sub:
            if orig_v_id not in vid_to_tag_map or orig_v_id >= len(self._layout2d):
                continue
            
            base_tag = vid_to_tag_map[orig_v_id]
            x, y = self._layout2d[orig_v_id]

            # Sensor node t-1 (slice 0)
            sensor_node_t0 = (base_tag, 0)
            current_plot_idx_t0 = len(xs)
            pos_index[sensor_node_t0] = current_plot_idx_t0
            xs.append(x)
            ys.append(y)
            zs.append(0.0)
            node_labels.append(f"{base_tag}(t-1)")
            node_plot_types.append("sensor")

            # Sensor node t (slice 1)
            sensor_node_t1 = (base_tag, 1)
            current_plot_idx_t1 = len(xs)
            pos_index[sensor_node_t1] = current_plot_idx_t1
            xs.append(x)
            ys.append(y)
            zs.append(z_step) # At z = z_step
            node_labels.append(f"{base_tag}(t)")
            node_plot_types.append("sensor")

        fig = go.Figure()

        # 2. Add Node Traces
        param_indices = [i for i, type_name in enumerate(node_plot_types) if type_name == "param"]
        sensor_indices = [i for i, type_name in enumerate(node_plot_types) if type_name == "sensor"]

        if sensor_indices:
            fig.add_trace(
                go.Scatter3d(
                    x=[xs[i] for i in sensor_indices], y=[ys[i] for i in sensor_indices], z=[zs[i] for i in sensor_indices],
                    mode="markers+text", text=[node_labels[i] for i in sensor_indices],
                    marker=dict(size=marker_size, symbol="circle", color="blue"), # Changed color for sensors
                    name="Sensor Nodes", textposition="top center"
                ))
        if param_indices:
            fig.add_trace(
                go.Scatter3d(
                    x=[xs[i] for i in param_indices], y=[ys[i] for i in param_indices], z=[zs[i] for i in param_indices],
                    mode="markers+text", text=[node_labels[i] for i in param_indices],
                    marker=dict(size=marker_size, symbol="diamond", color="orange"), # Changed color for params
                    name="Parameter Nodes", textposition="top center"
                ))
        
        # 3. Add Edge Traces
        legend_flags = {"sensor_inter": False, "param_sensor": False, "sensor_self": False}

        for src_dbn_node, dst_dbn_node in self._all_dbn_edges_collected:
            if src_dbn_node not in pos_index or dst_dbn_node not in pos_index:
                # This can happen if a node involved in an edge wasn't in _sensor_vids_in_sub or _param_vids_in_sub
                # or if its tag was missing.
                print(f"Warning: Skipping edge due to missing node in plot: {src_dbn_node} -> {dst_dbn_node}")
                continue

            src_idx = pos_index[src_dbn_node]
            dst_idx = pos_index[dst_dbn_node]

            edge_x = [xs[src_idx], xs[dst_idx]]
            edge_y = [ys[src_idx], ys[dst_idx]]
            edge_z = [zs[src_idx], zs[dst_idx]]

            line_props = {}
            show_legend = False
            trace_name = ""
            legend_group = ""

            is_param_source = src_dbn_node[0].endswith("(param)")
            
            if is_param_source:
                line_props = dict(dash="dash", width=2, color="purple") # Param edges
                trace_name = "Parameter→Sensor"
                legend_group = "param_sensor_edges"
                if not legend_flags["param_sensor"]:
                    show_legend = True
                    legend_flags["param_sensor"] = True
            elif src_dbn_node[1] == 0 and dst_dbn_node[1] == 1: # Sensor t-1 to Sensor t
                if src_dbn_node[0] == dst_dbn_node[0]: # Self-transition
                    line_props = dict(dash="dot", width=2, color="green")
                    trace_name = "Self-Transition (Sensor)"
                    legend_group = "sensor_self_edges"
                    if not legend_flags["sensor_self"]:
                        show_legend = True
                        legend_flags["sensor_self"] = True
                else: # Inter-slice sensor to sensor
                    line_props = dict(width=2, color="red")
                    trace_name = "Sensor→Sensor (Inter-slice)"
                    legend_group = "sensor_inter_edges"
                    if not legend_flags["sensor_inter"]:
                        show_legend = True
                        legend_flags["sensor_inter"] = True
            else: # Other edge types (e.g. within-slice if any, though DBN usually doesn't have them from non-params)
                # This should ideally not be common for typical DBN structures from this converter
                line_props = dict(width=1, color="grey", dash="longdash")
                trace_name = f"Other: {src_dbn_node[0]} to {dst_dbn_node[0]}"
                legend_group = "other_edges"


            if trace_name:
                fig.add_trace(
                    go.Scatter3d(
                        x=edge_x, y=edge_y, z=edge_z, mode="lines",
                        name=trace_name, legendgroup=legend_group,
                        showlegend=show_legend, line=line_props
                    ))

        fig.update_layout(
            scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Time Slice (t-1 at z=0, t at z=" + str(z_step) + ")"),
            margin=dict(l=0, r=0, b=0, t=0),
            legend_title_text="Edge Types"
        )
        fig.write_html(filename)
        print(f"Interactive 3D DBN plot saved: {filename}")


    # --------------------- DBN-Checks --------------------
    def check_dbn_with_igraph(self, dbn_model: DBN):
        if not list(dbn_model.nodes()):
            print("OK: DBN is empty (no nodes).")
            return
        if not list(dbn_model.edges()):
            print("OK: DBN has nodes but no edges (azyklisch by definition).")
            # Check for directedness is not meaningful without edges, igraph might complain.
            return
            
        # 1) Index nodes
        nodes = list(dbn_model.nodes())
        idx = {node_tuple: i for i, node_tuple in enumerate(nodes)}
        
        # 2) Create igraph Graph
        g = ig.Graph(directed=True)
        g.add_vertices(len(nodes))
        # Optional: Add names to igraph nodes for easier debugging if check fails
        # g.vs["name"] = [str(n) for n in nodes]

        try:
            edges_for_igraph = [(idx[u], idx[v]) for u, v in dbn_model.edges()]
            g.add_edges(edges_for_igraph)
        except KeyError as e:
            print(f"Error creating igraph for check: Node {e} from DBN edges not found in DBN nodes list.")
            print("DBN Nodes:", nodes)
            print("DBN Edges:", list(dbn_model.edges()))
            return


        # 3) Perform checks
        assert g.is_directed(), "Graph consistency check: DBN is not directed!"
        assert g.is_dag(), "Graph consistency check: DBN contains at least one cycle!"
        print("OK: DBN is directed and acyclic.")

if __name__ == "__main__":
    # 1) AML laden
    aml_file = GRAPH_CONFIG.AML_FILE_PATH
    dcdg = arroyo.DCDG_Class()
    dcdg.generate_graphfromAML(aml_file)

    # 2) Converter erzeugen
    converter = IGraphConverter(dcdg)

    # 3) Sub-Graph ohne 'hierarch'-Knoten holen
    sub, vid_map_sub, eid_map_sub = converter.get_filtered_subgraph_with_mapping(
        "hierarch", True
    )

    # 4) Knoten nach Typ aufteilen
    param_carrier_list = ["Height", "Area", "Diameter", "Roughness", "HDiff", "PDropNom", "Rotational_Speed", "MFNominal"]
    params, sensors = converter.split_nodes_by_carrier(sub, param_carrier_list)

    # 5) DBN-Converter erzeugen und DBN bauen
    dbn_converter = DBNConverter(sub, vid_map_sub, eid_map_sub, converter)
    model, inter_map, param_map = dbn_converter.build(sensors, params)

    dbn_converter.check_dbn_with_igraph(model)

    # 6) Optional: interaktiven Plot speichern
    dbn_converter.plot_interactive(filename="dbn_plot.html", z_step=10.0, marker_size=8)
