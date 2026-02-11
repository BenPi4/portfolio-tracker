from manager import PortfolioManager
import gspread
import os

def run_test():
    print("--- Starting Connection Test ---")
    
    # בדיקה אם הקובץ קיים
    if not os.path.exists('credentials.json'):
        print("❌ ERROR: 'credentials.json' is missing from the folder!")
        return

    try:
        # ניסיון התחברות
        mgr = PortfolioManager('credentials.json')
        
        print(f"1. Checking Users_DB (ID: {mgr.USERS_DB_ID})...")
        db = mgr.client.open_by_key(mgr.USERS_DB_ID)
        print(f"   ✅ Found file: {db.title}")
        
        print(f"2. Checking Template (ID: {mgr.TEMPLATE_ID})...")
        tmpl = mgr.client.open_by_key(mgr.TEMPLATE_ID)
        print(f"   ✅ Found file: {tmpl.title}")
        
        print("\n🏆 SUCCESS: Your bot is connected and has access to both files!")

    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        print("\nHint: Make sure the bot email is an 'Editor' on BOTH sheets.")

if __name__ == "__main__":
    run_test()