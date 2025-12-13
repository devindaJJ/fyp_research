import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# -----------------------------------
# CONFIGURATION
# -----------------------------------
VIDEO_PATH = "videos/speeding2.mp4"   # change video name here
DISTANCE_BETWEEN_LINES = 20           # meters (adjust per camera)
SPEED_LIMIT = 60                      # km/h

LINE_A = 400                          # first virtual line (pixels)
LINE_B = 1800                          # second virtual line (pixels)

VEHICLE_CLASSES = ["car", "motorcycle", "bus", "truck"]

# -----------------------------------
# LOAD MODELS
# -----------------------------------
model = YOLO("yolov8n.pt")
tracker = DeepSort(max_age=30, n_init=3)

# Store timestamps for each vehicle
vehicle_data = {}  # {track_id: {'t1': None, 't2': None, 'speed_done': False}}

# -----------------------------------
# LOAD VIDEO
# -----------------------------------
cap = cv2.VideoCapture(VIDEO_PATH)

# Resize window so FULL video is visible
cv2.namedWindow("Vehicle Speed Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Vehicle Speed Detection", 1280, 720)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # -----------------------------------
    # YOLO DETECTION
    # -----------------------------------
    results = model(frame, verbose=False)

    detections = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]

            if cls_name in VEHICLE_CLASSES:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append([[x1, y1, x2, y2], conf])

    # -----------------------------------
    # DEEPSORT TRACKING
    # -----------------------------------
    tracks = tracker.update_tracks(detections, frame=frame)
    active_ids = []

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = track.track_id
        active_ids.append(track_id)

        x1, y1, x2, y2 = map(int, track.to_ltrb())
        center_y = (y1 + y2) // 2

        # Initialize vehicle
        if track_id not in vehicle_data:
            vehicle_data[track_id] = {"t1": None, "t2": None, "speed_done": False}

        # Line A crossing
        if vehicle_data[track_id]["t1"] is None and center_y > LINE_A:
            vehicle_data[track_id]["t1"] = cv2.getTickCount() / cv2.getTickFrequency()

        # Line B crossing
        elif vehicle_data[track_id]["t2"] is None and center_y > LINE_B:
            vehicle_data[track_id]["t2"] = cv2.getTickCount() / cv2.getTickFrequency()

        # Speed calculation (once)
        if (
            vehicle_data[track_id]["t1"]
            and vehicle_data[track_id]["t2"]
            and not vehicle_data[track_id]["speed_done"]
        ):
            t1 = vehicle_data[track_id]["t1"]
            t2 = vehicle_data[track_id]["t2"]

            speed_mps = DISTANCE_BETWEEN_LINES / (t2 - t1)
            speed_kmh = speed_mps * 3.6

            vehicle_data[track_id]["speed"] = speed_kmh
            vehicle_data[track_id]["speed_done"] = True

        # -----------------------------------
        # DRAW BOX & LABEL
        # -----------------------------------
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID {track_id}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if "speed" in vehicle_data[track_id]:
            speed = vehicle_data[track_id]["speed"]
            cv2.putText(frame, f"{int(speed)} km/h", (x1, y2 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            if speed > SPEED_LIMIT:
                cv2.putText(frame, "SPEEDING!", (x1, y1 - 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # -----------------------------------
    # DRAW VIRTUAL LINES
    # -----------------------------------
    cv2.line(frame, (0, LINE_A), (frame.shape[1], LINE_A), (255, 0, 0), 2)
    cv2.line(frame, (0, LINE_B), (frame.shape[1], LINE_B), (0, 0, 255), 2)

    # -----------------------------------
    # CLEAN OLD TRACKS
    # -----------------------------------
    for vid in list(vehicle_data.keys()):
        if vid not in active_ids:
            del vehicle_data[vid]

    # -----------------------------------
    # SHOW OUTPUT
    # -----------------------------------
    cv2.imshow("Vehicle Speed Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
