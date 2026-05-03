import math
import os
import time
import pandas as pd
import osmnx as ox
import networkx as nx

GRAPH_FILE = os.path.join("data", "osm", "sri_lanka_drive.graphml")
EDGES_FILE = os.path.join("data", "osm", "sri_lanka_edges_enriched.csv")
INCIDENTS_FILE = os.path.join("data", "incidents", "manual_incidents.csv")
INCIDENT_EXPIRY_MINUTES = 60


# ---------------------------------
# LOAD BASE GRAPH
# ---------------------------------
def load_graph(file_path=GRAPH_FILE):
    print(f"Loading graph from: {file_path}")
    G = ox.load_graphml(file_path)
    print(f"Graph loaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    return G


# ---------------------------------
# LOAD ENRICHED EDGE DATASET
# ---------------------------------
def load_edges_dataset(file_path=EDGES_FILE):
    print(f"Loading enriched edge dataset from: {file_path}")
    df = pd.read_csv(file_path)
    print(f"Edge dataset loaded with {len(df)} rows.")
    return df


# ---------------------------------
# LOAD INCIDENTS
# ---------------------------------
def load_incidents(file_path=INCIDENTS_FILE):
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=[
            "incident_id", "type", "severity", "lat", "lng", "status", "description", "timestamp"
        ])

    df = pd.read_csv(file_path)

    if df.empty:
        return df

    now = time.time()
    expiry_seconds = INCIDENT_EXPIRY_MINUTES * 60

    if "status" in df.columns:
        df["status"] = df["status"].astype(str).str.lower()
        df = df[df["status"] == "active"]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        now = pd.Timestamp.now()
        expiry_time = now - pd.Timedelta(minutes=INCIDENT_EXPIRY_MINUTES)

        df = df[df["timestamp"] >= expiry_time]

    return df


# ---------------------------------
# BUILD ROUTING GRAPH FROM DATASET
# ---------------------------------
def build_routing_graph(base_graph, edges_df, vehicle_type, current_hour):
    vehicle_type = vehicle_type.lower()

    if vehicle_type == "car":
        allow_col = "allow_car_van"
    elif vehicle_type == "bike":
        allow_col = "allow_bike"
    elif vehicle_type == "three_wheeler":
        allow_col = "allow_three_wheeler"
    elif vehicle_type == "bus":
        allow_col = "allow_bus"
    elif vehicle_type == "lorry":
        allow_col = "allow_lorry"
    else:
        allow_col = "allow_car_van"

    H = nx.MultiDiGraph()
    H.graph.update(base_graph.graph)

    # copy nodes from base graph
    for node, data in base_graph.nodes(data=True):
        H.add_node(node, **data)

    for _, row in edges_df.iterrows():
        if not bool(row.get(allow_col, True)):
            continue

        u = int(row["u"])
        v = int(row["v"])
        key = int(row["key"])

        if u not in base_graph.nodes or v not in base_graph.nodes:
            continue

        # find matching original edge for geometry
        if not base_graph.has_edge(u, v, key):
            continue

        base_edge = base_graph[u][v][key]

        highway = str(row.get("highway", "")).lower()
        free_flow_time = float(row.get("free_flow_time_sec", 1))
        length_m = float(row.get("length_m", 0))
        road_name = str(row.get("road_name", ""))

        # dynamic hourly multiplier
        hourly_multiplier = get_hourly_multiplier(highway, current_hour)
        weight = free_flow_time * hourly_multiplier

        # additional vehicle penalties
        if vehicle_type in ["bus", "lorry"]:
            if highway in ["residential", "living_street", "service"]:
                weight *= 1.35

        if vehicle_type in ["bike", "three_wheeler"]:
            if highway in ["primary", "trunk"]:
                weight *= 1.08

        H.add_edge(
            u,
            v,
            key=key,
            weight=weight,
            free_flow_time=free_flow_time,
            predicted_time=weight,
            length=length_m,
            highway=highway,
            name=road_name,
            geometry=base_edge.get("geometry", None)
        )

    return H


