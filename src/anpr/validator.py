"""
Validation utilities for Sri Lankan number plate formats.
"""
import re


def validate_sri_lankan_plate(text):
    """
    Validate if the text matches Sri Lankan number plate patterns.
    
    Common Sri Lankan formats:
    - ABC1234 (Old format: 3 letters + 4 digits)
    - ABC1234 (New format with province codes)
    - 123-1234 (Commercial vehicles)
    
    Args:
        text: Recognized plate text (alphanumeric only)
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not text or len(text) < 6:
        return False
    
    # Pattern 1: 2-3 letters followed by 4 digits (e.g., CAA1234, WP-CAA1234)
    pattern1 = r'^[A-Z]{2,3}\d{4}$'
    
    # Pattern 2: Province code + letters + digits (e.g., WPCAA1234)
    pattern2 = r'^[A-Z]{2,4}\d{4}$'
    
    # Pattern 3: Commercial format (digits-digits)
    pattern3 = r'^\d{3}\d{4}$'
    
    return bool(
        re.match(pattern1, text) or 
        re.match(pattern2, text) or 
        re.match(pattern3, text)
    )


def clean_plate_text(ocr_result):
    """
    Clean and format OCR results for number plates.
    
    Args:
        ocr_result: Raw OCR output (list of strings)
        
    Returns:
        Cleaned alphanumeric string
    """
    if not ocr_result:
        return ""
    
    # Join all detected text elements
    text = " ".join(ocr_result)
    
    # Remove all non-alphanumeric characters
    text = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    return text