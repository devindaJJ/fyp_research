#!/usr/bin/env python3
"""
Quick test script to verify lane violation API endpoints are working
"""
import requests
import json

API_BASE = "http://localhost:8000/api"

def test_lane_violations_endpoint():
    """Test the lane violations endpoint"""
    try:
        response = requests.get(f"{API_BASE}/violations/lane", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Lane violations endpoint working")
            print(f"   Success: {data.get('success', False)}")
            if data.get('success'):
                violations = data.get('violations', [])
                print(f"   Total lane violations: {len(violations)}")
                if violations:
                    print(f"   Sample violation: {violations[0]}")
            return True
        else:
            print(f"❌ Lane violations endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Lane violations endpoint error: {e}")
        return False

def test_violations_summary_endpoint():
    """Test the violations summary endpoint"""
    try:
        response = requests.get(f"{API_BASE}/violations/summary", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Violations summary endpoint working")
            print(f"   Success: {data.get('success', False)}")
            if data.get('success'):
                summary = data.get('summary', {})
                print(f"   Summary: {summary}")
            return True
        else:
            print(f"❌ Violations summary endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Violations summary endpoint error: {e}")
        return False

def test_detection_status():
    """Test the detection status endpoint"""
    try:
        response = requests.get(f"{API_BASE}/detection/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Detection status endpoint working")
            print(f"   Is processing: {data.get('is_processing', False)}")
            return True
        else:
            print(f"❌ Detection status endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Detection status endpoint error: {e}")
        return False

if __name__ == "__main__":
    print("Testing lane violation API endpoints...\n")

    results = []
    results.append(test_lane_violations_endpoint())
    results.append(test_violations_summary_endpoint())
    results.append(test_detection_status())

    print(f"\nResults: {sum(results)}/{len(results)} endpoints working")

    if all(results):
        print("🎉 All endpoints are working! Frontend should display lane violations.")
    else:
        print("⚠️  Some endpoints failed. Check backend logs.")