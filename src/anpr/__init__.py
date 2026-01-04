"""
ANPR (Automatic Number Plate Recognition) module for Sri Lankan vehicle plates.
"""
from src.anpr.detector import NumberPlateDetector
from src.anpr.preprocessor import PlatePreprocessor
from src.anpr.validator import validate_sri_lankan_plate

__all__ = ['NumberPlateDetector', 'PlatePreprocessor', 'validate_sri_lankan_plate']