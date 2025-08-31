# app.py
import pkg_resources
print("google-auth-oauthlib version:", pkg_resources.get_distribution("google-auth-oauthlib").version)




import google_auth_oauthlib
print("google-auth-oauthlib version:")

import os
import logging
import sys
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# Pillow replacement for imghdr
from PIL import Image

# --- Logging setup ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s [%(module)s]: %(message)s',
    handlers=[
        logging.FileHandler("telegram_to_drive.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration ---
TELEGRAM_TOKEN = "7870598281:AAHNWpT6tVcoVA_6MhYnkAX3XoXAIY21teg"  # <-- Replace with your token
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_FILE = "/etc/secrets/credentials.json"  # <-- Place this in the same directory

DRIVE_FOLDER_ID = "1TOxkDN6apsHRf0Bxf9DqF7SYGw2dZJ9L"
drive_service = None

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Authenticate using service account
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
drive_service = build("drive", "v3", credentials=creds)

def upload_to_drive(file_path, file_name):
    global drive_service
    logger.info(f"Preparing to upload {file_name} to Google Drive.")
    try:
        if drive_service is None:
            logger.error("Google Drive service not available.")
            return None
        file_metadata = {"name": file_name}
        if DRIVE_FOLDER_ID:
             file_metadata["parents"] = [DRIVE_FOLDER_ID]
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
        logger.info(f"File uploaded to Google Drive! ID: {file.get('id')}")
        return file.get("id")
    except Exception as e:
        logger.error(f"Failed to upload file to Drive: {e}")
        return None

# Pillow helper to detect image type if needed
def get_image_type(file_path):
    try:
        with Image.open(file_path) as img:
            return img.format  # 'JPEG', 'PNG', etc.
    except Exception as e:
        logger.warning(f"Failed to detect image type for {file_path}: {e}")
        return None

def handle_file(update: Update, context: CallbackContext):
    logger.debug("handle_file called.")
    try:
        file_path = None
        file_name = None

        # Handle documents
        if update.message.document:
            document = update.message.document
            file_id = document.file_id
            file_name = document.file_name or "document"
            logger.info(f"Received document: {file_name}, file_id: {file_id}")

            os.makedirs("downloads", exist_ok=True)
            file_path = os.path.join("downloads", file_name)
            logger.info(f"Downloading document to {file_path}")
            file = context.bot.get_file(file_id)
            file.download(custom_path=file_path)
            logger.info(f"Downloaded document: {file_path}")

        # Handle photos
        elif update.message.photo:
            # Get largest photo size
            photo = update.message.photo[-1]
            file_id = photo.file_id
            file_name = f"photo_{file_id}.jpg"
            logger.info(f"Received photo, file_id: {file_id}")

            os.makedirs("downloads", exist_ok=True)
            file_path = os.path.join("downloads", file_name)
            logger.info(f"Downloading photo to {file_path}")
            file = context.bot.get_file(file_id)
            file.download(custom_path=file_path)
            logger.info(f"Downloaded photo: {file_path}")

            # Example: detect type using Pillow
            img_type = get_image_type(file_path)
            logger.info(f"Detected photo type: {img_type}")

        # Handle videos
        elif update.message.video:
            video = update.message.video
            file_id = video.file_id
            file_name = video.file_name or f"video_{file_id}.mp4"
            logger.info(f"Received video: {file_name}, file_id: {file_id}")

            os.makedirs("downloads", exist_ok=True)
            file_path = os.path.join("downloads", file_name)
            logger.info(f"Downloading video to {file_path}")
            file = context.bot.get_file(file_id)
            file.download(custom_path=file_path)
            logger.info(f"Downloaded video: {file_path}")

        else:
            logger.info("Received unsupported message type.")
            update.message.reply_text("Please send a document, photo, or video.")
            return

        # Upload to Google Drive
        drive_file_id = upload_to_drive(file_path, file_name)
        if drive_file_id:
            update.message.reply_text(f"File uploaded to Google Drive! ID: {drive_file_id}")
            logger.info(f"Replied to user with Drive file ID: {drive_file_id}")
        else:
            update.message.reply_text("Failed to upload file to Google Drive.")
            logger.error("Failed to upload file to Google Drive.")

    except Exception as e:
        logger.error(f"Error in handle_file: {e}", exc_info=True)
        try:
            update.message.reply_text(f"Error: {e}")
        except Exception as ex:
            logger.error(f"Failed to send error message to user: {ex}")

def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}", exc_info=True)
    try:
        if update and update.message:
            update.message.reply_text(f"An error occurred: {context.error}")
    except Exception as ex:
        logger.error(f"Failed to send error message in error_handler: {ex}")

def main():
    logger.info("Starting Telegram bot.")
    try:
        updater = Updater(TELEGRAM_TOKEN, use_context=True)
        dp = updater.dispatcher

        # Accept documents, photos, and videos
        dp.add_handler(MessageHandler(Filters.document | Filters.photo | Filters.video, handle_file))
        dp.add_error_handler(error_handler)

        logger.info("Bot polling started.")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}", exc_info=True)

if __name__ == "__main__":
    # Suppress known warnings about urllib3 and pkg_resources for cleaner output
    import warnings
    warnings.filterwarnings("ignore")

    logger.info("Running main()")
    main()