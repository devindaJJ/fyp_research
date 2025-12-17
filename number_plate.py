import cv2
import easyocr

# Initialize OCR
reader = easyocr.Reader(['en'])

# Path to your video
video_path = r"C:\Users\hp\Desktop\Vehicle Speed Detection\fyp_research\videos\speeding2.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Cannot open video")
    exit()

frame_count = 0  # To optionally skip frames for speed

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    # Optional: skip some frames to reduce flicker/processing load
    if frame_count % 2 != 0:
        continue

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(blur, 30, 200)

    contours, _ = cv2.findContours(
        edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.018 * peri, True)
        if len(approx) == 4:
            plate = approx
            break

    if plate is not None:
        x, y, w, h = cv2.boundingRect(plate)
        plate_img = gray[y:y+h, x:x+w]

        # Resize for better OCR
        plate_img = cv2.resize(plate_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Threshold to enhance contrast
        _, plate_img = cv2.threshold(plate_img, 150, 255, cv2.THRESH_BINARY)

        # OCR detection
        try:
            result = reader.readtext(plate_img)
            for detection in result:
                text = detection[1].replace(" ", "")  # Remove spaces for cleaner plate
                cv2.putText(
                    frame,
                    text,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2
                )
                print("Detected:", text)
        except Exception as e:
            print("OCR error:", e)

        # Draw green rectangle around detected plate
        cv2.drawContours(frame, [plate], -1, (0, 255, 0), 2)

    # Display the video frame
    cv2.imshow("Number Plate Detection", frame)

    # Press 'Q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
