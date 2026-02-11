import gspread
from manager import PortfolioManager

try:
    mgr = PortfolioManager('credentials.json')
    
    print("Connecting to Google Drive API...")
    # התיקון: קריאה ישירה דרך ה-client שמותקן ב-Manager
    response = mgr.client.request('delete', 'https://www.googleapis.com/drive/v3/files/trash')
    
    if response.status_code == 204:
        print("✅ Success! The bot's trash has been permanently emptied.")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")
        
except Exception as e:
    print(f"❌ Failed to empty trash: {e}")