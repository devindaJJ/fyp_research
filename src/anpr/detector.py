"""
Number plate detection and recognition using YOLO and OCR.
"""
import cv2
from ultralytics import YOLO
import easyocr
from typing import List, Tuple, Optional

from src.anpr.preprocessor import PlatePreprocessor
from src.anpr.validator import clean_plate_text, validate_sri_lankan_plate


class NumberPlateDetector:
    """
    Detects and reads vehicle number plates using YOLO object detection and EasyOCR.
    """
    
    def __init__(self, model_path: str, languages: List[str] = None, 
                 confidence_threshold: float = 0.25, image_size: int = 640):
        """
        Initialize the number plate detector.
        
        Args:
            model_path: Path to the YOLO model for plate detection
            languages: List of languages for OCR (default: ['en'])
            confidence_threshold: Minimum confidence for plate detection (default: 0.25)
            image_size: Image size for YOLO inference (default: 640)
        """
        # Attempt to load YOLO model; if it fails, disable plate detection
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            # log error and fallback to no-detection mode
            print(f"[WARNING] NumberPlateDetector could not load model '{model_path}': {e}")
            self.model = None

        # initialize OCR reader even if model failed; OCR is cheap
        try:
            self.reader = easyocr.Reader(languages or ['en'])
        except Exception as e:
            print(f"[WARNING] EasyOCR reader initialization failed: {e}")
            self.reader = None

        self.preprocessor = PlatePreprocessor()
        self.confidence_threshold = confidence_threshold
        self.image_size = image_size
    
    def detect_plates(self, image) -> List[Tuple[int, int, int, int]]:
        """
        Detect number plate regions in the image.
        
        Args:
            image: Input image (numpy array)
            
        Returns:
            List of bounding boxes [(x1, y1, x2, y2), ...]
        """
        if self.model is None:
            # model not available, skip detection
            return []

        results = self.model(image, imgsz=self.image_size, conf=self.confidence_threshold)
        
        plates = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                plates.append((x1, y1, x2, y2))
        
        return plates
    
    def read_plate_text(self, plate_img, validate: bool = True) -> Optional[str]:
        """
        Read text from a number plate image using OCR.
        
        Args:
            plate_img: Cropped plate image
            validate: Whether to validate against Sri Lankan formats (default: True)
            
        Returns:
            Recognized plate text or None if validation fails
        """
        # Preprocess image for better OCR
        preprocessed = self.preprocessor.enhance_for_ocr(plate_img)
        
        # Perform OCR (if reader available)
        if self.reader:
            ocr_result = self.reader.readtext(preprocessed, detail=0)
            # Clean the text
            text = clean_plate_text(ocr_result)
        else:
            text = None
        
        # Validate format if required
        if validate and text and not validate_sri_lankan_plate(text):
            return None
        
        return text if text else None
    
    def detect_and_read(self, image, draw_results: bool = False):
        """
        Detect plates and read text in one pass.
        
        Args:
            image: Input image
            draw_results: Whether to draw bounding boxes and text on image
            
        Returns:
            List of tuples [(bbox, text), ...] and optionally annotated image
        """
        plates_data = []
        annotated_image = image.copy() if draw_results else None
        
        # Detect plate regions
        plate_boxes = self.detect_plates(image)
        
        for x1, y1, x2, y2 in plate_boxes:
            # Extract plate region
            plate_img = image[y1:y2, x1:x2]
            
            # Read plate text
            text = self.read_plate_text(plate_img, validate=False)
            
            plates_data.append({
                'bbox': (x1, y1, x2, y2),
                'text': text,
                'valid': validate_sri_lankan_plate(text) if text else False
            })
            
            # Draw on image if requested
            if draw_results:
                color = (0, 255, 0) if text else (0, 0, 255)
                cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
                
                if text:
                    cv2.putText(
                        annotated_image, 
                        text, 
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.9, 
                        color, 
                        2
                    )
        
        if draw_results:
            return plates_data, annotated_image
        return plates_data