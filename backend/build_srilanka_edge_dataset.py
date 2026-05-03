import os
import pandas as pd
import osmnx as ox

GRAPH_FILE = os.path.join("data", "osm", "sri_lanka_drive.graphml")
OUTPUT_FILE = os.path.join("data", "osm", "sri_lanka_edges_enriched.csv")


def first_value(value):
    if isinstance(value, list):
        return str(value[0]) if len(value) > 0 else ""
    if value is None:
        return ""
    return str(value)


def normalize_text(value):
    return first_value(value).strip().lower()


def parse_speed_kph(maxspeed, highway):
    maxspeed_text = first_value(maxspeed)

    digits = "".join(ch for ch in maxspeed_text if ch.isdigit())
    if digits:
        return float(digits)

    highway = normalize_text(highway)

    if highway == "motorway":
        return 100
    elif highway == "motorway_link":
        return 70
    elif highway == "trunk":
        return 80
    elif highway == "trunk_link":
        return 60
    elif highway == "primary":
        return 60
    elif highway == "primary_link":
        return 50
    elif highway == "secondary":
        return 50
    elif highway == "secondary_link":
        return 45
    elif highway == "tertiary":
        return 40
    elif highway == "tertiary_link":
        return 35
    elif highway == "residential":
        return 30
    elif highway == "service":
        return 25
    else:
        return 35


def allow_vehicle(highway, access, bicycle, vehicle_type):
    highway = normalize_text(highway)
    access = normalize_text(access)
    bicycle = normalize_text(bicycle)

    if access == "no":
        return False

    if vehicle_type == "car":
        return True

    if vehicle_type == "bike":
        if highway in ["motorway", "motorway_link"]:
            return False
        if bicycle == "no":
            return False
        return True

    if vehicle_type == "three_wheeler":
        if highway in ["motorway", "motorway_link"]:
            return False
        return True

    if vehicle_type == "bus":
        if highway in ["service", "path", "footway", "cycleway"]:
            return False
        return True

    if vehicle_type == "lorry":
        if highway in ["service", "path", "footway", "cycleway"]:
            return False
        return True

    return True


def hourly_congestion_multiplier(highway, hour):
    highway = normalize_text(highway)

    if 0 <= hour < 5:
        if highway in ["motorway", "trunk", "primary"]:
            return 1.02
        return 1.05

    if 5 <= hour < 7:
        if highway in ["motorway", "trunk"]:
            return 1.08
        elif highway in ["primary", "secondary"]:
            return 1.15
        return 1.20

    if 7 <= hour < 10:
        if highway in ["motorway"]:
            return 1.20
        elif highway in ["trunk", "primary"]:
            return 1.40
        elif highway in ["secondary", "tertiary"]:
            return 1.55
        return 1.65

    if 10 <= hour < 16:
        if highway in ["motorway"]:
            return 1.08
        elif highway in ["trunk", "primary"]:
            return 1.18
        elif highway in ["secondary", "tertiary"]:
            return 1.28
        return 1.32

    if 16 <= hour < 20:
        if highway in ["motorway"]:
            return 1.22
        elif highway in ["trunk", "primary"]:
            return 1.48
        elif highway in ["secondary", "tertiary"]:
            return 1.62
        return 1.75

    return 1.10


def main():
    print("Loading Sri Lanka graph...")
    G = ox.load_graphml(GRAPH_FILE)
    print("Graph loaded.")

    rows = []
    sample_hour = 9

    for u, v, key, data in G.edges(keys=True, data=True):
        highway = normalize_text(data.get("highway", ""))
        road_name = first_value(data.get("name", ""))
        access = normalize_text(data.get("access", ""))
        bicycle = normalize_text(data.get("bicycle", ""))
        maxspeed = data.get("maxspeed", "")
        lanes = first_value(data.get("lanes", ""))
        oneway = first_value(data.get("oneway", ""))
        bridge = first_value(data.get("bridge", ""))
        tunnel = first_value(data.get("tunnel", ""))
        junction = first_value(data.get("junction", ""))
        toll = first_value(data.get("toll", ""))

        length = float(data.get("length", 0))
        speed_kph = parse_speed_kph(maxspeed, highway)

        if speed_kph <= 0:
            speed_kph = 35

        free_flow_time_sec = (length / 1000) / speed_kph * 3600
        congestion_mult = hourly_congestion_multiplier(highway, sample_hour)
        predicted_time_sec = free_flow_time_sec * congestion_mult

        rows.append({
            "u": u,
            "v": v,
            "key": key,
            "length_m": round(length, 2),
            "highway": highway,
            "road_name": road_name,
            "access": access,
            "bicycle": bicycle,
            "lanes": lanes,
            "oneway": oneway,
            "bridge": bridge,
            "tunnel": tunnel,
            "junction": junction,
            "toll": toll,
            "free_flow_speed_kph": round(speed_kph, 2),
            "free_flow_time_sec": round(free_flow_time_sec, 2),
            "hourly_congestion_multiplier": round(congestion_mult, 2),
            "predicted_time_sec": round(predicted_time_sec, 2),

            "allow_car_van": allow_vehicle(highway, access, bicycle, "car"),
            "allow_bike": allow_vehicle(highway, access, bicycle, "bike"),
            "allow_three_wheeler": allow_vehicle(highway, access, bicycle, "three_wheeler"),
            "allow_bus": allow_vehicle(highway, access, bicycle, "bus"),
            "allow_lorry": allow_vehicle(highway, access, bicycle, "lorry"),
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("Saved enriched dataset to:")
    print(OUTPUT_FILE)
    print("Total rows:", len(df))

    print("\nHighway type counts:")
    print(df["highway"].value_counts().head(20))

    print("\nBike not allowed count:")
    print((df["allow_bike"] == False).sum())

    print("\nThree-wheeler not allowed count:")
    print((df["allow_three_wheeler"] == False).sum())

    print("\nSample motorway rows:")
    print(df[df["highway"].str.contains("motorway", na=False)][
        ["highway", "road_name", "allow_bike", "allow_three_wheeler", "allow_car_van"]
    ].head(10))


if __name__ == "__main__":
    main()