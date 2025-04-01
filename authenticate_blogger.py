from google_auth_oauthlib.flow import InstalledAppFlow

# Define Blogger API Scopes
BLOGGER_SCOPES = ["https://www.googleapis.com/auth/blogger"]

# File Paths
CREDENTIALS_FILE = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/Credentials/automationProject1/blogger_credentials.json"
TOKEN_FILE = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/Credentials/automationProject1/blogger_token.json"

def authenticate_blogger():
    """Authenticate to Blogger API and save access token."""
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, BLOGGER_SCOPES)
    creds = flow.run_local_server(port=0)  # Opens a browser for authentication

    # Save the credentials for future use
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())

    print("✅ Authentication successful! Token saved to", TOKEN_FILE)

if __name__ == "__main__":
    authenticate_blogger()