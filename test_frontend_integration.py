#!/usr/bin/env python3
"""
Test script to verify frontend integration with lane violations
"""
import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def test_frontend_integration():
    """Test the complete frontend integration with lane violations"""
    print("🧪 Testing Frontend Integration with Lane Violations")
    print("=" * 60)

    try:
        # Test 1: Fetch lane violations
        print("\n1. Testing Lane Violations Fetch...")
        lane_response = requests.get(f"{API_BASE}/violations/lane", timeout=5)
        if lane_response.status_code == 200:
            lane_data = lane_response.json()
            print("✅ Lane violations fetched successfully")
            print(f"   Total lane violations: {lane_data.get('total_count', 0)}")
            if lane_data.get('violations'):
                print("   Sample lane violations:")
                for i, v in enumerate(lane_data['violations'][:3]):
                    print(f"     {i+1}. {v.get('type')} - {v.get('description')}")
        else:
            print(f"❌ Lane violations fetch failed: {lane_response.status_code}")
            return False

        # Test 2: Fetch violations summary
        print("\n2. Testing Violations Summary...")
        summary_response = requests.get(f"{API_BASE}/violations/summary", timeout=5)
        if summary_response.status_code == 200:
            summary_data = summary_response.json()
            print("✅ Violations summary fetched successfully")
            summary = summary_data.get('summary', {})
            print(f"   Total violations: {summary.get('total_violations', 0)}")
            print(f"   Speed violations: {summary.get('speed_violations', 0)}")
            print(f"   Lane violations: {summary.get('lane_violations', 0)}")
        else:
            print(f"❌ Violations summary fetch failed: {summary_response.status_code}")
            return False

        # Test 3: Fetch detection violations (speeding)
        print("\n3. Testing Speed Violations Fetch...")
        speed_response = requests.get(f"{API_BASE}/detection/violations", timeout=5)
        if speed_response.status_code == 200:
            speed_data = speed_response.json()
            print("✅ Speed violations fetched successfully")
            print(f"   Success: {speed_data.get('success', False)}")
            if speed_data.get('success'):
                violations = speed_data.get('violations', [])
                print(f"   Total speed violations: {len(violations)}")
        else:
            print(f"❌ Speed violations fetch failed: {speed_response.status_code}")
            return False

        # Test 4: Fetch safety alerts
        print("\n4. Testing Safety Alerts Fetch...")
        alerts_response = requests.get(f"{API_BASE}/detection/safety-alerts", timeout=5)
        if alerts_response.status_code == 200:
            alerts_data = alerts_response.json()
            print("✅ Safety alerts fetched successfully")
            print(f"   Total alerts: {alerts_data.get('total_count', 0)}")
        else:
            print(f"❌ Safety alerts fetch failed: {alerts_response.status_code}")
            return False

        # Test 5: Fetch detection stats
        print("\n5. Testing Detection Stats...")
        stats_response = requests.get(f"{API_BASE}/detection/stats", timeout=5)
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            print("✅ Detection stats fetched successfully")
            print(f"   Success: {stats_data.get('success', False)}")
        else:
            print(f"❌ Detection stats fetch failed: {stats_response.status_code}")
            return False

        print("\n" + "=" * 60)
        print("🎉 Frontend Integration Test PASSED!")
        print("✅ All API endpoints are working correctly")
        print("✅ Lane violations are available for frontend display")
        print("✅ Frontend should now show both speeding and lane violations")
        print("\n📱 Frontend URL: http://localhost:5174")
        print("🔗 Backend API: http://localhost:8000/api")

        return True

    except Exception as e:
        print(f"\n❌ Frontend integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_frontend_integration()
    exit(0 if success else 1)