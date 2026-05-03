import pandas as pd
from datetime import datetime

# Load processed data
df = pd.read_csv("data/processed/colombo_network_edges_processed.csv")

# ----------------------------------
# 1️⃣ Define realistic default speeds (km/h)
# ----------------------------------
default_speed = {
    "motorway": 100,
    "trunk": 80,
    "primary": 60,
    "secondary": 50,
    "tertiary": 40,
    "residential": 30,
    "service": 25
}

# Map speed based on highway type
df["speed_kph"] = df["highway"].map(default_speed)

# Fill missing speeds with 35 km/h
df["speed_kph"] = df["speed_kph"].fillna(35)

# ----------------------------------
# 2️⃣ Calculate travel_time_sec properly
# length is in meters
# speed convert km/h → m/s
# ----------------------------------
df["travel_time_sec"] = df["length"] / (df["speed_kph"] * 1000 / 3600)

# ----------------------------------
# 3️⃣ Road multiplier
# ----------------------------------
road_multiplier = {
    "motorway": 0.8,
    "trunk": 0.9,
    "primary": 1.0,
    "secondary": 1.2,
    "tertiary": 1.3,
    "residential": 1.5,
    "service": 1.6
}

df["road_multiplier"] = df["highway"].map(road_multiplier).fillna(1.4)

# ----------------------------------
# 4️⃣ Time of day multiplier
# ----------------------------------
current_hour = datetime.now().hour

if 7 <= current_hour <= 9:
    time_multiplier = 1.8
elif 16 <= current_hour <= 19:
    time_multiplier = 2.0
elif 22 <= current_hour or current_hour <= 5:
    time_multiplier = 0.7
else:
    time_multiplier = 1.2

# ----------------------------------
# 5️⃣ Final predicted time
# ----------------------------------
df["predicted_time"] = df["travel_time_sec"] * df["road_multiplier"] * time_multiplier

# Save
df.to_csv("data/processed/colombo_network_with_prediction.csv", index=False)

print("✅ Traffic prediction completed.")
print("Saved as: data/processed/colombo_network_with_prediction.csv")