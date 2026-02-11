import gspread
from google.oauth2.service_account import Credentials

class PortfolioManager:
    def __init__(self, creds_file):
        # Set up permissions and authentication
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
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
            # Assuming Column A contains usernames
            existing_users = db_sheet.col_values(1) 
            if username in existing_users:
                return False, "Error: Username already taken. Please try another one."

            print(f"Creating new environment for user: {username}...")

            # 2. Duplicate the Template Sheet
            # The .copy() method duplicates the file in Google Drive
            new_sheet = self.client.copy(self.TEMPLATE_ID, title=f"Portfolio_{username}")
            
            # Optional: Share the new sheet with the user's real email address
            if user_email:
                print(f"Sharing sheet with {user_email}...")
                new_sheet.share(user_email, perm_type='user', role='writer')
            
            # 3. Save the new user record in the Database
            # We store: Username, Password, and the ID of their new personal sheet
            # Appending to the next available row
            db_sheet.append_row([username, password, new_sheet.id])
            
            return True, f"Success! User created. New Sheet ID: {new_sheet.id}"
            
        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    def login(self, username, password):
        """
        Verifies credentials and returns the user's personal sheet object.
        """
        try:
            db_sheet = self.client.open_by_key(self.USERS_DB_ID).sheet1
            
            # Fetch all records to search for the user
            # Expecting headers: Username, Password, Sheet_ID
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

# --- Main Execution Example ---

if __name__ == "__main__":
    # 1. Initialize the system
    # Make sure 'credentials.json' is in the same folder
    manager = PortfolioManager('credentials.json')

    # Scenario 1: A new friend wants to sign up
    print("\n--- Sign Up Process ---")
    # You can change these details to test
    new_user = "TestUser_1"
    new_pass = "secret123"
    new_email = "example@gmail.com" # Put a real email here to test sharing
    
    success, msg = manager.sign_up(new_user, new_pass, new_email) 
    print(msg)

    # Scenario 2: User logs in to update their portfolio
    print("\n--- Login Process ---")
    is_logged_in, sheet_obj = manager.login(new_user, new_pass)

    if is_logged_in:
        print(f"Login Successful! Connected to sheet: '{sheet_obj.title}'")
        # Now you can work with 'sheet_obj' just like before
        # Example: sheet_obj.sheet1.update_cell(1, 1, 'Hello User!')
    else:
        print("Login Failed: Invalid username or password.")
