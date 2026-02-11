from manager import PortfolioManager
import gspread

try:
    mgr = PortfolioManager('credentials.json')
    
    print("1. Testing Users_DB connection...")
    db = mgr.client.open_by_key(mgr.USERS_DB_ID)
    print(f"   ✅ Found file: {db.title}")
    
    print("2. Testing 'sheet1' inside Users_DB...")
    try:
        ws = db.worksheet('sheet1')
        print("   ✅ Found worksheet 'sheet1'")
    except:
        print("   ❌ ERROR: Could not find 'sheet1'. Check your tab name!")

    print("3. Testing Template connection...")
    tmpl = mgr.client.open_by_key(mgr.TEMPLATE_ID)
    print(f"   ✅ Found file: {tmpl.title}")

except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")
