import gspread
from google.oauth2.service_account import Credentials

class PortfolioManager:
    def __init__(self, creds_input):
        """
        Initialize the Portfolio Manager with Google Sheets API credentials.
        """
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        if isinstance(creds_input, dict):
            # Handle newline characters in private key from Streamlit Secrets
            if 'private_key' in creds_input:
                creds_input['private_key'] = creds_input['private_key'].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_input, scopes=scopes)
        else:
            # Handle local file credentials
            creds = Credentials.from_service_account_file(creds_input, scopes=scopes)
            
        self.client = gspread.authorize(creds)
        
        # --- CONFIGURATION ---
        self.USERS_DB_ID = '1NwDxpF_NaeZxWLS2VvSnJYmwj_ztN2ym4l3V0ZiYce4' 
        # The ID of your Master Portfolio Tracker file
        self.MASTER_FILE_ID = '1NwDxpF_NaeZxWLS2VvSnJYmwj_ztN2ym4l3V0ZiYce4' 

    def sign_up(self, username, password, user_email=""):
        """
        Registers a new user, creates their specific tabs, and cleans up the sheet.
        """
        try:
            # 1. Access the Users Database
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            
            # Find the specific worksheet in DB (GID 1266209882)
            db_sheet = None
            for worksheet in db_spreadsheet.worksheets():
                if str(worksheet.id) == '1266209882':
                    db_sheet = worksheet
                    break
            if db_sheet is None: db_sheet = db_spreadsheet.get_worksheet(0)

            # 2. Check if username already exists
            existing_users = db_sheet.col_values(1)
            if username in existing_users:
                return False, "Error: Username already taken."

            # --- 3. Create Transaction Tab ---
            master_file = self.client.open_by_key(self.MASTER_FILE_ID)
            
            # Create the tab
            new_user_tab = master_file.add_worksheet(title=f"User_{username}", rows="100", cols="5")
            
            # Add Headers immediately to prevent "Unique Header" error
            headers = ["Date", "Ticker", "Type", "Quantity", "Price"]
            new_user_tab.append_row(headers)
            
            # Clean up: Delete all columns from F onwards (resize to exactly 5 columns)
            new_user_tab.resize(rows=100, cols=5)

            # --- 4. Create Alerts Tab ---
            # This ensures every user has a place to store price alerts
            alerts_tab = master_file.add_worksheet(title=f"Alerts_{username}", rows="50", cols="4")
            alert_headers = ["Ticker", "Target", "Condition", "Active"]
            alerts_tab.append_row(alert_headers)

            # 5. Save user to Database
            # We store the Transaction Tab Name in the 'Sheet_ID' column
            db_sheet.append_row([username, password, f"User_{username}", user_email])
            
            return True, "Success! User created."
            
        except Exception as e:
            return False, f"Error during signup: {str(e)}"

    def login(self, username, password):
        """
        Authenticates user and returns both their Transaction Tab and Alerts Tab.
        """
        try:
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            db_sheet = None
            for worksheet in db_spreadsheet.worksheets():
                if str(worksheet.id) == '1266209882':
                    db_sheet = worksheet
                    break
            if db_sheet is None: db_sheet = db_spreadsheet.get_worksheet(0)

            all_records = db_sheet.get_all_records() 
            for record in all_records:
                if str(record.get('Username')) == str(username) and str(record.get('Password')) == str(password):
                    master_file = self.client.open_by_key(self.MASTER_FILE_ID)
                    
                    user_tab_name = record.get('Sheet_ID') 
                    
                    try:
                        # Get Transaction Tab
                        trans_tab = master_file.worksheet(user_tab_name)
                        
                        # Try to get Alerts Tab (derived from username)
                        alerts_tab_name = user_tab_name.replace("User_", "Alerts_")
                        try:
                            alerts_tab = master_file.worksheet(alerts_tab_name)
                        except:
                            # If user is old and doesn't have an alerts tab yet
                            alerts_tab = None 
                            
                        return True, trans_tab, alerts_tab
                    except:
                        return False, None, None
            
            return False, None, None
        except Exception as e:
            print(f"Login error: {e}")
            return False, None, None
