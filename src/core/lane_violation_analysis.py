"""
Lane violation visualization and analysis utilities.
Provides comprehensive reporting and visualization for lane violation data.
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict


class LaneViolationVisualizer:
    """Visualizes lane violations on video frames."""
    
    # Color schemes
    COLORS = {
        'normal': (0, 255, 0),           # Green
        'lane_violation': (0, 165, 255), # Orange
        'speed_violation': (255, 0, 0),  # Red
        'critical': (0, 0, 255),         # Red (bright)
        'warning': (0, 255, 255)         # Yellow
    }
    
    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        """Initialize visualizer."""
        self.frame_width = frame_width
        self.frame_height = frame_height
    
    def draw_lanes(self, frame: np.ndarray, lanes: List) -> np.ndarray:
        """
        Draw detected lanes on frame.
        
        Args:
            frame: Input frame
            lanes: List of LaneInfo objects
            
        Returns:
            Frame with drawn lanes
        """
        if not lanes:
            return frame
        
        for lane in lanes:
            # Draw lane center line
            x = int(lane.center_x)
            cv2.line(frame, (x, 0), (x, self.frame_height),
                    self.COLORS['normal'], 2)
            
            # Draw lane boundaries
            left_x = int(lane.center_x - lane.width / 2)
            right_x = int(lane.center_x + lane.width / 2)
            
            cv2.line(frame, (left_x, 0), (left_x, self.frame_height),
                    self.COLORS['normal'], 1)
            cv2.line(frame, (right_x, 0), (right_x, self.frame_height),
                    self.COLORS['normal'], 1)
            
            # Lane ID label
            cv2.putText(frame, f"Lane {lane.lane_id}", (x - 20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLORS['normal'], 1)
        
        return frame
    
    def draw_vehicle_with_violation(self, frame: np.ndarray, track_id: int,
                                    bbox: Tuple[int, int, int, int],
                                    speed: Optional[float] = None,
                                    plate: Optional[str] = None,
                                    violations: Optional[List[Dict]] = None) -> np.ndarray:
        """
        Draw vehicle with violation information.
        
        Args:
            frame: Input frame
            track_id: Vehicle track ID
            bbox: Bounding box (x1, y1, x2, y2)
            speed: Vehicle speed
            plate: License plate text
            violations: List of violations
            
        Returns:
            Annotated frame
        """
        x1, y1, x2, y2 = bbox
        
        # Determine color based on violations
        color = self.COLORS['normal']
        if violations:
            if any(v['type'] in ['ILLEGAL_LANE_CHANGE', 'LANE_CROSSING'] for v in violations):
                color = self.COLORS['lane_violation']
            if any(v['type'] == 'SPEEDING' for v in violations):
                color = self.COLORS['critical']
            if any(v['type'] in ['EXCESSIVE_LANE_CHANGES'] for v in violations):
                color = self.COLORS['critical']
        
        # Draw bounding box
        thickness = 3 if violations else 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        
        # Draw background for text
        label_parts = [f"ID:{track_id}"]
        if speed is not None:
            label_parts.append(f"Speed:{speed:.1f}km/h")
        if plate:
            label_parts.append(f"Plate:{plate}")
        
        label = " | ".join(label_parts)
        
        # Text background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness_text = 1
        (text_width, text_height), baseline = cv2.getTextSize(
            label, font, font_scale, thickness_text
        )
        
        cv2.rectangle(frame, (x1, y1 - text_height - 10),
                     (x1 + text_width, y1), color, -1)
        
        # Draw text
        cv2.putText(frame, label, (x1, y1 - 5),
                   font, font_scale, (255, 255, 255), thickness_text)
        
        # Draw violations
        if violations:
            violation_text = ", ".join([v['type'] for v in violations])
            cv2.putText(frame, f"VIOLATIONS: {violation_text}", (x1, y2 + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLORS['critical'], 2)
        
        return frame
    
    def draw_statistics_panel(self, frame: np.ndarray, stats: Dict) -> np.ndarray:
        """
        Draw statistics panel on frame.
        
        Args:
            frame: Input frame
            stats: Statistics dictionary
            
        Returns:
            Frame with statistics
        """
        panel_height = 150
        panel = np.zeros((panel_height, self.frame_width, 3), dtype=np.uint8)
        panel[:] = (50, 50, 50)
        
        # Draw stats
        y_offset = 20
        line_height = 25
        
        stats_items = [
            f"Frame: {stats.get('frame', 0)}",
            f"Vehicles: {stats.get('vehicles', 0)}",
            f"Speed Violations: {stats.get('speed_violations', 0)}",
            f"Lane Violations: {stats.get('lane_violations', 0)}",
            f"Total Violations: {stats.get('total_violations', 0)}"
        ]
        
        for item in stats_items:
            cv2.putText(panel, item, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            y_offset += line_height
        
        # Paste panel on frame
        frame[0:panel_height, 0:self.frame_width] = panel
        
        return frame


class LaneViolationAnalyzer:
    """Analyzes lane violation patterns and statistics."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.violations_by_type = defaultdict(int)
        self.violations_by_vehicle = defaultdict(list)
        self.violations_timeline = []
        self.violation_severity_count = defaultdict(int)
    
    def analyze_violations(self, violations: List[Dict]) -> Dict:
        """
        Analyze violation data and generate statistics.
        
        Args:
            violations: List of violation dictionaries
            
        Returns:
            Analysis results
        """
        self.violations_timeline = violations
        
        # Count by type
        for v in violations:
            v_type = v.get('type', 'UNKNOWN')
            self.violations_by_type[v_type] += 1
            
            track_id = v.get('track_id', 'UNKNOWN')
            self.violations_by_vehicle[track_id].append(v)
            
            severity = v.get('severity', 'UNKNOWN')
            self.violation_severity_count[severity] += 1
        
        return {
            'total_violations': len(violations),
            'by_type': dict(self.violations_by_type),
            'by_severity': dict(self.violation_severity_count),
            'vehicles_with_violations': len(self.violations_by_vehicle),
            'violations_per_vehicle': {
                k: len(v) for k, v in self.violations_by_vehicle.items()
            }
        }
    
    def get_violation_summary(self) -> str:
        """
        Generate text summary of violations.
        
        Returns:
            Formatted summary string
        """
        summary = "="*80 + "\n"
        summary += "LANE VIOLATION ANALYSIS SUMMARY\n"
        summary += "="*80 + "\n\n"
        
        # By type
        summary += "Violations by Type:\n"
        for v_type, count in sorted(self.violations_by_type.items()):
            summary += f"  {v_type}: {count}\n"
        
        # By severity
        summary += "\nViolations by Severity:\n"
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = self.violation_severity_count.get(severity, 0)
            if count > 0:
                summary += f"  {severity}: {count}\n"
        
        # By vehicle
        summary += "\nViolations by Vehicle:\n"
        for track_id, violations in sorted(self.violations_by_vehicle.items()):
            summary += f"  Vehicle {track_id}: {len(violations)} violations\n"
            for v in violations:
                summary += f"    - {v.get('type', 'UNKNOWN')}: {v.get('description', '')}\n"
        
        summary += "="*80 + "\n"
        
        return summary
    
    def export_to_csv(self, filepath: str):
        """
        Export violations to CSV file.
        
        Args:
            filepath: Path to save CSV
        """
        import csv
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Timestamp', 'Vehicle_ID', 'Violation_Type', 'Severity',
                'Description', 'Speed', 'Lane', 'Details'
            ])
            
            # Data
            for v in self.violations_timeline:
                writer.writerow([
                    v.get('timestamp', '').isoformat() if hasattr(v.get('timestamp'), 'isoformat') else str(v.get('timestamp', '')),
                    v.get('track_id', ''),
                    v.get('type', ''),
                    v.get('severity', ''),
                    v.get('description', ''),
                    v.get('speed', ''),
                    v.get('current_lane_id', ''),
                    str(v)
                ])
    
    def export_to_json(self, filepath: str):
        """
        Export violations to JSON file.
        
        Args:
            filepath: Path to save JSON
        """
        import json
        
        # Convert violations to JSON-serializable format
        violations_json = []
        for v in self.violations_timeline:
            v_json = dict(v)
            if hasattr(v_json.get('timestamp'), 'isoformat'):
                v_json['timestamp'] = v_json['timestamp'].isoformat()
            violations_json.append(v_json)
        
        with open(filepath, 'w') as f:
            json.dump({
                'violations': violations_json,
                'summary': {
                    'by_type': dict(self.violations_by_type),
                    'by_severity': dict(self.violation_severity_count),
                    'total': len(violations_json)
                }
            }, f, indent=2)


