import cv2
from ultralytics import YOLO
import easyocr

# Load trained model
model = YOLO("models/number_plate_yolo.pt")

# OCR reader
reader = easyocr.Reader(['en'])

# Video path
video_path = r"C:\Users\hp\Desktop\Vehicle Speed Detection\fyp_research\videos\speeding3.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Cannot open video")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            plate_img = frame[y1:y2, x1:x2]

            # OCR
            ocr_result = reader.readtext(plate_img, detail=0)

            if ocr_result:
                text = ocr_result[0]
                print("Detected Plate:", text)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, text, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    cv2.imshow("Sri Lankan ANPR", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
