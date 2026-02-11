import gspread
from google.oauth2.service_account import Credentials

class PortfolioManager:
    def __init__(self, creds_input):
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        if isinstance(creds_input, dict):
            if 'private_key' in creds_input:
                creds_input['private_key'] = creds_input['private_key'].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_input, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file(creds_input, scopes=scopes)
            
        self.client = gspread.authorize(creds)
        
        # --- Update these with the correct IDs from your browser URL ---
        self.USERS_DB_ID = '1NwDxpF_NaeZxWLS2VvSnJYmwj_ztN2ym4l3V0ZiYce4' 
        self.TEMPLATE_ID = '1uvtDM1h6knCAZssERAxMp7bqK2-lqoe_1gna9O9iJBU'

    def sign_up(self, username, password, user_email=None):
        try:
            # 1. Open the Users_DB and specifically the sheet named 'sheet1'
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            db_sheet = db_spreadsheet.worksheet('sheet1') # Matches your description
            
            # 2. Check if user exists
            existing_users = db_sheet.col_values(1)
            if username in existing_users:
                return False, "Error: Username already taken."

            # 3. Copy the Template file (the one with 'Transactions')
            new_sheet = self.client.copy(self.TEMPLATE_ID, title=f"Portfolio_{username}")
            
            if user_email:
                new_sheet.share(user_email, perm_type='user', role='writer')
            
            # 4. Save to DB: [Username, Password, New_Sheet_ID]
            db_sheet.append_row([username, password, new_sheet.id])
            return True, "Success! User created."
            
        except Exception as e:
            # This will help us see if it's a 404 or something else
            return False, f"Error: {str(e)}"

    def login(self, username, password):
        try:
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            db_sheet = db_spreadsheet.worksheet('sheet1')
            all_records = db_sheet.get_all_records() 
            
            for record in all_records:
                # Make sure the column names in 'sheet1' are exactly 'Username' and 'Password'
                if str(record.get('Username')) == str(username) and str(record.get('Password')) == str(password):
                    personal_sheet = self.client.open_by_key(record.get('Sheet_ID'))
                    return True, personal_sheet
            
            return False, None
        except Exception as e:
            print(f"Login error: {e}")
            return False, None
