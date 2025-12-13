import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# -------------------------------
# Configuration
# -------------------------------
VIDEO_PATH = "videos/speeding2.mp4"  # path to your video
DISTANCE_BETWEEN_LINES = 20  # meters (adjust based on camera view)
SPEED_LIMIT = 60  # km/h

LINE_A = 200  # first line y-coordinate in pixels
LINE_B = 400  # second line y-coordinate in pixels

VEHICLE_CLASSES = ["car", "motorcycle", "bus", "truck"]

# -------------------------------
# Initialize models
# -------------------------------
model = YOLO("yolov8n.pt")
tracker = DeepSort(max_age=30, n_init=3)

# Dictionary to store vehicle timestamps and speed flags
vehicle_timestamps = {}  # {track_id: {'T1': None, 'T2': None, 'speed_recorded': False}}

# -------------------------------
# Load video
# -------------------------------
cap = cv2.VideoCapture(VIDEO_PATH)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # -------------------------------
    # YOLO Detection
    # -------------------------------
    results = model(frame)

    dets = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]

            if class_name in VEHICLE_CLASSES:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                dets.append([[x1, y1, x2, y2], conf])  # correct format for DeepSORT

    # -------------------------------
    # Update Tracker
    # -------------------------------
    tracks = tracker.update_tracks(dets, frame=frame)

    current_ids = []

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = track.track_id
        current_ids.append(track_id)
        x1, y1, x2, y2 = map(int, track.to_ltrb())
        center_y = (y1 + y2) // 2

        # Initialize vehicle record
        if track_id not in vehicle_timestamps:
            vehicle_timestamps[track_id] = {'T1': None, 'T2': None, 'speed_recorded': False}

        # Record crossing Line A
        if vehicle_timestamps[track_id]['T1'] is None and center_y > LINE_A:
            vehicle_timestamps[track_id]['T1'] = cv2.getTickCount() / cv2.getTickFrequency()

        # Record crossing Line B
        elif vehicle_timestamps[track_id]['T2'] is None and center_y > LINE_B:
            vehicle_timestamps[track_id]['T2'] = cv2.getTickCount() / cv2.getTickFrequency()

        # Calculate speed only once
        if (vehicle_timestamps[track_id]['T1'] and
            vehicle_timestamps[track_id]['T2'] and
            not vehicle_timestamps[track_id]['speed_recorded']):

            t1 = vehicle_timestamps[track_id]['T1']
            t2 = vehicle_timestamps[track_id]['T2']
            speed_m_s = DISTANCE_BETWEEN_LINES / (t2 - t1)
            speed_kmh = speed_m_s * 3.6

            cv2.putText(frame, f"Speed: {int(speed_kmh)} km/h", (x1, y2+20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            if speed_kmh > SPEED_LIMIT:
                cv2.putText(frame, "SPEEDING!", (x1, y1-25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            vehicle_timestamps[track_id]['speed_recorded'] = True

        # Draw bounding box and ID
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID:{track_id}", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # -------------------------------
    # Draw Virtual Lines
    # -------------------------------
    cv2.line(frame, (0, LINE_A), (frame.shape[1], LINE_A), (255, 0, 0), 2)  # Line A: blue
    cv2.line(frame, (0, LINE_B), (frame.shape[1], LINE_B), (0, 0, 255), 2)  # Line B: red

    # -------------------------------
    # Cleanup exited vehicles
    # -------------------------------
    for vid in list(vehicle_timestamps.keys()):
        if vid not in current_ids:
            del vehicle_timestamps[vid]

    # -------------------------------
    # Display Frame
    # -------------------------------
    cv2.imshow("Vehicle Tracking", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
