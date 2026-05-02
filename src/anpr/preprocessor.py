"""
Image preprocessing utilities for number plate OCR enhancement.
"""
import cv2
import numpy as np


class PlatePreprocessor:
    """
    Handles preprocessing of number plate images to improve OCR accuracy.
    """
    
    @staticmethod
    def enhance_for_ocr(plate_img, scale_factor=2):
        """
        Apply preprocessing pipeline to enhance plate image for OCR.
        
        Args:
            plate_img: Input plate image (BGR format)
            scale_factor: Upscaling factor for better OCR (default: 2x)
            
        Returns:
            Preprocessed binary image ready for OCR
        """
        # Upscale for better OCR accuracy
        plate_img = cv2.resize(
            plate_img, 
            None, 
            fx=scale_factor, 
            fy=scale_factor, 
            interpolation=cv2.INTER_CUBIC
        )
        
        # Convert to grayscale
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # Reduce noise while preserving edges
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Apply binary threshold to make text stand out
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        return thresh
    
    @staticmethod
    def adaptive_threshold(plate_img, scale_factor=2):
        """
        Alternative preprocessing using adaptive thresholding.
        
        Args:
            plate_img: Input plate image (BGR format)
            scale_factor: Upscaling factor
            
        Returns:
            Preprocessed binary image
        """
        plate_img = cv2.resize(
            plate_img, 
            None, 
            fx=scale_factor, 
            fy=scale_factor, 
            interpolation=cv2.INTER_CUBIC
        )
        
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding for varying lighting conditions
        thresh = cv2.adaptiveThreshold(
            gray, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 
            2
        )
        
        return thresh