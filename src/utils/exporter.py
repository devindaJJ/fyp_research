"""
Export utilities for vehicle tracking and ANPR results.
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class ResultExporter:
    """
    Export integrated vehicle tracking and ANPR results to various formats.
    """
    
    def __init__(self, output_dir: str = "data/exports"):
        """
        Initialize the exporter.
        
        Args:
            output_dir: Directory to save exported files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_csv(self, vehicle_data: Dict[int, Dict], filename: str = None) -> str:
        """
        Export vehicle data to CSV file.
        
        Args:
            vehicle_data: Dictionary of vehicle data from integrator
            filename: Output filename (default: timestamped)
            
        Returns:
            Path to the exported CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vehicle_tracking_{timestamp}.csv"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = ['track_id', 'speed_kmh', 'number_plate', 'violation', 'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for track_id, data in sorted(vehicle_data.items()):
                bbox = data.get('bbox', (None, None, None, None))
                writer.writerow({
                    'track_id': track_id,
                    'speed_kmh': f"{data['speed']:.1f}" if data['speed'] is not None else 'N/A',
                    'number_plate': data['plate'] if data['plate'] else 'N/A',
                    'violation': 'YES' if data['violation'] else 'NO',
                    'bbox_x1': bbox[0] if bbox[0] is not None else 'N/A',
                    'bbox_y1': bbox[1] if bbox[1] is not None else 'N/A',
                    'bbox_x2': bbox[2] if bbox[2] is not None else 'N/A',
                    'bbox_y2': bbox[3] if bbox[3] is not None else 'N/A'
                })
        
        return str(output_path)
    
    def export_to_json(self, vehicle_data: Dict[int, Dict], filename: str = None) -> str:
        """
        Export vehicle data to JSON file.
        
        Args:
            vehicle_data: Dictionary of vehicle data from integrator
            filename: Output filename (default: timestamped)
            
        Returns:
            Path to the exported JSON file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vehicle_tracking_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        # Convert to JSON-serializable format
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'vehicles': {}
        }
        
        for track_id, data in vehicle_data.items():
            export_data['vehicles'][str(track_id)] = {
                'track_id': track_id,
                'speed_kmh': data['speed'],
                'number_plate': data['plate'],
                'violation': data['violation'],
                'bbox': data['bbox']
            }
        
        with open(output_path, 'w') as jsonfile:
            json.dump(export_data, jsonfile, indent=2)
        
        return str(output_path)
    
    def export_violations_only(self, vehicle_data: Dict[int, Dict], filename: str = None) -> str:
        """
        Export only vehicles with violations to CSV.
        
        Args:
            vehicle_data: Dictionary of vehicle data from integrator
            filename: Output filename (default: timestamped)
            
        Returns:
            Path to the exported CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"violations_{timestamp}.csv"
        
        output_path = self.output_dir / filename
        
        violations = {k: v for k, v in vehicle_data.items() if v['violation']}
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = ['track_id', 'speed_kmh', 'number_plate', 'speed_limit_exceeded']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for track_id, data in sorted(violations.items()):
                writer.writerow({
                    'track_id': track_id,
                    'speed_kmh': f"{data['speed']:.1f}" if data['speed'] is not None else 'N/A',
                    'number_plate': data['plate'] if data['plate'] else 'UNKNOWN',
                    'speed_limit_exceeded': f"{data['speed'] - 60:.1f}" if data['speed'] else 'N/A'  # Assuming 60 km/h limit
                })
        
        return str(output_path)
    
    def print_summary_report(self, vehicle_data: Dict[int, Dict]):
        """
        Print a detailed summary report of all tracked vehicles.
        
        Args:
            vehicle_data: Dictionary of vehicle data from integrator
        """
        total_vehicles = len(vehicle_data)
        vehicles_with_speed = sum(1 for v in vehicle_data.values() if v['speed'] is not None)
        vehicles_with_plate = sum(1 for v in vehicle_data.values() if v['plate'] is not None)
        violations = sum(1 for v in vehicle_data.values() if v['violation'])
        
        print("\n" + "="*80)
        print("VEHICLE TRACKING SUMMARY REPORT")
        print("="*80)
        print(f"Total Vehicles Tracked: {total_vehicles}")
        print(f"Vehicles with Speed Data: {vehicles_with_speed}")
        print(f"Vehicles with Plate Data: {vehicles_with_plate}")
        print(f"Vehicles with Violations: {violations}")
        print("="*80)
        
        if violations > 0:
            print("\nVIOLATIONS DETAILS:")
            print("-"*80)
            print(f"{'Track ID':<10} {'Speed (km/h)':<15} {'Number Plate':<20} {'Exceeded By':<15}")
            print("-"*80)
            
            for track_id, data in sorted(vehicle_data.items()):
                if data['violation']:
                    speed_str = f"{data['speed']:.1f}" if data['speed'] is not None else "N/A"
                    plate_str = data['plate'] if data['plate'] else "UNKNOWN"
                    exceeded = f"{data['speed'] - 60:.1f}" if data['speed'] else "N/A"
                    print(f"{track_id:<10} {speed_str:<15} {plate_str:<20} {exceeded:<15}")
            
            print("="*80)
