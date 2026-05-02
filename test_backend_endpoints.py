#!/usr/bin/env python3
"""
Test script for new lane violation API endpoints
"""
import requests
import json
import time
import threading
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_backend():
    """Test backend API endpoints"""
    print("\n" + "="*80)
    print("BACKEND API ENDPOINT TESTING")
    print("="*80)
    
    # Test 1: Check if backend is running
    print("\n[TEST 1] Testing backend status...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        print(f"✓ Backend is running: {response.json()}")
    except Exception as e:
        print(f"✗ Backend not running or error: {e}")
        return False
    
    # Test 2: Start detection with lane 1.mp4
    print("\n[TEST 2] Starting detection with lane 1.mp4...")
    try:
        video_path = "videos/lane 1.mp4"
        response = requests.post(
            f"{BASE_URL}/api/detection/start",
            json={"video_path": video_path},
            timeout=30  # Increased timeout for detector initialization
        )
        result = response.json()
        print(f"✓ Detection started: {result['message']}")
        print(f"  Video: {result['video']}")
        
        # Wait for processing to start
        time.sleep(5)
        
    except Exception as e:
        print(f"✗ Failed to start detection: {e}")
        return False
    
    # Test 3: Get detection status
    print("\n[TEST 3] Checking detection status...")
    try:
        response = requests.get(f"{BASE_URL}/api/detection/status", timeout=10)
        status = response.json()
        print(f"✓ Status: Processing={status['is_processing']}, Frames={status['frame_count']}")
    except Exception as e:
        print(f"✗ Status check failed: {e}")
    
    # Wait for some processing
    print("\n[TEST 4] Waiting for violations to be detected (60 seconds max)...")
    for i in range(60):
        time.sleep(1)
        try:
            response = requests.get(f"{BASE_URL}/api/detection/status", timeout=10)
            status = response.json()
            frame_count = status['frame_count']
            if i % 10 == 0:
                print(f"  Progress: {frame_count} frames processed...")
            
            if not status['is_processing']:
                print(f"  Processing complete at frame {frame_count}")
                break
        except:
            pass
    
    # Test 4: Get lane violations
    print("\n[TEST 5] Fetching lane violations (/api/violations/lane)...")
    try:
        response = requests.get(f"{BASE_URL}/api/violations/lane", timeout=10)
        violations = response.json()
        
        if violations['success']:
            print(f"✓ Found {violations['total_count']} lane violations")
            
            # Group by type
            by_type = {}
            for v in violations['violations']:
                vtype = v['type']
                by_type[vtype] = by_type.get(vtype, 0) + 1
            
            print("\n  Violations by type:")
            for vtype, count in by_type.items():
                print(f"    - {vtype}: {count}")
            
            # Show sample violations
            if violations['violations']:
                print(f"\n  Sample violations (first 3):")
                for v in violations['violations'][:3]:
                    print(f"    Track {v['track_id']}: {v['type']} - {v['description']}")
        else:
            print(f"✗ Error: {violations.get('error')}")
    except Exception as e:
        print(f"✗ Failed to fetch lane violations: {e}")
    
    # Test 5: Get violation summary
    print("\n[TEST 6] Fetching violation summary (/api/violations/summary)...")
    try:
        response = requests.get(f"{BASE_URL}/api/violations/summary", timeout=10)
        summary = response.json()
        
        if summary['success']:
            print(f"✓ Violation Summary:")
            print(f"  Total violations: {summary['summary']['total_violations']}")
            print(f"  Speed violations: {summary['summary']['speed_violations']}")
            print(f"  Lane violations: {summary['summary']['lane_violations']}")
            print(f"  Vehicles with violations: {summary['summary']['vehicles_with_violations']}")
            
            # Breakdown by type
            if summary['violation_breakdown']['lane']:
                print(f"\n  Lane violation breakdown:")
                for item in summary['violation_breakdown']['lane']:
                    print(f"    - {item['type']}: {item['count']}")
        else:
            print(f"✗ Error: {summary.get('error')}")
    except Exception as e:
        print(f"✗ Failed to fetch summary: {e}")
    
    # Test 6: Get vehicle-specific violations
    print("\n[TEST 7] Fetching vehicle-specific violations (/api/violations/vehicle/<id>)...")
    try:
        response = requests.get(f"{BASE_URL}/api/violations/vehicle/1", timeout=10)
        vehicle = response.json()
        
        if vehicle['success']:
            print(f"✓ Vehicle Track 1:")
            print(f"  Plate: {vehicle['vehicle']['plate']}")
            print(f"  Speed: {vehicle['vehicle']['speed']}")
            print(f"  Total violations: {vehicle['vehicle']['total_violations']}")
            print(f"  Lane violations: {len(vehicle['vehicle']['lane_violations'])}")
            
            if vehicle['vehicle']['lane_violations']:
                print(f"\n  Lane violations for Track 1:")
                for v in vehicle['vehicle']['lane_violations'][:3]:
                    print(f"    - {v['type']} (severity {v['severity']}): {v['description']}")
        else:
            print(f"ⓘ Info: {vehicle.get('error')}")
    except Exception as e:
        print(f"ⓘ Vehicle query (expected if Track 1 not found): {e}")
    
    # Test 7: Get detection stats
    print("\n[TEST 8] Fetching detection statistics (/api/detection/stats)...")
    try:
        response = requests.get(f"{BASE_URL}/api/detection/stats", timeout=10)
        result = response.json()
        
        if result['success']:
            stats = result['stats']
            print(f"✓ Detection Statistics:")
            print(f"  Total vehicles tracked: {stats['total_vehicles_tracked']}")
            print(f"  Speed violations: {stats['speeding_violations']}")
            print(f"  Lane violations: {stats['lane_violations']}")
            print(f"  Total violations: {stats['total_violations']}")
            print(f"  Frames processed: {stats['frame_count']}")
        else:
            print(f"✗ Error: {result.get('error')}")
    except Exception as e:
        print(f"✗ Failed to fetch stats: {e}")
    
    # Test 8: Stop detection
    print("\n[TEST 9] Stopping detection...")
    try:
        response = requests.post(f"{BASE_URL}/api/detection/stop", timeout=10)
        result = response.json()
        print(f"✓ Detection stopped: {result['message']}")
        print(f"  Total frames: {result['frames_processed']}")
    except Exception as e:
        print(f"✗ Failed to stop detection: {e}")
    
    print("\n" + "="*80)
    print("ENDPOINT TESTING COMPLETE")
    print("="*80 + "\n")
    return True

if __name__ == "__main__":
    try:
        test_backend()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
