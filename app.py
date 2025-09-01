# app.py
import pkg_resources
print("google-auth-oauthlib version:", pkg_resources.get_distribution("google-auth-oauthlib").version)




import google_auth_oauthlib
print("google-auth-oauthlib version:")

import os, base64
import logging
import sys
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle



# Pillow replacement for imghdr
from PIL import Image

import asyncio

# --- Telethon setup ---
api_id = 24305862       # replace with your API ID from https://my.telegram.org
api_hash = "9c83a1f28298af42fc1647664b6489ae"  # replace with your API hash
TELEGRAM_BOT_TOKEN = "7870598281:AAHNWpT6tVcoVA_6MhYnkAX3XoXAIY21teg"
downloads_dir = "downloads"
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

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def get_drive_service():
    creds = None

    # 1. Try loading from ENV (Render/GitHub secrets)
    token_b64 = os.getenv("TOKEN_PICKLE")
    if token_b64:
        try:
            creds = pickle.loads(base64.b64decode(token_b64))
        except Exception as e:
            print("⚠️ Failed to load creds from env:", e)

    # 🔹 If no valid creds, ask login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        # 🔹 Save the creds for next time
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

        print("🔑 New token.pickle created. Convert to base64 and save as TOKEN_PICKLE env var:")
        with open("token.pickle", "rb") as f:
            print(base64.b64encode(f.read()).decode())

    return build("drive", "v3", credentials=creds)

    

def upload_to_drive(file_path, file_name):
    global drive_service
    drive_service = get_drive_service()  # Use OAuth credentials
    if drive_service is None:
        logger.error("Google Drive service not available.")
        return None

    logger.info(f"Preparing to upload {file_name} to Google Drive.")
    try:
        file_metadata = {"name": file_name}
        if DRIVE_FOLDER_ID:
            file_metadata["parents"] = [DRIVE_FOLDER_ID]

        media = MediaFileUpload(file_path, resumable=True)
        request = drive_service.files().create(body=file_metadata, media_body=media, fields="id")
        response = None
        while response is None:
            status, response = request.next_chunk()  # Upload in chunks
        logger.info(f"File uploaded to Google Drive! ID: {response.get('id')}")
        return response.get("id")
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

# Telethon part for handling files
# -----------------------------
from telethon import TelegramClient, events

client = TelegramClient("telethon_session", api_id, api_hash).start(bot_token=TELEGRAM_BOT_TOKEN)

@client.on(events.NewMessage)
async def handle_file(event):
    try:
        if not event.message.file:
            await event.reply("Please send a document, photo, or video.")
            return
        file_path = await client.download_media(event.message, downloads_dir)
        file_name = os.path.basename(file_path)
        os.makedirs("downloads", exist_ok=True)
        

        logger.info(f"Downloading {file_name} via Telethon...")
        await event.message.download_media(file_path)
        logger.info(f"Downloaded to {file_path}")

        # Upload to Google Drive
        drive_file_id = upload_to_drive(file_path, file_name)
        if drive_file_id:
            await event.reply(f"File uploaded to Google Drive! ID: {drive_file_id}")
            logger.info(f"Replied to user with Drive file ID: {drive_file_id}")
        else:
            await event.reply("Failed to upload file to Google Drive.")
            logger.error("Failed to upload file to Google Drive.")

    except Exception as e:
        logger.error(f"Error in handle_file: {e}", exc_info=True)
        await event.reply(f"Error: {e}")

def main():
    logger.info("Starting Telethon bot.")
    client.run_until_disconnected()

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    logger.info("Running main()")
    main()