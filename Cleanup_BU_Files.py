import os
import datetime

# Directories to clean up
BU_MEDIA_DIRECTORY = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/BU-Media"
BU_SCRIPT_DIRECTORY = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/BU-Scripts"

RETENTION_DAYS = 90  # Days before deletion


def cleanup_old_files(directory, retention_days=RETENTION_DAYS, file_extensions=None):
    """Delete files older than retention_days in the specified directory."""
    now = datetime.datetime.now()

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Ensure it's a file and matches allowed extensions
        if os.path.isfile(file_path) and (file_extensions is None or filename.endswith(tuple(file_extensions))):
            file_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            file_age_days = (now - file_modified_time).days

            if file_age_days > retention_days:
                try:
                    os.remove(file_path)
                    print(f"🗑️ Deleted old file: {filename} (Age: {file_age_days} days)")
                except Exception as e:
                    print(f"❌ Error deleting {filename}: {e}")


# Run cleanup for both images and backups
cleanup_old_files(BU_MEDIA_DIRECTORY, file_extensions=[".png"])
cleanup_old_files(BU_SCRIPT_DIRECTORY)  # Cleans all backup files