import gspread
from google.oauth2.service_account import Credentials

class PortfolioManager:
    def __init__(self, creds_input):
        """
        Initialize the Portfolio Manager.
        Handles authentication via local JSON or Streamlit Secrets.
        """
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        if isinstance(creds_input, dict):
            if 'private_key' in creds_input:
                creds_input['private_key'] = creds_input['private_key'].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_input, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file(creds_input, scopes=scopes)
            
        self.client = gspread.authorize(creds)
        
        # --- CONFIGURATION: SET YOUR IDs HERE ---
        self.USERS_DB_ID = '1NwDxpF_NaeZxWLS2VvSnJYmwj_ztN2ym4l3V0ZiYce4' 
        self.TEMPLATE_ID = '1uvtDM1h6knCAZssERAxMp7bqK2-lqoe_1gna9O9iJBU'

   def sign_up(self, username, password, user_email=""):
        try:
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            
            # --- FIX: Access sheet by GID instead of Name ---
            # Your URL ends with gid=1266209882
            db_sheet = None
            for worksheet in db_spreadsheet.worksheets():
                if str(worksheet.id) == '1266209882':
                    db_sheet = worksheet
                    break
            
            if db_sheet is None:
                # Fallback to the very first sheet if GID is not found
                db_sheet = db_spreadsheet.get_worksheet(0)

            # 1. Check if username already exists
            existing_users = db_sheet.col_values(1)
            if username in existing_users:
                return False, "Error: Username already taken."

            # 2. Duplicate the Template file
            new_sheet = self.client.copy(self.TEMPLATE_ID, title=f"Portfolio_{username}")
            
            # 3. Share with user
            if user_email and "@" in user_email:
                new_sheet.share(user_email, perm_type='user', role='writer')
            
            # 4. Append row to DB
            db_sheet.append_row([username, password, new_sheet.id, user_email])
            return True, "Success! User created."
            
        except Exception as e:
            return False, f"Error during signup: {str(e)}"


    def login(self, username, password):
        """
        Authenticates user and returns their private portfolio sheet.
        """
        try:
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            db_sheet = db_spreadsheet.worksheet('sheet1')
            all_records = db_sheet.get_all_records() 
            
            for record in all_records:
                # Matches keys in 'sheet1' header row (Username, Password)
                if str(record.get('Username')) == str(username) and str(record.get('Password')) == str(password):
                    personal_sheet = self.client.open_by_key(record.get('Sheet_ID'))
                    return True, personal_sheet
            
            return False, None
        except Exception as e:
            print(f"Login error: {e}")
            return False, None