class LaneViolationReporter:
    """Generates comprehensive violation reports."""
    
    def __init__(self, analyzer: LaneViolationAnalyzer):
        """
        Initialize reporter.
        
        Args:
            analyzer: LaneViolationAnalyzer instance
        """
        self.analyzer = analyzer
    
    def generate_report(self, output_path: str, format: str = 'html'):
        """
        Generate comprehensive report.
        
        Args:
            output_path: Path to save report
            format: Report format ('html', 'csv', 'json', or 'txt')
        """
        if format == 'html':
            self._generate_html_report(output_path)
        elif format == 'csv':
            self.analyzer.export_to_csv(output_path)
        elif format == 'json':
            self.analyzer.export_to_json(output_path)
        elif format == 'txt':
            self._generate_txt_report(output_path)
    
    def _generate_html_report(self, output_path: str):
        """Generate HTML report."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Lane Violation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; }
        .critical { background-color: #ffcccc; }
        .high { background-color: #ffe6cc; }
        .medium { background-color: #ffffcc; }
        .chart { margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Lane Violation Detection Report</h1>
    <p>Generated: {timestamp}</p>
    
    <h2>Summary Statistics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Total Violations</td>
            <td>{total_violations}</td>
        </tr>
        <tr>
            <td>Vehicles Involved</td>
            <td>{vehicles_involved}</td>
        </tr>
        <tr>
            <td>Critical Violations</td>
            <td>{critical_count}</td>
        </tr>
        <tr>
            <td>High Severity Violations</td>
            <td>{high_count}</td>
        </tr>
    </table>
    
    <h2>Violations by Type</h2>
    <table>
        <tr>
            <th>Type</th>
            <th>Count</th>
        </tr>
        {type_rows}
    </table>
    
    <h2>All Violations</h2>
    <table>
        <tr>
            <th>Vehicle ID</th>
            <th>Type</th>
            <th>Severity</th>
            <th>Description</th>
        </tr>
        {violation_rows}
    </table>
</body>
</html>
        """
        
        # Fill in data
        analysis = self.analyzer.analyze_violations(self.analyzer.violations_timeline)
        
        type_rows = ""
        for v_type, count in self.analyzer.violations_by_type.items():
            type_rows += f"<tr><td>{v_type}</td><td>{count}</td></tr>"
        
        violation_rows = ""
        for v in self.analyzer.violations_timeline:
            severity_class = v.get('severity', 'UNKNOWN').lower()
            violation_rows += f"""
            <tr class="{severity_class}">
                <td>{v.get('track_id', '')}</td>
                <td>{v.get('type', '')}</td>
                <td>{v.get('severity', '')}</td>
                <td>{v.get('description', '')}</td>
            </tr>
            """
        
        html = html.format(
            timestamp=datetime.now().isoformat(),
            total_violations=len(self.analyzer.violations_timeline),
            vehicles_involved=len(self.analyzer.violations_by_vehicle),
            critical_count=self.analyzer.violation_severity_count.get('CRITICAL', 0),
            high_count=self.analyzer.violation_severity_count.get('HIGH', 0),
            type_rows=type_rows,
            violation_rows=violation_rows
        )
        
        with open(output_path, 'w') as f:
            f.write(html)
    
    def _generate_txt_report(self, output_path: str):
        """Generate text report."""
        with open(output_path, 'w') as f:
            f.write(self.analyzer.get_violation_summary())
