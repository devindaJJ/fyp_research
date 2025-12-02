import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Google Sheets Configuration
    GOOGLE_SHEETS_CREDENTIALS = 'credentials.json'
    SPREADSHEET_NAME = 'Parking System Data'
    
    # Flask Configuration
    DEBUG = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'traffic-management-secret-key')