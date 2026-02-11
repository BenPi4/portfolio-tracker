from manager import PortfolioManager
mgr = PortfolioManager('credentials.json')
try:
    print("Trying to open Users DB...")
    sheet = mgr.client.open_by_key(mgr.USERS_DB_ID)
    print(f"Success! Opened: {sheet.title}")
    print("Trying to open Template...")
    temp = mgr.client.open_by_key(mgr.TEMPLATE_ID)
    print(f"Success! Opened: {temp.title}")
except Exception as e:
    print(f"Found the error: {e}")