# ---------------------------------
# DYNAMIC HOURLY MULTIPLIER
# ---------------------------------
def get_hourly_multiplier(highway, hour):
    highway = str(highway).lower()

    # midnight to early morning
    if 0 <= hour < 5:
        if highway in ["motorway", "trunk", "primary"]:
            return 1.00
        return 1.03

    # early morning
    if 5 <= hour < 7:
        if highway in ["motorway", "trunk"]:
            return 1.03
        elif highway in ["primary", "secondary"]:
            return 1.08
        return 1.12

    # morning peak
    if 7 <= hour < 10:
        if highway == "motorway":
            return 1.10
        elif highway in ["trunk", "primary"]:
            return 1.25
        elif highway in ["secondary", "tertiary"]:
            return 1.40
        return 1.50

    # daytime
    if 10 <= hour < 16:
        if highway == "motorway":
            return 1.04
        elif highway in ["trunk", "primary"]:
            return 1.10
        elif highway in ["secondary", "tertiary"]:
            return 1.18
        return 1.22

    # evening peak
    if 16 <= hour < 20:
        if highway == "motorway":
            return 1.12
        elif highway in ["trunk", "primary"]:
            return 1.30
        elif highway in ["secondary", "tertiary"]:
            return 1.45
        return 1.55

    # night
    return 1.06


# ---------------------------------
# INCIDENT CONFIG
# ---------------------------------
def get_incident_config(incident_type, severity):
    incident_type = str(incident_type).lower()
    severity = str(severity).lower()

    radius_m = 120
    multiplier = 1.5
    remove_edge = False

    if incident_type == "road_closure":
        radius_m = 180 if severity == "high" else 120
        remove_edge = True

    elif incident_type == "flooding":
        if severity == "high":
            radius_m = 220
            remove_edge = True
        else:
            radius_m = 160
            multiplier = 2.2

    elif incident_type == "accident":
        if severity == "high":
            radius_m = 180
            multiplier = 3.0
        elif severity == "medium":
            radius_m = 140
            multiplier = 2.0
        else:
            radius_m = 100
            multiplier = 1.4

    elif incident_type == "construction":
        if severity == "high":
            radius_m = 180
            multiplier = 2.5
        elif severity == "medium":
            radius_m = 140
            multiplier = 1.8
        else:
            radius_m = 100
            multiplier = 1.3

    elif incident_type == "pothole":
        radius_m = 60
        multiplier = 1.15 if severity == "low" else 1.30

    elif incident_type == "congestion_hotspot":
        if severity == "high":
            radius_m = 250
            multiplier = 2.2
        elif severity == "medium":
            radius_m = 180
            multiplier = 1.6
        else:
            radius_m = 120
            multiplier = 1.25

    return radius_m, multiplier, remove_edge


# ---------------------------------
# HAVERSINE DISTANCE
# ---------------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    R = 6371000
    return R * c


