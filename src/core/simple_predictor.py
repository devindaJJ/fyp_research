"""
ULTRA-SIMPLE PREDICTOR
No ML, just basic rules
"""
from typing import Dict

class SimplePredictor:
    @staticmethod
    def predict_traffic(current_time: float, historical_avg: float) -> Dict:
        """
        Basic prediction: Compare current vs historical
        """
        if not historical_avg:
            return {
                "status": "NO_DATA",
                "message": "Insufficient historical data",
                "confidence": 0
            }
        
        # Calculate difference
        difference = current_time - historical_avg
        difference_percent = (difference / historical_avg) * 100
        
        # Simple rules for Sri Lanka
        if difference_percent > 30:
            status = "VERY_HEAVY"
            message = "Much worse than usual"
            action = "Leave 15+ minutes earlier"
        elif difference_percent > 15:
            status = "HEAVY"
            message = "Worse than usual"
            action = "Leave 10 minutes earlier"
        elif difference_percent < -10:
            status = "LIGHT"
            message = "Better than usual"
            action = "Normal departure OK"
        else:
            status = "NORMAL"
            message = "Typical traffic conditions"
            action = "Plan normal travel time"
        
        # Simple confidence based on data points
        confidence = min(80, historical_avg)  # Placeholder
        
        return {
            "status": status,
            "current_time": round(current_time, 1),
            "historical_avg": round(historical_avg, 1),
            "difference_percent": round(difference_percent, 1),
            "message": message,
            "action": action,
            "confidence": confidence
        }
    
    @staticmethod
    def get_simple_forecast(origin: str, destination: str, hour: int) -> str:
        """
        Generate simple text forecast for display
        """
        # Hardcoded patterns for Sri Lanka 
        patterns = {
            ("Colombo", "Kandy"): {
                8: "Morning peak to Kandy: Usually heavy 7-9 AM",
                17: "Evening return: Often congested 5-7 PM"
            },
            ("Colombo", "Katunayake Airport"): {
                8: "Airport route: Moderate, allow extra time for security",
                14: "Afternoon: Usually smooth, check flight status"
            }
        }
        
        key = (origin, destination)
        if key in patterns and hour in patterns[key]:
            return patterns[key][hour]
        
        return "Standard travel conditions expected"