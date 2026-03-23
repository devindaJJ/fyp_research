#!/usr/bin/env python
"""
Quick test of lane violation module - processes just 30 frames
"""
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(__file__))

from test_lane_violations import LaneViolationDemo

def main():
    video_path = r'c:\Users\hp\Documents\fyp_research\videos\lane 1.mp4'
    anpr_model = r'c:\Users\hp\Documents\fyp_research\models\number_plate_yolo.pt'
    
    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return
    
    print("[INFO] Starting quick test (30 frames)...")
    demo = LaneViolationDemo(video_path, speed_limit=60.0, anpr_model=anpr_model)
    
    # Process just 30 frames to test
    demo.process_video(skip_frames=1, max_frames=30, display=False)

if __name__ == '__main__':
    main()
