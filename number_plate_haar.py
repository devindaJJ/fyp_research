import cv2
import easyocr

# Initialize OCR
reader = easyocr.Reader(['en'])

# Video path
video_path = r"C:\Users\hp\Desktop\Vehicle Speed Detection\fyp_research\videos\speeding3.mp4"
cap = cv2.VideoCapture(video_path)

# Load Haar Cascade
# The path found: anpr-env\Lib\site-packages\cv2\data\haarcascade_russian_plate_number.xml
# We will use cv2.data.haarcascades to automatically find it
plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_russian_plate_number.xml")

if plate_cascade.empty():
    print("Error: Could not load Haar Cascade XML file.")
    exit()

if not cap.isOpened():
    print("Error: Cannot open video")
    exit()

print("Processing video... Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect plates
    plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(plates) > 0:
        print(f"Found {len(plates)} potential plates")

    for (x, y, w, h) in plates:
        # Draw detection box
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Crop plate
        plate_img = gray[y:y+h, x:x+w]
        
        # Preprocess
        # Resize for better OCR
        plate_img = cv2.resize(plate_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        # Threshold
        _, plate_thresh = cv2.threshold(plate_img, 150, 255, cv2.THRESH_BINARY)

        cv2.imshow("Plate Crop", plate_thresh)

        # OCR
        try:
            result = reader.readtext(plate_thresh)
            text = ""
            for detection in result:
                text += detection[1].replace(" ", "")
            
            if text.strip():
                print(f"Detected: {text}")
                cv2.putText(frame, text, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        except Exception as e:
            pass

    cv2.imshow("Haar Plate Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
