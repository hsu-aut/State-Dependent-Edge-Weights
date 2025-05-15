import igraph as ig
from pgmpy.models import DynamicBayesianNetwork as DBN
from graph_copy_for_dbn import IGraphConverter
import Arroyo_DCDG_PLUT as arroyo


class DBNConverter:
    def __init__(
        self,
        sub_graph: ig.Graph,
        vid_map_sub: dict[int, int],
        eid_map_sub: dict[int, int],
        converter: IGraphConverter,
    ):
        self.sub = sub_graph
        self.vid_map = vid_map_sub
        self.eid_map = eid_map_sub
        self.converter = converter

        self.T = sub_graph.vcount()
        self.dyn = DBN()

        # für Sensor-Knoten je zwei Slices
        self.tminus1_nodes: list[tuple[str, int]] = []
        self.t_nodes: list[tuple[str, int]] = []

        # Interslice (Sensor→Sensor)
        # Nur echte Subgraph-Kanten (ohne Selbstübergänge)
        self.inter_eid_map: dict[int, tuple[int, int]] = {}
        self.inter_edges: list[tuple[int, int]] = []
        # Selbstübergänge separat
        self.self_edges: list[int] = []

        # Parameter-Knoten und -Kanten
        # param_node_names: vid → (node_name, slice_index)
        self.param_node_names: dict[int, tuple[str, int]] = {}
        # param_eid_map: dyn_edge_id → orig_sub_eid (nur für Kanten in t-Slice)
        self.param_eid_map: dict[int, int] = {}
        # param_edges: Liste der (u, v, slice_index) zum Plotten
        self.param_edges: list[tuple[int, int, int]] = []

        # Converter-edge-id zurück auf subgraph-edge-id
        self.conv2sub = {conv: sub for sub, conv in eid_map_sub.items()}

        # Layout für Plot
        self._raw_layout = self.sub.layout("fr")
        self._compute_scaled_layout((5000, 5000))

    def _create_nodes(self, sensor_ids: list[int], param_ids: list[int]):
        """
        Erzeugt im DBN:
         - für jeden Parameter-Knoten v in param_ids: genau einen Node (v,param) in Slice 0
         - für alle anderen Knoten v: zwei Nodes (v, t-1) in Slice 0 und (v, t) in Slice 1
        """
        for v in range(self.T):
            if v in param_ids:
                name = f"{v}(param)"
                self.dyn.add_node((name, 0))
                self.param_node_names[v] = (name, 0)
            elif v in sensor_ids:
                name_t0 = f"{v}(t-1)"
                name_t1 = f"{v}(t)"
                self.dyn.add_node((name_t0, 0))
                self.dyn.add_node((name_t1, 1))
                self.tminus1_nodes.append((name_t0, 0))
                self.t_nodes.append((name_t1, 1))

    def _add_interslice_edges(self, sensor_ids: list[int]):
        """
        Fügt für jeden Sensor u in sensor_ids alle ausgehenden Kanten u→v
        als Interslice-Kanten u(t-1)→v(t) hinzu.
        Außerdem werden Selbstübergänge separat erfasst.
        """
        self.inter_eid_map.clear()
        self.inter_edges.clear()
        eid_counter = 0

        # Interslice-Kanten (Sensor→Sensor)
        for sub_eid in range(self.sub.ecount()):
            u, v = self.sub.es[sub_eid].tuple
            if u not in sensor_ids:
                continue

            src = (f"{u}(t-1)", 0)
            dst = (f"{v}(t)", 1)
            self.dyn.add_edge(src, dst)

            conv_eid = self.eid_map[sub_eid]
            orig_eid = self.converter.orig_eid(conv_eid)
            self.inter_eid_map[eid_counter] = (conv_eid, orig_eid)
            self.inter_edges.append((u, v))
            eid_counter += 1

        # Selbstübergänge für jeden Sensor-Knoten
        for u in sensor_ids:
            src = (f"{u}(t-1)", 0)
            dst = (f"{u}(t)", 1)
            self.dyn.add_edge(src, dst)
            self.self_edges.append(u)

    def _add_parameter_edges(self, param_ids: list[int]):
        """
        Fügt für jeden Parameter-Knoten u alle ausgehenden Parameter→Sensor-Kanten u→v
        in beide Slices ein:
         - (u(param) → v(t-1))
         - (u(param) → v(t)) mit original sub_eid als dyn_edge_id
        """
        self.param_eid_map.clear()
        self.param_edges.clear()

        for sub_eid in range(self.sub.ecount()):
            u, v = self.sub.es[sub_eid].tuple
            # nur Parameter→Sensor, keine Parameter→Parameter
            if u not in param_ids or v in param_ids:
                continue

            param_name, param_slice = self.param_node_names[u]

            # a) Parameter → Sensor in Slice t-1
            dst0 = (f"{v}(t-1)", 0)
            self.dyn.add_edge((param_name, param_slice), dst0)
            self.param_edges.append((u, v, 0))

            # b) Parameter → Sensor in Slice t, mit original sub_eid als ID
            dst1 = (f"{v}(t)", 1)
            self.dyn.add_edge((param_name, param_slice), dst1)
            self.param_eid_map[sub_eid] = sub_eid
            self.param_edges.append((u, v, 1))

    def build(self, sensor_ids: list[int], param_ids: list[int]):
        """
        Baut das DBN auf:
         1. Knoten anlegen
         2. Sensor→Sensor Interslice-Kanten
         3. Parameter→Sensor Kanten in beiden Slices
        """
        self._create_nodes(sensor_ids, param_ids)
        self._add_interslice_edges(sensor_ids)
        self._add_parameter_edges(param_ids)
        return self.dyn, self.inter_eid_map, self.param_eid_map

    # --------------------- Plotting --------------------
    def _compute_scaled_layout(self, bbox):
        layout = self._raw_layout.copy()
        layout.fit_into(bbox, keep_aspect_ratio=False)
        self._layout2d = layout.coords

    def plot_interactive(
        self,
        filename: str = "dbn_plot.html",
        z_step: float = 1.0,
        marker_size: int = 6,
        bbox: tuple[float, float] = (5000, 5000),
    ):
        import plotly.graph_objects as go

        if self._layout2d is None:
            self._compute_scaled_layout(bbox)

        xs, ys, zs = [], [], []
        labels = []
        types = []  # 'param' oder 'sensor'
        pos_index = {}

        tags = [
            self.sub.vs[i]["Tag"] if "Tag" in self.sub.vs.attribute_names() else str(i)
            for i in range(self.T)
        ]

        for i in range(self.T):
            x, y = self._layout2d[i]
            if i in self.param_node_names:
                # Parameter-Knoten
                slice_idx = self.param_node_names[i][1]
                pos = len(xs)
                pos_index[(i, slice_idx)] = pos
                xs.append(x)
                ys.append(y)
                zs.append(0.0)
                labels.append(f"{tags[i]}(param)")
                types.append("param")
            else:
                # Sensor-Knoten t-1
                pos0 = len(xs)
                pos_index[(i, 0)] = pos0
                xs.append(x)
                ys.append(y)
                zs.append(0.0)
                labels.append(f"{tags[i]}(t-1)")
                types.append("sensor")
                # Sensor-Knoten t
                pos1 = len(xs)
                pos_index[(i, 1)] = pos1
                xs.append(x)
                ys.append(y)
                zs.append(z_step)
                labels.append(f"{tags[i]}(t)")
                types.append("sensor")

        # trennen Daten nach Typ
        param_idx = [i for i, t in enumerate(types) if t == "param"]
        sensor_idx = [i for i, t in enumerate(types) if t == "sensor"]

        fig = go.Figure()

        # Sensor-Knoten (z.B. Kreise)
        fig.add_trace(
            go.Scatter3d(
                x=[xs[i] for i in sensor_idx],
                y=[ys[i] for i in sensor_idx],
                z=[zs[i] for i in sensor_idx],
                mode="markers+text",
                text=[labels[i] for i in sensor_idx],
                marker=dict(size=marker_size, symbol="circle"),
            )
        )

        # Parameter-Knoten (z.B. Diamanten)
        fig.add_trace(
            go.Scatter3d(
                x=[xs[i] for i in param_idx],
                y=[ys[i] for i in param_idx],
                z=[zs[i] for i in param_idx],
                mode="markers+text",
                text=[labels[i] for i in param_idx],
                marker=dict(size=marker_size, symbol="diamond"),
            )
        )

        # Sensor→Sensor-Kanten (solide rote Linien)
        added_sensor_legend = False
        for u, v in self.inter_edges:
            fig.add_trace(
                go.Scatter3d(
                    x=[xs[pos_index[(u,0)]], xs[pos_index[(v,1)]]],
                    y=[ys[pos_index[(u,0)]], ys[pos_index[(v,1)]]],
                    z=[zs[pos_index[(u,0)]], zs[pos_index[(v,1)]]],
                    mode="lines",
                    name="Sensor→Sensor",              
                    legendgroup="sensor",              
                    showlegend=not added_sensor_legend,
                    line=dict(width=2, color="red"),
                )
            )
            added_sensor_legend = True

        # Parameter→Sensor-Kanten (gestrichelte blaue Linien)
        added_param_legend = False
        for u, v, sl in self.param_edges:
            fig.add_trace(
                go.Scatter3d(
                    x=[xs[pos_index[(u,self.param_node_names[u][1])]],
                    xs[pos_index[(v,sl)]]],
                    y=[ys[pos_index[(u,self.param_node_names[u][1])]],
                    ys[pos_index[(v,sl)]]],
                    z=[zs[pos_index[(u,self.param_node_names[u][1])]],
                    zs[pos_index[(v,sl)]]],
                    mode="lines",
                    name="Parameter→Sensor",
                    legendgroup="param",
                    showlegend=not added_param_legend,
                    line=dict(dash="dash", width=2, color="blue"),
                )
            )
            added_param_legend = True

        # Self-Loops (gestrichelte grüne Linien)
        added_self_legend = False
        for u in self.self_edges:
            fig.add_trace(
                go.Scatter3d(
                    x=[xs[pos_index[(u,0)]], xs[pos_index[(u,1)]]],
                    y=[ys[pos_index[(u,0)]], ys[pos_index[(u,1)]]],
                    z=[zs[pos_index[(u,0)]], zs[pos_index[(u,1)]]],
                    mode="lines",
                    name="Self-Loop",
                    legendgroup="self",
                    showlegend=not added_self_legend,
                    line=dict(dash="dot", width=2, color="green"),
                )
            )
            added_self_legend = True


        fig.update_layout(
            scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Time"),
            margin=dict(l=0, r=0, b=0, t=0),
        )
        fig.write_html(filename)
        print(f"Interaktiver 3D-Plot gespeichert: {filename}")


if __name__ == "__main__":
    # 1) AML laden
    aml_file = r"ModVA_Mixer_incl_SensorNamingConvention_reduced.aml"
    dcdg = arroyo.DCDG_Class()
    dcdg.generate_graphfromAML(aml_file)

    # 2) Converter erzeugen
    converter = IGraphConverter(dcdg)

    # 3) Sub-Graph ohne 'hierarch'-Knoten holen
    sub, vid_map_sub, eid_map_sub = converter.get_filtered_subgraph_with_mapping(
        "hierarch", True
    )

    # 4) Knoten nach Typ aufteilen
    param_carrier_list = ["Height", "Area", "Diameter", "Roughness", "HDiff", "PDropNom", "Rotational_Speed"]
    params, sensors = converter.split_nodes_by_carrier(sub, param_carrier_list)

    # 5) DBN-Converter erzeugen und DBN bauen
    dbn_converter = DBNConverter(sub, vid_map_sub, eid_map_sub, converter)
    model, inter_map, param_map = dbn_converter.build(sensors, params)

    # 6) Optional: interaktiven Plot speichern
    dbn_converter.plot_interactive(filename="dbn_plot.html", z_step=10.0, marker_size=8)
