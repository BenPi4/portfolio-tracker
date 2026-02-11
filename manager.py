import gspread
from google.oauth2.service_account import Credentials

class PortfolioManager:
    def __init__(self, creds_input):
        """
        Initialize the Portfolio Manager.
        
        Args:
            creds_input: Can be either:
                         1. A string path to a local JSON file (e.g., 'credentials.json').
                         2. A dictionary object (e.g., st.secrets from Streamlit Cloud).
        """
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # --- Authentication Logic ---
        if isinstance(creds_input, dict):
            # Case A: We are running on Streamlit Cloud (using secrets dictionary)
            print("DEBUG: Authenticating via Dictionary (Secrets)...")
            
            # Fix for private_key newline characters often messed up in TOML/Secrets
            if 'private_key' in creds_input:
                creds_input['private_key'] = creds_input['private_key'].replace('\\n', '\n')
            
            creds = Credentials.from_service_account_info(creds_input, scopes=scopes)
            
        else:
            # Case B: We are running locally (using a file path string)
            print(f"DEBUG: Authenticating via File: {creds_input}")
            creds = Credentials.from_service_account_file(creds_input, scopes=scopes)
            
        self.client = gspread.authorize(creds)
        
        # --- CONFIGURATION: PASTE YOUR SHEET IDs HERE ---
        # 1. The ID of the empty Users_DB sheet
        self.USERS_DB_ID = '1fsmzv2pcxJmVZ8DT5KMC1TM936rmoBLOdJ5umvizaFo' 
        
        # 2. The ID of the clean Portfolio_Template sheet
        self.TEMPLATE_ID = '1fsmzv2pcxJmVZ8DT5KMC1TM936rmoBLOdJ5umvizaFo'

    def sign_up(self, username, password, user_email=None):
        """
        Creates a new user, duplicates the template sheet for them,
        and saves their credentials in the Users DB.
        """
        try:
            db_sheet = self.client.open_by_key(self.USERS_DB_ID).sheet1
            
            # 1. Check if user already exists
            existing_users = db_sheet.col_values(1) # Assuming Column A is Username
            if username in existing_users:
                return False, "Error: Username already taken. Please try another one."

            print(f"Creating new environment for user: {username}...")

            # 2. Duplicate the Template Sheet
            new_sheet = self.client.copy(self.TEMPLATE_ID, title=f"Portfolio_{username}")
            
            # Optional: Share the new sheet with the user's real email address
            if user_email:
                print(f"Sharing sheet with {user_email}...")
                new_sheet.share(user_email, perm_type='user', role='writer')
            
            # 3. Save the new user record in the Database
            # Format: [Username, Password, Sheet_ID]
            db_sheet.append_row([username, password, new_sheet.id])
            
            return True, f"Success! User created."
            
        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    def login(self, username, password):
        """
        Verifies credentials and returns the user's personal sheet object.
        """
        try:
            db_sheet = self.client.open_by_key(self.USERS_DB_ID).sheet1
            
            # Fetch all records to search for the user
            all_records = db_sheet.get_all_records() 
            
            for record in all_records:
                # Convert to string to ensure safe comparison
                if str(record['Username']) == str(username) and str(record['Password']) == str(password):
                    # Found match! Open and return their personal sheet
                    personal_sheet = self.client.open_by_key(record['Sheet_ID'])
                    return True, personal_sheet
            
            return False, None
            
        except Exception as e:
            print(f"Login error: {e}")
            return False, None
