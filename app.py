# app.py
import pkg_resources
print("google-auth-oauthlib version:", pkg_resources.get_distribution("google-auth-oauthlib").version)

import google_auth_oauthlib
print("google-auth-oauthlib version:")

import os, base64
import logging
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from PIL import Image
import asyncio

# --- Telethon setup ---
try:
    import cryptg
    print("CryptG is installed — Telethon will use it for faster encryption.")
except ImportError:
    print("CryptG not installed — Telethon will use slower pure-Python encryption.")

from telethon import TelegramClient, events

api_id = 24305862       # replace with your API ID
api_hash = "9c83a1f28298af42fc1647664b6489ae"  # replace with your API hash
TELEGRAM_BOT_TOKEN = "7870598281:AAHNWpT6tVcoVA_6MhYnkAX3XoXAIY21teg"
TARGET_CHAT_ID = 1003118263
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

# --- Google Drive Configuration ---
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_FILE = "/etc/secrets/credentials.json"
DRIVE_FOLDER_ID = "1TOxkDN6apsHRf0Bxf9DqF7SYGw2dZJ9L"
drive_service = None

def get_drive_service():
    creds = None
    token_b64 = os.getenv("TOKEN_PICKLE")
    if token_b64:
        try:
            creds = pickle.loads(base64.b64decode(token_b64))
        except Exception as e:
            print("⚠️ Failed to load creds from env:", e)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

        print("🔑 New token.pickle created. Convert to base64 and save as TOKEN_PICKLE env var:")
        with open("token.pickle", "rb") as f:
            print(base64.b64encode(f.read()).decode())

    return build("drive", "v3", credentials=creds)

# Upload with Telegram progress update
async def upload_to_drive(file_path, file_name, progress_callback=None):
    global drive_service
    drive_service = get_drive_service()
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
            status, response = request.next_chunk()
            if status and progress_callback:
                # Detect if callback is async
                import inspect
                if inspect.iscoroutinefunction(progress_callback):
                    await progress_callback(status.progress() * 100)
                else:
                    progress_callback(status.progress() * 100)

        logger.info(f"File uploaded to Google Drive! ID: {response.get('id')}")
        return response.get("id")
    except Exception as e:
        logger.error(f"Failed to upload file to Drive: {e}")
        return None

# Telethon client
client = TelegramClient("telethon_session", api_id, api_hash)

@client.on(events.NewMessage)
async def handle_file(event):
    try:
        if not event.message.file:
            await event.reply("Please send a document, photo, or video.")
            return

        os.makedirs(downloads_dir, exist_ok=True)
        file_path = os.path.join(downloads_dir, f"temp_{event.message.id}")
        file_name = event.message.file.name or f"file_{event.message.id}"

        # Progress message for Telegram
        progress_msg = await event.reply(f"Downloading {file_name}: 0%")

        # Download with progress updates
        downloaded = 0
        total = event.message.file.size or 1
        async for chunk in client.iter_download(event.message, file_path=file_path, chunk_size=5*1024*1024):
            downloaded += len(chunk)
            percent = int(downloaded / total * 100)
            await progress_msg.edit(f"Downloading {file_name}: {percent}%")

        # Upload with Telegram progress updates
        async def tg_upload_progress(percent):
            await progress_msg.edit(f"Uploading {file_name}: {int(percent)}%")

        drive_file_id = await upload_to_drive(file_path, file_name, progress_callback=tg_upload_progress)

        if drive_file_id:
            await event.reply(f"File uploaded to Google Drive! ID: {drive_file_id}")
            logger.info(f"Replied to user with Drive file ID: {drive_file_id}")
        else:
            await event.reply("Failed to upload file to Google Drive.")
            logger.error("Failed to upload file to Google Drive.")

        os.remove(file_path)

    except Exception as e:
        logger.error(f"Error in handle_file: {e}", exc_info=True)
        await event.reply(f"Error: {e}")

# Keep Render alive
async def keep_alive():
    while True:
        try:
            await client.send_message(TARGET_CHAT_ID, "💤 Keeping Render awake...")
        except Exception as e:
            print(f"Error sending keep-alive message: {e}")
        await asyncio.sleep(10)

async def main():
    await client.start(bot_token=TELEGRAM_BOT_TOKEN)
    await asyncio.gather(
        client.run_until_disconnected(),
        keep_alive()
    )

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())