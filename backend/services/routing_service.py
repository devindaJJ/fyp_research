import osmnx as ox
import networkx as nx

# Load Colombo road network
print("Loading road network...")

G = ox.graph_from_place(
    "Colombo District, Sri Lanka",
    network_type="drive"
)

print("Road network loaded!")

# Add travel speed estimates
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)


def calculate_route(origin_lat, origin_lng, dest_lat, dest_lng, vehicle="car"):

    try:

        # Find nearest nodes
        orig_node = ox.distance.nearest_nodes(G, origin_lng, origin_lat)
        dest_node = ox.distance.nearest_nodes(G, dest_lng, dest_lat)

        # Vehicle speed modifier
        speed_factor = {
            "car": 1.0,
            "bike": 1.2,
            "threewheel": 0.9,
            "bus": 0.7
        }

        factor = speed_factor.get(vehicle, 1.0)

        # Shortest path using travel time
        route = nx.shortest_path(
            G,
            orig_node,
            dest_node,
            weight="travel_time"
        )

        # Calculate distance + time
        route_edges = ox.utils_graph.get_route_edge_attributes(G, route)

        distance = sum(edge["length"] for edge in route_edges)
        travel_time = sum(edge["travel_time"] for edge in route_edges)

        travel_time = travel_time / factor

        return {
            "success": True,
            "distance_km": distance / 1000,
            "travel_time_min": travel_time / 60,
            "route_nodes": route
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }