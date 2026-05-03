import pandas as pd
import os

# ============================
# STEP 1 — Load dataset
# ============================

# Get current file directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Go to data/processed folder
file_path = os.path.join(BASE_DIR, "..", "data", "processed", "colombo_network_edges_with_time.csv")

print("Loading file from:", file_path)

edges = pd.read_csv(file_path)

print("\nFile loaded successfully.")
print("\nColumns in dataset:")
print(edges.columns)

print("\nSample data:")
print(edges.head())

print("\nTotal road segments:", len(edges))


# ============================
# STEP 2 — Sri Lanka legal speed limits
# ============================

def get_base_speed(highway):

    # Convert to string (important for safety)
    highway = str(highway)

    # Expressways (E01, E02, E03)
    if highway == "motorway":
        return 100

    # Major roads
    elif highway in ["trunk", "primary"]:
        return 50

    # Medium roads
    elif highway in ["secondary", "tertiary"]:
        return 50

    # Urban roads
    elif highway in ["residential", "service", "unclassified"]:
        return 40

    # Default
    else:
        return 50


# ============================
# STEP 3 — Add base speed column
# ============================

edges["base_speed_kmh"] = edges["highway"].apply(get_base_speed)


# ============================
# STEP 4 — Calculate free flow travel time
# ============================

# length is in meters → convert to km
edges["length_km"] = edges["length"] / 1000

# time = distance / speed
edges["free_flow_time_hr"] = edges["length_km"] / edges["base_speed_kmh"]

# convert to seconds
edges["free_flow_time_sec"] = edges["free_flow_time_hr"] * 3600


# ============================
# STEP 5 — Simulate congestion (for now)
# ============================

# simulate congestion factor
# 1.0 = no congestion
# 1.5 = medium congestion
# 2.0 = heavy congestion

import random

def simulate_congestion():
    return random.uniform(1.0, 2.0)

edges["congestion_factor"] = edges["highway"].apply(lambda x: simulate_congestion())

# actual travel time
edges["current_travel_time_sec"] = edges["free_flow_time_sec"] * edges["congestion_factor"]


# ============================
# STEP 6 — Calculate congestion percentage
# ============================

edges["congestion_percentage"] = (
    (edges["current_travel_time_sec"] - edges["free_flow_time_sec"])
    / edges["free_flow_time_sec"]
) * 100


# ============================
# STEP 7 — Detect congested roads
# ============================

def detect_congestion(percent):

    if percent < 20:
        return "LOW"

    elif percent < 50:
        return "MEDIUM"

    else:
        return "HIGH"


edges["congestion_level"] = edges["congestion_percentage"].apply(detect_congestion)


# ============================
# STEP 8 — Save output
# ============================

output_path = os.path.join(BASE_DIR, "..", "data", "processed", "colombo_network_edges_with_traffic.csv")

edges.to_csv(output_path, index=False)

print("\nTraffic analysis complete.")
print("File saved to:", output_path)


# ============================
# STEP 9 — Summary statistics
# ============================

print("\nCongestion Summary:")

print(edges["congestion_level"].value_counts())

print("\nAverage congestion:", edges["congestion_percentage"].mean(), "%")