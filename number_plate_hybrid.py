import cv2
from ultralytics import YOLO
import easyocr
import numpy as np

# Initialize OCR
print("Initializing OCR...")
reader = easyocr.Reader(['en'])

# Load YOLOv8 model (for vehicles)
print("Loading YOLOv8 model...")
model = YOLO("yolov8n.pt")

# Load Haar Cascade (for plates)
print("Loading Haar Cascade...")
plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_russian_plate_number.xml")

# Video path
video_path = r"C:\Users\hp\Desktop\Vehicle Speed Detection\fyp_research\videos\speeding3.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: Cannot open video at {video_path}")
    exit()

# Vehicle classes in COCO dataset: 2=car, 3=motorcycle, 5=bus, 7=truck
vehicle_classes = [2, 3, 5, 7]

print("Starting video processing...")
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame/image.")
        break
        
    print(f"Frame shape: {frame.shape}")

    # 1. Detect Vehicles with YOLO
    results = model(frame, stream=True, verbose=False)

    for r in results:
        boxes = r.boxes
        print(f"YOLO found {len(boxes)} objects") # Debug count
        
        for box in boxes:
            # Check class
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            
            print(f" - Object: Class {cls}, Conf {conf:.2f}")

            if cls not in vehicle_classes:
                print(f"   > Ignored (Not a vehicle)")
                continue

            if conf < 0.1: # Extremely low confidence for debug
                print(f"   > Ignored (Low confidence)")
                continue

            # Get Vehicle Coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            print(f"   > Vehicle accepted at {x1},{y1} size {x2-x1}x{y2-y1}")
            
            # Draw Vehicle Box (Blue)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, "Vehicle", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            # Crop Vehicle
            vehicle_img = frame[y1:y2, x1:x2]
            if vehicle_img.size == 0:
                continue

            # 2. Detect Plates inside Vehicle with Haar Cascade
            gray_vehicle = cv2.cvtColor(vehicle_img, cv2.COLOR_BGR2GRAY)
            # Relaxed parameters: scaleFactor 1.1 -> 1.05, minNeighbors 4 -> 3
            plates = plate_cascade.detectMultiScale(gray_vehicle, scaleFactor=1.05, minNeighbors=3, minSize=(10, 10))

            if len(plates) > 0:
                print(f"Haar: Found {len(plates)} candidate plates in vehicle.")

            for (px, py, pw, ph) in plates:
                # Plate coordinates relative to vehicle crop
                # Convert to global coordinates for drawing
                gx = x1 + px
                gy = y1 + py
                
                # Draw Plate Box (Green)
                cv2.rectangle(frame, (gx, gy), (gx+pw, gy+ph), (0, 255, 0), 2)

                # Crop Plate
                plate_crop = gray_vehicle[py:py+ph, px:px+pw]
                
                # Check size
                h, w = plate_crop.shape
                print(f"  > Plate crop size: {w}x{h}")
                
                if w < 10 or h < 5:
                    print("  > Skip: Too small")
                    continue

                # Preprocess for OCR
                # Resize to make text bigger (helpful for OCR)
                # scale_factor = 3
                plate_upscaled = cv2.resize(plate_crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                
                # Show debug windows (Raw crop vs Upscaled)
                cv2.imshow("Debug Plate Raw", plate_crop)
                cv2.imshow("Debug Plate Upscaled", plate_upscaled)

                # 3. OCR
                # Use upscaled grayscale image. Do NOT threshold manually. EasyOCR does it better.
                try:
                    ocr_res = reader.readtext(plate_upscaled, detail=1)
                    
                    if not ocr_res:
                         print("  > OCR returned no results.")

                    full_text = ""
                    for (bbox, text, prob) in ocr_res:
                        print(f"  > OCR raw: '{text}' prob {prob:.2f}")
                        if prob > 0.2: 
                            cleaned_text = text.replace(" ", "").upper()
                            full_text += cleaned_text
                    
                    if full_text: 
                        print(f"Detected Plate Text: {full_text}")
                        cv2.putText(frame, full_text, (gx, gy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                except Exception as e:
                    print(f"OCR Error: {e}")

    cv2.imshow("Hybrid Detection", frame)

    # Check if input is an image (by extension or behavior)
    is_image = video_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))
    
    if is_image:
        # Wait indefinitely for images so window doesn't close
        print("Image processing complete. Press any key to exit.")
        cv2.waitKey(0)
        break
    else:
        # Wait 1ms for video
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
