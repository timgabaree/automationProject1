import os
import subprocess

SOURCE_DIR = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/automationProject1/media/"
DEST_DIR = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/BU-Media/automationProject1"

def sync_media():
    """Syncs all media files to the backup directory."""
    try:
        subprocess.run(["rsync", "-av", "--delete", SOURCE_DIR, DEST_DIR], check=True)
        print(f"✅ Media files successfully synced from {SOURCE_DIR} to {DEST_DIR}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Media sync failed: {e}")

sync_media()