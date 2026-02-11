import gspread
from google.oauth2.service_account import Credentials

class PortfolioManager:
    def __init__(self, creds_input):
        """
        Initialize the Portfolio Manager.
        """
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        if isinstance(creds_input, dict):
            if 'private_key' in creds_input:
                creds_input['private_key'] = creds_input['private_key'].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_input, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file(creds_input, scopes=scopes)
            
        self.client = gspread.authorize(creds)
        
        # --- CONFIGURATION ---
        self.USERS_DB_ID = '1NwDxpF_NaeZxWLS2VvSnJYmwj_ztN2ym4l3V0ZiYce4' 
        self.MASTER_FILE_ID = '1fsmzv2pcxJmVZ8DT5KMC1TM936rmoBLOdJ5umvizaFo' 

    def sign_up(self, username, password, user_email=""):
        """
        Registers a new user by creating a new TAB inside the Master File.
        """
        try:
            # 1. Access the Users Database
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            db_sheet = None
            for worksheet in db_spreadsheet.worksheets():
                if str(worksheet.id) == '1266209882':
                    db_sheet = worksheet
                    break
            
            if db_sheet is None:
                db_sheet = db_spreadsheet.get_worksheet(0)

            # 2. Check if user already exists
            existing_users = db_sheet.col_values(1)
            if username in existing_users:
                return False, "Error: Username already taken."

            # 3. Create a new Worksheet (Tab) for the user in the Master File
            # This avoids the '403 storage quota' error because the file belongs to YOU.
            master_file = self.client.open_by_key(self.MASTER_FILE_ID)
            
            # Create a new tab for the user. 
            # rows/cols can be adjusted based on your template needs
            new_user_tab = master_file.add_worksheet(title=f"User_{username}", rows="100", cols="20")
            
            # 4. Append row to DB: [Username, Password, Tab_Name, Email]
            # Note: We store the Tab Name instead of a separate File ID
            db_sheet.append_row([username, password, f"User_{username}", user_email])
            return True, "Success! User created."
            
        except Exception as e:
            return False, f"Error during signup: {str(e)}"

    def login(self, username, password):
        """
        Authenticates user and returns their specific tab from the Master File.
        """
        try:
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            db_sheet = None
            for worksheet in db_spreadsheet.worksheets():
                if str(worksheet.id) == '1266209882':
                    db_sheet = worksheet
                    break
            
            if db_sheet is None:
                db_sheet = db_spreadsheet.get_worksheet(0)

            all_records = db_sheet.get_all_records() 
            
            for record in all_records:
                if str(record.get('Username')) == str(username) and str(record.get('Password')) == str(password):
                    # Open the specific tab in the Master File
                    master_file = self.client.open_by_key(self.MASTER_FILE_ID)
                    personal_tab = master_file.worksheet(record.get('Sheet_ID'))
                    return True, personal_tab
            
            return False, None
        except Exception as e:
            print(f"Login error: {e}")
            return False, None