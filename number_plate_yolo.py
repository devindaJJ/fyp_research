import cv2
from ultralytics import YOLO
import easyocr
import re

model = YOLO(
    r"C:\Users\hp\Desktop\Vehicle Speed Detection\fyp_research\models\number_plate_yolo.pt"
)

reader = easyocr.Reader(['en'])

img_path = r"C:\Users\hp\Desktop\Vehicle Speed Detection\fyp_research\videos\speeding5.jpg"
img = cv2.imread(img_path)

results = model(img, imgsz=640, conf=0.25)

for r in results:
    for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        plate_img = img[y1:y2, x1:x2]

        # ===== OCR IMPROVEMENT =====
        plate_img = cv2.resize(plate_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        ocr_result = reader.readtext(thresh, detail=0)

        text = ""
        if ocr_result:
            text = " ".join(ocr_result)
            text = re.sub(r'[^A-Z0-9]', '', text)

        print("Detected Plate:", text)

        cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(img, text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

cv2.imshow("Sri Lankan ANPR", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
