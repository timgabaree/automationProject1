import os
import datetime

# Path to the log file
LOG_FILE_PATH = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/Logs/automationProject1/script_log.txt"

def rotate_log():
    """Deletes and recreates the log file every 30 days."""
    try:
        if os.path.exists(LOG_FILE_PATH):
            os.remove(LOG_FILE_PATH)
            print(f"🗑️ Deleted old log file: {LOG_FILE_PATH}")

        # Recreate an empty log file
        with open(LOG_FILE_PATH, "w") as log_file:
            log_file.write(f"{datetime.datetime.now()} - Log file created\n")
            print(f"✅ New log file created: {LOG_FILE_PATH}")

    except Exception as e:
        print(f"❌ Error rotating log file: {e}")

# Run log rotation
rotate_log()