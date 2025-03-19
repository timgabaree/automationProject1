import os
import openai
import requests
from dotenv import load_dotenv
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google.oauth2 import service_account

# === API KEYS & AUTHENTICATION ===
CREDENTIALS_PATH = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/Credentials/automationProject1"
env_path = os.path.join(CREDENTIALS_PATH, ".env")

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print("⚠️ WARNING: .env file not found!")

# Load environment variables from .env file
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Google Drive Credentials:
DRIVE_CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
SCOPES = ['https://www.googleapis.com/auth/drive']
GOOGLE_DRIVE_FOLDER_ID = "14fjoDVxGY5OZwuGMmzqbNE5nCqQUu1jH"

# Define save directory
FALLBACK_IMAGE_DIRECTORY = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/automationProject1/media/fallback_images"
os.makedirs(FALLBACK_IMAGE_DIRECTORY, exist_ok=True)  # Ensure the folder exists

# Define categories and prompts
fallback_images = {
    "ai_fallback_image.png": "A futuristic AI concept, glowing neural networks and a digital human face in a cyberpunk city.",
    "cybersecurity_fallback_image.png": "A cyber shield protecting data streams, futuristic digital security concept with a glowing firewall.",
    "it_leadership_fallback_image.png": "A confident and visionary IT leader in a modern boardroom, guiding a team in a collaborative discussion. The scene reflects servant leadership, innovation, and teamwork. The leader is warm and approachable. Do not include text in the image."
}


def authenticate_google_drive():
    """Authenticate Google Drive API."""
    creds = service_account.Credentials.from_service_account_file(DRIVE_CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)


def upload_fallback_image_to_drive(file_path):
    """Upload a fallback image to Google Drive and return its public URL."""
    try:
        drive_service = authenticate_google_drive()

        file_metadata = {
            "name": os.path.basename(file_path),
            "parents": [GOOGLE_DRIVE_FOLDER_ID],  # ✅ Replace with your Google Drive Folder ID
        }

        mime_type = "image/png"
        media = MediaFileUpload(file_path, mimetype=mime_type)
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        # ✅ Make file public
        drive_service.permissions().create(
            fileId=uploaded_file["id"],
            body={"role": "reader", "type": "anyone"},
        ).execute()

        public_url = f"https://drive.google.com/uc?id={uploaded_file['id']}"
        print(f"✅ Uploaded to Google Drive: {public_url}")
        return public_url

    except Exception as e:
        print(f"❌ Google Drive upload failed: {e}")
        return None  # ✅ Fallback handling


def generate_fallback_image(file_name, prompt):
    """Generate an AI image, save it locally, and upload it to Google Drive."""
    try:
        print(f"🎨 Generating fallback image: {file_name}")

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1792x1024"
        )

        image_url = response.data[0].url
        file_path = os.path.join(FALLBACK_IMAGE_DIRECTORY, file_name)

        # Download and save image
        img_data = requests.get(image_url).content
        with open(file_path, "wb") as img_file:
            img_file.write(img_data)

        print(f"✅ Saved locally: {file_path}")

        # ✅ Upload to Google Drive after saving locally
        drive_url = upload_fallback_image_to_drive(file_path)
        if drive_url:
            print(f"📤 Google Drive URL: {drive_url}")

    except Exception as e:
        print(f"❌ Error generating {file_name}: {e}")


# === **EXECUTE THE SCRIPT** ===
if __name__ == "__main__":
    print("🚀 Starting fallback image generation and upload process...")

    # ✅ Generate all fallback images and upload them to Google Drive
    for file_name, prompt in fallback_images.items():
        generate_fallback_image(file_name, prompt)

    print("✅ All fallback images are successfully generated and uploaded.")