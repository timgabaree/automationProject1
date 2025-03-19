from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/Credentials/automationProject1/drive_credentials.json"
TIMGABAREE_BLOGGER_IMAGE_FOLDER_ID = "14fjoDVxGY5OZwuGMmzqbNE5nCqQUu1jH"
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build("drive", "v3", credentials=creds)

# Test access by listing files
results = drive_service.files().list(q=f"'{TIMGABAREE_BLOGGER_IMAGE_FOLDER_ID}' in parents", fields="files(id, name)").execute()
items = results.get('files', [])

if not items:
    print("No files found. Check permissions.")
else:
    print("✅ Service Account has access! Files in the folder:")
    for item in items:
        print(f"{item['name']} ({item['id']})")