import os
import os
import gspread
import pandas as pd
import datetime
import time
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
from dotenv import load_dotenv

load_dotenv()

class GoogleSheetsHandler:
    def __init__(self):
        self.setup_google_sheets()
    
    def setup_google_sheets(self):
        # Google Sheets API setup
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Download service account JSON from Google Cloud Console
        creds = Credentials.from_service_account_file(
            os.getenv("SERVICE_ACCOUNT_CREDS"), scopes=scope
        )
        
        self.client = gspread.authorize(creds)
        
        # Open your Google Sheet
        self.sheet = self.client.open_by_key(os.getenv("SHEET_ID")).sheet1
    
    def get_parking_data(self):
        """Get all parking data from Google Sheets"""
        try:
            # Get all records
            records = self.sheet.get_all_records()
            
            # Process data
            processed_data = []
            for record in records:
                if record.get('Timestamp') and record.get('Distance'):
                    processed_data.append({
                        'timestamp': record['Timestamp'],
                        'distance': int(record['Distance']),
                        'status': record['Status'],
                        'location': record.get('Location', 'Unknown'),
                        'spot_id': record.get('SpotID', 'A1')
                    })
            
            return processed_data[-50:]  # Return last 50 records
        
        except Exception as e:
            print(f"Error reading Google Sheets: {e}")
            return []
    
    def get_violations_since(self, since_time):
        """Get violations since specified time"""
        try:
            records = self.sheet.get_all_records()
            violations = []
            
            for record in records:
                if (record.get('Status') == 'OCCUPIED' and 
                    record.get('Distance', 100) < 10):  # Too close = violation
                    
                    # Parse timestamp (adjust format as needed)
                    record_time = datetime.strptime(
                        record['Timestamp'], '%Y-%m-%d %H:%M:%S'
                    )
                    
                    if record_time >= since_time:
                        violations.append({
                            'timestamp': record['Timestamp'],
                            'location': record.get('Location', 'Unknown'),
                            'distance': record['Distance'],
                            'spot_id': record.get('SpotID', 'A1'),
                            'priority': 'HIGH' if record['Distance'] < 5 else 'MEDIUM'
                        })
            
            return violations
        
        except Exception as e:
            print(f"Error getting violations: {e}")
            return []
    
    def get_system_statistics(self):
        """Calculate system statistics"""
        try:
            records = self.sheet.get_all_records()
            if not records:
                return {}
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(records)
            
            # Calculate statistics
            total_records = len(df)
            available_spots = len(df[df['Status'] == 'AVAILABLE'])
            occupied_spots = len(df[df['Status'] == 'OCCUPIED'])
            violation_count = len(df[(df['Status'] == 'OCCUPIED') & (df['Distance'].astype(float) < 10)])
            
            return {
                'total_records': total_records,
                'available_spots': available_spots,
                'occupied_spots': occupied_spots,
                'violation_count': violation_count,
                'utilization_rate': round((occupied_spots / total_records) * 100, 2) if total_records > 0 else 0
            }
        
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}
    
    def get_device_health(self):
        """Get device health status (mock data - extend based on your actual data)"""
        # This would typically come from a separate sheet or database
        return [
            {
                'device_id': 'SN-001',
                'location': 'Main Gate A1',
                'status': 'online',
                'battery': 85,
                'last_update': datetime.now().isoformat()
            },
            {
                'device_id': 'SN-002', 
                'location': 'Street B2',
                'status': 'offline',
                'battery': 15,
                'last_update': (datetime.now() - timedelta(hours=3)).isoformat()
            }
        ]