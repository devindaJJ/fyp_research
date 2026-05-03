from services.live_traffic_service import get_live_travel_time

# Example coordinates in Colombo
origin_lat = 6.9271
origin_lng = 79.8612

dest_lat = 6.9147
dest_lng = 79.9737

time_sec = get_live_travel_time(origin_lat, origin_lng, dest_lat, dest_lng)

print("Live travel time:", time_sec, "seconds")
print("Live travel time:", time_sec/60, "minutes")