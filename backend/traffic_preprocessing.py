import pandas as pd

# ===== 1. LOAD DATA =====
input_file = "data/processed/colombo_network_edges_with_time.csv"
output_file = "data/processed/colombo_network_edges_processed.csv"

df = pd.read_csv(input_file)

# ===== 2. CLASSIFY ROAD CATEGORY =====

def classify_road(highway_type):
    if highway_type == "motorway":
        return "motorway"
    elif highway_type == "trunk":
        return "trunk"
    elif highway_type in ["primary", "secondary"]:
        return "urban_main"
    elif highway_type == "tertiary":
        return "tertiary"
    elif highway_type in ["residential", "service", "unclassified"]:
        return "local"
    else:
        return "local"

df["road_category"] = df["highway"].apply(classify_road)

# ===== 3. ADD VEHICLE ACCESS RULES =====

# Default: all vehicles allowed
df["allow_bike"] = True
df["allow_three_wheeler"] = True
df["allow_car"] = True
df["allow_van"] = True
df["allow_bus"] = True
df["allow_lorry"] = True

# Apply motorway restrictions
motorway_mask = df["road_category"] == "motorway"

df.loc[motorway_mask, "allow_bike"] = False
df.loc[motorway_mask, "allow_three_wheeler"] = False

# ===== 4. SAVE UPDATED DATA =====
df.to_csv(output_file, index=False)

print("✅ Preprocessing completed.")
print("Saved as:", output_file)