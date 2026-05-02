"""
Tests for Location Service
"""
import unittest
from unittest.mock import Mock, patch
from src.core.location_service import LocationService, Location
from src.api.google_maps_client import GoogleMapsClient


class TestLocationService(unittest.TestCase):
    """Test cases for LocationService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_gmaps = Mock(spec=GoogleMapsClient)
        self.service = LocationService(self.mock_gmaps)
    
    def test_location_creation(self):
        """Test Location dataclass creation."""
        location = Location(
            latitude=6.9271,
            longitude=79.8612,
            address="Colombo, Sri Lanka",
            city="Colombo",
            country="Sri Lanka",
            accuracy=0.9,
            source="test"
        )
        
        self.assertEqual(location.latitude, 6.9271)
        self.assertEqual(location.longitude, 79.8612)
        self.assertEqual(location.city, "Colombo")
        self.assertEqual(location.accuracy, 0.9)
    
    def test_to_coordinates(self):
        """Test coordinates string conversion."""
        location = Location(
            latitude=6.9271,
            longitude=79.8612,
            address="Test",
            city="Test",
            country="Test"
        )
        
        self.assertEqual(location.to_coordinates(), "6.9271,79.8612")
    
    @patch('requests.get')
    def test_get_public_ip(self, mock_get):
        """Test getting public IP."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "203.0.113.1"
        
        ip = self.service._get_public_ip()
        self.assertEqual(ip, "203.0.113.1")
    
    def test_is_in_sri_lanka(self):
        """Test Sri Lanka bounds check."""
        # Test Colombo (should be in Sri Lanka)
        colombo = Location(
            latitude=6.9271,
            longitude=79.8612,
            address="Colombo",
            city="Colombo",
            country="Sri Lanka"
        )
        self.assertTrue(colombo.is_in_sri_lanka())
        
        # Test London (should not be in Sri Lanka)
        london = Location(
            latitude=51.5074,
            longitude=-0.1278,
            address="London",
            city="London",
            country="UK"
        )
        self.assertFalse(london.is_in_sri_lanka())


if __name__ == '__main__':
    unittest.main()