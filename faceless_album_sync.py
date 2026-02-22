import logging
import os
import smtplib
import ssl
import sys
import traceback
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration loading ---
IMMICH_URL = str(os.getenv("IMMICH_URL"))
API_KEY = str(os.getenv("API_KEY"))
ALBUM_NAME = str(os.getenv("ALBUM_NAME"))
LOG_FILE_PATH = str(os.getenv("LOG_FILE_PATH"))
enable_email_helper = str(os.getenv("ENABLE_EMAIL_ON_ERROR"))
ENABLE_EMAIL_ON_ERROR = enable_email_helper.lower() in (
    "True",
    "true",
    "1",
    "yes",
    "on",
)
EMAIL_SMTP_SERVER = str(os.getenv("EMAIL_SMTP_SERVER"))
smtp_port_helper = str(os.getenv("EMAIL_SMTP_PORT"))
EMAIL_SMTP_PORT = int(smtp_port_helper)
EMAIL_USERNAME = str(os.getenv("EMAIL_USERNAME"))
EMAIL_PASSWORD = str(os.getenv("EMAIL_PASSWORD"))
EMAIL_TO = str(os.getenv("EMAIL_TO"))
EMAIL_FROM = str(os.getenv("EMAIL_FROM"))
# ---------------------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE_PATH, maxBytes=5 * 1024 * 1024, backupCount=3),
        logging.StreamHandler(sys.stdout),
    ],
)

HEADERS: dict[str, str] = {"x-api-key": API_KEY, "Accept": "application/json"}


def send_error_email(exc: Exception) -> None:
    """Send an email containing the exception traceback. Uses the Gmail SMTP settings above."""
    if not ENABLE_EMAIL_ON_ERROR:
        return

    try:
        tb = traceback.format_exc()
        subject = f"[Faceless Album Sync] Unhandled exception: {type(exc).__name__}"
        body = f"An unhandled exception occurred in Faceless_album_sync.py:\n\nException: {exc}\n\nTraceback:\n{tb}"

        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg["Subject"] = subject
        msg.set_content(body)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, context=context
        ) as server:
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info("Error notification email sent successfully.")

    except Exception:
        logging.error("Failed to send error notification email.", exc_info=True)


def get_all_asset_ids() -> set[str]:
    untagged_ids = set()
    page = 1
    page_size = 250

    while True:
        response = requests.post(
            f"{IMMICH_URL}/api/search/metadata",
            headers=HEADERS,
            json={"withPeople": True, "page": page, "size": page_size},
            verify=False,
        )
        response.raise_for_status()
        assets_node = response.json().get("assets", {})
        assets = assets_node.get("items", []) if isinstance(assets_node, dict) else []
        untagged_ids.update(asset["id"] for asset in assets if not asset.get("people"))

        if len(assets) < page_size:
            break
        page += 1

    return untagged_ids


def get_or_create_album(name: str) -> str:
    """Finds an existing album by name or creates a new one."""
    # 1. Search for existing album
    response = requests.get(f"{IMMICH_URL}/api/albums", headers=HEADERS)
    response.raise_for_status()
    albums = response.json()

    for album in albums:
        if album["albumName"] == name:
            logging.info(f"Found existing album: {name}")
            return album["id"]

    # 2. Create if not found
    logging.info(f"Album '{name}' not found. Creating it...")
    payload = {"albumName": name}
    response = requests.post(f"{IMMICH_URL}/api/albums", headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()["id"]


def add_assets_to_album(album_id: str, asset_ids: set[str]) -> None:
    """Adds a list of asset IDs to the specified album."""
    # Convert set to list for JSON serialization
    payload = {"ids": list(asset_ids)}

    # PUT /api/albums/{id}/assets is the standard endpoint
    url = f"{IMMICH_URL}/api/albums/{album_id}/assets"
    response = requests.put(url, headers=HEADERS, json=payload)
    response.raise_for_status()

    result = response.json()
    # The API typically returns a list of results for each ID
    success_count = sum(1 for item in result if item.get("success", True))
    logging.info(f"Successfully added {success_count} assets to the album.")


def get_assets_in_album(album_id: str) -> set[str]:
    """Fetches all asset IDs currently in the specified album."""
    response = requests.get(f"{IMMICH_URL}/api/albums/{album_id}", headers=HEADERS)
    response.raise_for_status()
    return set(asset["id"] for asset in response.json().get("assets", []))


def remove_assets_from_album(album_id: str, asset_ids: set[str]) -> None:
    """Removes a list of asset IDs from the specified album."""
    payload = {"ids": list(asset_ids)}
    url = f"{IMMICH_URL}/api/albums/{album_id}/assets"
    response = requests.delete(url, headers=HEADERS, json=payload)
    response.raise_for_status()

    result = response.json()
    success_count = sum(1 for item in result if item.get("success", True))
    logging.info(f"Successfully removed {success_count} assets from the album.")


def main() -> None:
    try:
        logging.info("Starting sync process...")
        logging.info("Fetching asset IDs...")
        no_people = get_all_asset_ids()

        album_id = get_or_create_album(ALBUM_NAME)

        logging.info("Fetching current album assets...")
        current_album_assets = get_assets_in_album(album_id)

        ids_to_add = no_people - current_album_assets
        ids_to_remove = current_album_assets - no_people

        if ids_to_add:
            add_assets_to_album(album_id, ids_to_add)
        else:
            logging.info("No new assets to add.")

        if ids_to_remove:
            remove_assets_from_album(album_id, ids_to_remove)
        else:
            logging.info("No assets to remove.")

        logging.info("Sync process completed.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        # Send email notification if enabled
        try:
            send_error_email(e)
        except Exception:
            # send_error_email already logs failures; avoid raising from the global exception handler
            pass


if __name__ == "__main__":
    main()
