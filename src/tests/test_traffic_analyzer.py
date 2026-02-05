"""
Tests for Traffic Analyzer
"""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from src.core.traffic_analyzer import TrafficAnalyzer, TrafficAnalysis
from src.models.traffic import TrafficLevel
from src.models.route import Route


class TestTrafficAnalyzer(unittest.TestCase):
    """Test cases for TrafficAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_gmaps = Mock()
        self.analyzer = TrafficAnalyzer(self.mock_gmaps)
    
    def test_determine_congestion_level(self):
        """Test congestion level determination."""
        # Test light traffic
        self.assertEqual(
            self.analyzer._determine_congestion_level(3),
            TrafficLevel.LIGHT
        )
        
        # Test moderate traffic
        self.assertEqual(
            self.analyzer._determine_congestion_level(10),
            TrafficLevel.MODERATE
        )
        
        # Test heavy traffic
        self.assertEqual(
            self.analyzer._determine_congestion_level(20),
            TrafficLevel.HEAVY
        )
        
        # Test severe traffic
        self.assertEqual(
            self.analyzer._determine_congestion_level(45),
            TrafficLevel.SEVERE
        )
    
    def test_calculate_alternative_score(self):
        """Test alternative route scoring."""
        # Create mock routes
        primary_route = Mock()
        primary_route.distance_meters = 10000
        primary_route.traffic_duration = 30
        primary_route.normal_duration = 20
        
        alternative = Mock()
        alternative.delay_minutes = 5
        alternative.distance_meters = 11000
        alternative.traffic_level = TrafficLevel.LIGHT
        
        current_delay = 10  # primary route delay
        
        score = self.analyzer._calculate_alternative_score(
            primary_route, alternative, current_delay
        )
        
        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)
    
    @patch('src.core.traffic_analyzer.LocationService')
    def test_analyze_with_auto_location(self, mock_location_service):
        """Test analysis with automatic location detection."""
        # Mock location service
        mock_location = Mock()
        mock_location.address = "Colombo, Sri Lanka"
        mock_location_service.return_value.detect_current_location.return_value = mock_location
        
        # Mock Google Maps response
        mock_route_data = {
            'legs': [{
                'start_address': 'Colombo, Sri Lanka',
                'end_address': 'Kandy, Sri Lanka',
                'duration': {'value': 7200},  # 2 hours in seconds
                'duration_in_traffic': {'value': 9000},  # 2.5 hours
                'distance': {'value': 115000, 'text': '115 km'},
                'steps': []
            }],
            'summary': 'Route 1',
            'overview_polyline': {'points': ''}
        }
        
        self.mock_gmaps.get_route_alternatives.return_value = [mock_route_data]
        
        analysis = self.analyzer.analyze_with_auto_location("Kandy, Sri Lanka")
        
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.primary_route.origin, "Colombo, Sri Lanka")
        self.assertEqual(analysis.primary_route.destination, "Kandy, Sri Lanka")


    def test_parse_route_steps_includes_segments(self):
        """Ensure per-step delays and traffic levels are computed and present."""
        mock_route_data = {
            'legs': [{
                'start_address': 'Colombo, Sri Lanka',
                'end_address': 'Kandy, Sri Lanka',
                'duration': {'value': 600},  # 10 minutes
                'duration_in_traffic': {'value': 900},  # 15 minutes
                'distance': {'value': 20000, 'text': '20 km'},
                'steps': [
                    {
                        'html_instructions': 'Head north',
                        'distance': {'text': '5 km'},
                        'duration': {'text': '5 mins', 'value': 300},
                        'duration_in_traffic': {'value': 600},
                        'polyline': {'points': '??'}
                    },
                    {
                        'html_instructions': 'Continue',
                        'distance': {'text': '15 km'},
                        'duration': {'text': '5 mins', 'value': 300},
                        'duration_in_traffic': {'value': 300},
                        'polyline': {'points': '??'}
                    }
                ]
            }],
            'summary': 'Route 1',
            'overview_polyline': {'points': ''}
        }

        # Directly parse route
        route = self.analyzer._parse_route(mock_route_data, 'Colombo, Sri Lanka', 'Kandy, Sri Lanka')
        self.assertIsNotNone(route)
        self.assertTrue(hasattr(route, 'steps'))
        self.assertGreaterEqual(len(route.steps), 2)
        # Each step should include delay_minutes and traffic_level
        for s in route.steps:
            self.assertIn('delay_minutes', s)
            self.assertIn('traffic_level', s)
            self.assertIsInstance(s['delay_minutes'], float)
            # traffic_level should be an enum-like object with value
            self.assertTrue(hasattr(s['traffic_level'], 'value'))


if __name__ == '__main__':
    unittest.main()