import gspread
from google.oauth2.service_account import Credentials

class PortfolioManager:
    def __init__(self, creds_input):
        """
        Initialize the Portfolio Manager.
        Supports both dictionary input (Streamlit Secrets) and file path (Local).
        """
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        if isinstance(creds_input, dict):
            # Handle newline characters in private key from environment variables
            if 'private_key' in creds_input:
                creds_input['private_key'] = creds_input['private_key'].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_input, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file(creds_input, scopes=scopes)
            
        self.client = gspread.authorize(creds)
        
        # --- CONFIGURATION: IDs ---
        self.USERS_DB_ID = '1NwDxpF_NaeZxWLS2VvSnJYmwj_ztN2ym4l3V0ZiYce4' 
        self.TEMPLATE_ID = '1uvtDM1h6knCAZssERAxMp7bqK2-lqoe_1gna9O9iJBU'
        self.FOLDER_ID = '17RIu2ZRBOJD9i0PdZP_7Pr6JszbZE6hcIg_HaVI3K-c' 

    def sign_up(self, username, password, user_email=""):
        """
        Registers a new user:
        1. Checks if username exists in the Database.
        2. Clones the template into a specific folder to avoid quota limits.
        3. Shares the new file with the user's email.
        4. Logs the new user in the Database.
        """
        try:
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            
            # Target specific worksheet using GID 1266209882
            db_sheet = None
            for worksheet in db_spreadsheet.worksheets():
                if str(worksheet.id) == '1266209882':
                    db_sheet = worksheet
                    break
            
            if db_sheet is None:
                db_sheet = db_spreadsheet.get_worksheet(0)

            # 1. Check if username already exists in column 1
            existing_users = db_sheet.col_values(1)
            if username in existing_users:
                return False, "Error: Username already taken."

            # 2. Duplicate Template into the designated folder (avoids 403 quota error)
            new_sheet = self.client.copy(
                self.TEMPLATE_ID, 
                title=f"Portfolio_{username}",
                folder_id=self.FOLDER_ID
            )
            
            # 3. Grant 'Writer' access to the user if email is provided
            if user_email and "@" in user_email:
                new_sheet.share(user_email, perm_type='user', role='writer')
            
            # 4. Record new user data in DB: [Username, Password, Sheet_ID, Email]
            db_sheet.append_row([username, password, new_sheet.id, user_email])
            return True, "Success! User created."
            
        except Exception as e:
            return False, f"Error during signup: {str(e)}"

    def login(self, username, password):
        """
        Validates credentials and returns the user's specific Google Sheet object.
        """
        try:
            db_spreadsheet = self.client.open_by_key(self.USERS_DB_ID)
            
            # Access DB worksheet by GID
            db_sheet = None
            for worksheet in db_spreadsheet.worksheets():
                if str(worksheet.id) == '1266209882':
                    db_sheet = worksheet
                    break
            
            if db_sheet is None:
                db_sheet = db_spreadsheet.get_worksheet(0)

            # Fetch all rows as a list of dictionaries
            all_records = db_sheet.get_all_records() 
            
            for record in all_records:
                # Compare credentials
                if str(record.get('Username')) == str(username) and str(record.get('Password')) == str(password):
                    # Open the user's personal sheet using the stored ID
                    personal_sheet = self.client.open_by_key(record.get('Sheet_ID'))
                    return True, personal_sheet
            
            return False, None
        except Exception as e:
            print(f"Login error: {e}")
            return False, None
