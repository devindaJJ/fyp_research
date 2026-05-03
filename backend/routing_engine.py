import pandas as pd
import networkx as nx

# Load predicted traffic data
def load_graph(vehicle_type="car"):
    
    file_path = "data/processed/colombo_network_with_prediction.csv"
    
    df = pd.read_csv(file_path)

    print("Loading predicted traffic data...")
    print("Total edges:", len(df))

    G = nx.DiGraph()

    # Vehicle permission column name
    vehicle_column = f"allow_{vehicle_type}"

    if vehicle_column not in df.columns:
        raise Exception(f"Vehicle type '{vehicle_type}' not supported")

    for _, row in df.iterrows():

        # Skip roads not allowed for vehicle
        if row[vehicle_column] == False:
            continue

        # Skip invalid prediction
        if pd.isna(row["predicted_time"]):
            continue

        G.add_edge(
            int(row["u"]),
            int(row["v"]),
            weight=float(row["predicted_time"]),
            highway=row["highway"]
        )

    print("Graph created successfully.")
    print("Nodes:", G.number_of_nodes())
    print("Edges:", G.number_of_edges())

    return G


# Find best route
def find_route(G, source, target):

    try:
        path = nx.shortest_path(
            G,
            source=source,
            target=target,
            weight="weight"
        )

        total_time = 0

        for i in range(len(path)-1):
            total_time += G[path[i]][path[i+1]]["weight"]

        return path, total_time

    except nx.NetworkXNoPath:

        return None, None


# MAIN
if __name__ == "__main__":

    vehicle = input("Enter vehicle type (car/bike/bus/lorry/three_wheeler): ").strip()

    source = int(input("Enter source node ID: "))
    target = int(input("Enter destination node ID: "))

    G = load_graph(vehicle)

    path, time = find_route(G, source, target)

    if path:

        print("\nRoute found")
        print("Number of nodes:", len(path))

        print(f"Estimated travel time: {round(time,2)} minutes")

    else:
        print("No route found")