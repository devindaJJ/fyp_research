import cv2
from ultralytics import YOLO
import easyocr

# Initialize OCR
reader = easyocr.Reader(['en'])

# Load YOLOv8 model (pretrained for demo)
model = YOLO("yolov8n.pt")  # replace with custom plate model later if available

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

    # YOLOv8 detects objects (plates)
    results = model(frame)

    # Loop through detections
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])  # get box coordinates
            conf = float(box.conf[0])
            
            # Only process boxes with high confidence
            if conf > 0.3:
                plate_img = frame[y1:y2, x1:x2]
                
                # Check if plate_img is valid
                if plate_img.size == 0:
                    continue

                # Preprocess for OCR
                gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                _, gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                
                # Show debug windows
                cv2.imshow("Debug Plate Crop", plate_img)
                cv2.imshow("Debug OCR Preprocess", gray)

                # OCR detection
                try:
                    result = reader.readtext(gray)
                    text = ""
                    for detection in result:
                        text += detection[1].replace(" ", "")
                    
                    # Draw results
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    
                    if text.strip():
                        print(f"Detected: '{text}' (Conf: {conf:.2f})")
                    else:
                        print(f"Empty OCR result (Conf: {conf:.2f})")
                        
                except Exception as e:
                    print("OCR error:", e)

    cv2.imshow("YOLOv8 Number Plate Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