# ---------------------------------
# EDGE GEOMETRY POINTS FOR INCIDENT CHECK
# ---------------------------------
def get_edge_points_for_incident_check(G, u, v, key, data):
    points = []

    if data.get("geometry") is not None:
        line = data["geometry"]
        coords = list(line.coords)

        if len(coords) > 8:
            step = max(1, len(coords) // 8)
            coords = coords[::step]
            if coords[-1] != list(line.coords)[-1]:
                coords.append(list(line.coords)[-1])

        for lng, lat in coords:
            points.append((lat, lng))
    else:
        points.append((float(G.nodes[u]["y"]), float(G.nodes[u]["x"])))
        points.append((float(G.nodes[v]["y"]), float(G.nodes[v]["x"])))

    return points


# ---------------------------------
# APPLY INCIDENT PENALTIES
# ---------------------------------
def apply_incident_penalties(G, incidents_df):
    if incidents_df is None or incidents_df.empty:
        return 0

    edges_to_remove = []
    affected_count = 0

    for _, inc in incidents_df.iterrows():
        inc_lat = float(inc["lat"])
        inc_lng = float(inc["lng"])
        inc_type = str(inc["type"]).lower()
        severity = str(inc["severity"]).lower()

        radius_m, multiplier, remove_edge = get_incident_config(inc_type, severity)
        approx_deg = radius_m / 111320.0

        for u, v, key, data in G.edges(keys=True, data=True):
            u_lat = float(G.nodes[u]["y"])
            u_lng = float(G.nodes[u]["x"])
            v_lat = float(G.nodes[v]["y"])
            v_lng = float(G.nodes[v]["x"])

            min_lat = min(u_lat, v_lat) - approx_deg
            max_lat = max(u_lat, v_lat) + approx_deg
            min_lng = min(u_lng, v_lng) - approx_deg
            max_lng = max(u_lng, v_lng) + approx_deg

            if not (min_lat <= inc_lat <= max_lat and min_lng <= inc_lng <= max_lng):
                continue

            edge_points = get_edge_points_for_incident_check(G, u, v, key, data)

            affected = False
            for p_lat, p_lng in edge_points:
                if haversine_distance(inc_lat, inc_lng, p_lat, p_lng) <= radius_m:
                    affected = True
                    break

            if not affected:
                continue

            affected_count += 1

            if remove_edge:
                edges_to_remove.append((u, v, key))
            else:
                data["weight"] = float(data.get("weight", 1)) * multiplier

    for u, v, key in edges_to_remove:
        if G.has_edge(u, v, key):
            G.remove_edge(u, v, key)

    return affected_count


# ---------------------------------
# HAVERSINE HEURISTIC
# ---------------------------------
def haversine_heuristic(node1, node2, G):
    lat1 = float(G.nodes[node1]["y"])
    lon1 = float(G.nodes[node1]["x"])
    lat2 = float(G.nodes[node2]["y"])
    lon2 = float(G.nodes[node2]["x"])

    distance_m = haversine_distance(lat1, lon1, lat2, lon2)
    return distance_m / 11.11


# ---------------------------------
# FIND NEAREST NODE + DISTANCE
# ---------------------------------
def find_nearest_node_with_distance(G, lat, lng):
    node = ox.distance.nearest_nodes(G, X=lng, Y=lat)

    node_lat = float(G.nodes[node]["y"])
    node_lng = float(G.nodes[node]["x"])

    distance_m = haversine_distance(lat, lng, node_lat, node_lng)
    return node, distance_m


# ---------------------------------
# CORRIDOR SUBGRAPH FROM BASE GRAPH
# ---------------------------------
def get_corridor_subgraph(G, origin_lat, origin_lng, dest_lat, dest_lng, buffer_deg=0.12):
    min_lat = min(origin_lat, dest_lat) - buffer_deg
    max_lat = max(origin_lat, dest_lat) + buffer_deg
    min_lng = min(origin_lng, dest_lng) - buffer_deg
    max_lng = max(origin_lng, dest_lng) + buffer_deg

    nodes_to_keep = [
        n for n, data in G.nodes(data=True)
        if min_lat <= float(data["y"]) <= max_lat
        and min_lng <= float(data["x"]) <= max_lng
    ]

    return G.subgraph(nodes_to_keep).copy()


# ---------------------------------
# FILTER EDGE DATASET TO CORRIDOR
# ---------------------------------
def filter_edges_for_subgraph(edges_df, subG):
    node_ids = set(subG.nodes())
    return edges_df[
        edges_df["u"].isin(node_ids) &
        edges_df["v"].isin(node_ids)
    ].copy()


# ---------------------------------
# PRIMARY A* ROUTE
# ---------------------------------
def calculate_shortest_path(G, start_node, end_node):
    try:
        path = nx.astar_path(
            G,
            source=start_node,
            target=end_node,
            heuristic=lambda n1, n2: haversine_heuristic(n1, n2, G),
            weight="weight"
        )
    except nx.NetworkXNoPath:
        return None, 0, 0, 0

    total_weight = 0.0
    total_free_flow = 0.0
    total_distance = 0.0

    for u, v in zip(path[:-1], path[1:]):
        edge_dict = G.get_edge_data(u, v)
        edge = edge_dict[min(edge_dict.keys())]

        total_weight += float(edge.get("weight", 0))
        total_free_flow += float(edge.get("free_flow_time", 0))
        total_distance += float(edge.get("length", 0))

    return path, total_weight, total_distance, total_free_flow


# ---------------------------------
# ROUTE OVERLAP
# ---------------------------------
def route_overlap_ratio(path_a, path_b):
    set_a = set(zip(path_a[:-1], path_a[1:]))
    set_b = set(zip(path_b[:-1], path_b[1:]))

    if not set_a:
        return 0

    return len(set_a.intersection(set_b)) / len(set_a)


# ---------------------------------
# ALTERNATIVE ROUTES
# ---------------------------------
def calculate_multiple_routes(G, start_node, end_node, k=2):
    routes = []

    try:
        simple_graph = nx.DiGraph()

        for u, v, key, data in G.edges(keys=True, data=True):
            weight = float(data.get("weight", 1))
            length = float(data.get("length", 0))
            free_flow = float(data.get("free_flow_time", 1))

            if simple_graph.has_edge(u, v):
                if weight < simple_graph[u][v]["weight"]:
                    simple_graph[u][v]["weight"] = weight
                    simple_graph[u][v]["length"] = length
                    simple_graph[u][v]["free_flow_time"] = free_flow
            else:
                simple_graph.add_edge(
                    u, v,
                    weight=weight,
                    length=length,
                    free_flow_time=free_flow
                )

        generator = nx.shortest_simple_paths(
            simple_graph,
            start_node,
            end_node,
            weight="weight"
        )

        selected_paths = []

        for path in generator:
            too_similar = False

            for existing in selected_paths:
                if route_overlap_ratio(existing, path) > 0.85:
                    too_similar = True
                    break

            if too_similar:
                continue

            selected_paths.append(path)

            total_weight = 0.0
            total_free_flow = 0.0
            total_distance = 0.0

            for u, v in zip(path[:-1], path[1:]):
                edge = simple_graph[u][v]
                total_weight += float(edge.get("weight", 0))
                total_free_flow += float(edge.get("free_flow_time", 0))
                total_distance += float(edge.get("length", 0))

            routes.append({
                "path": path,
                "travel_time_sec": total_weight,
                "free_flow_time_sec": total_free_flow,
                "distance_m": total_distance
            })

            if len(routes) >= k:
                break

        return routes

    except nx.NetworkXNoPath:
        return []


# ---------------------------------
# SIMPLIFY ROUTE POINTS
# ---------------------------------
def simplify_coordinates(coords, max_points=120):
    if len(coords) <= max_points:
        return coords

    step = max(1, len(coords) // max_points)
    reduced = coords[::step]

    if reduced[-1] != coords[-1]:
        reduced.append(coords[-1])

    return reduced


# ---------------------------------
# GEOMETRY-AWARE ROUTE COORDS
# ---------------------------------
def get_route_coordinates(G, path, max_points=120):
    coords = []

    for u, v in zip(path[:-1], path[1:]):
        edge_dict = G.get_edge_data(u, v)

        if not edge_dict:
            continue

        edge = edge_dict[min(edge_dict.keys())]

        if "geometry" in edge and edge["geometry"] is not None:
            line = edge["geometry"]
            segment = [[lat, lng] for lng, lat in line.coords]
        else:
            segment = [
                [float(G.nodes[u]["y"]), float(G.nodes[u]["x"])],
                [float(G.nodes[v]["y"]), float(G.nodes[v]["x"])]
            ]

        if coords:
            if coords[-1] == segment[0]:
                coords.extend(segment[1:])
            else:
                coords.extend(segment)
        else:
            coords.extend(segment)

    return simplify_coordinates(coords, max_points=max_points)


# ---------------------------------
# ROUTE SUMMARY
# ---------------------------------
def get_route_summary(G, path, max_edges_to_scan=40):
    road_names = []

    for u, v in list(zip(path[:-1], path[1:]))[:max_edges_to_scan]:
        edge_dict = G.get_edge_data(u, v)

        if not edge_dict:
            continue

        edge = edge_dict[min(edge_dict.keys())]
        name = edge.get("name", "")

        if isinstance(name, list):
            if len(name) > 0:
                name = name[0]

        if name and str(name) not in road_names:
            road_names.append(str(name))

    if len(road_names) >= 2:
        return f"{road_names[0]} → {road_names[1]}"
    elif len(road_names) == 1:
        return road_names[0]
    else:
        return "Unnamed road route"