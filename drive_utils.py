"""
Google Drive utility module for uploading MP3 files.

Handles authentication via a Service Account, folder creation for playlists,
duplicate detection, and file uploads with progress tracking.
"""

import os
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service(service_account_file: str):
    """Authenticate with Google Drive using a Service Account JSON key file."""
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def find_file_in_folder(service, folder_id: str, filename: str) -> str | None:
    """Check if a file with the given name already exists inside *folder_id*.

    Returns the file ID if found, otherwise ``None``.
    """
    query = (
        f"name = '{filename}' and '{folder_id}' in parents and trashed = false"
    )
    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)", pageSize=1)
        .execute()
    )
    files = results.get("files", [])
    return files[0]["id"] if files else None


def create_folder(service, folder_name: str, parent_folder_id: str) -> str:
    """Create a folder inside *parent_folder_id* and return its ID.

    If a folder with the same name already exists, its ID is returned instead
    of creating a duplicate.  This keeps the Drive tidy when the same playlist
    is downloaded more than once.
    """
    existing = find_file_in_folder(service, parent_folder_id, folder_name)
    if existing:
        logger.info("Folder '%s' already exists (ID: %s)", folder_name, existing)
        return existing

    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    folder_id = folder.get("id")
    logger.info("Created folder '%s' (ID: %s)", folder_name, folder_id)
    return folder_id


def upload_file(
    service,
    filepath: str,
    folder_id: str,
    progress_callback=None,
) -> str:
    """Upload *filepath* into *folder_id* on Google Drive.

    Parameters
    ----------
    service : googleapiclient.discovery.Resource
        An authorised Google Drive API service instance.
    filepath : str
        Absolute or relative path to the local file.
    folder_id : str
        The Drive folder ID where the file will be placed.
    progress_callback : callable, optional
        Called with ``(progress_fraction)`` (0.0 – 1.0) after each chunk.

    Returns
    -------
    str
        The Drive file ID of the newly uploaded file.
    """
    filename = os.path.basename(filepath)

    # Duplicate check — skip upload if the file already exists.
    existing = find_file_in_folder(service, folder_id, filename)
    if existing:
        logger.info("File '%s' already exists in folder (ID: %s)", filename, existing)
        return existing

    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(filepath, mimetype="audio/mpeg", resumable=True)

    request = service.files().create(
        body=file_metadata, media_body=media, fields="id"
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status and progress_callback:
            progress_callback(status.progress())

    file_id = response.get("id")
    logger.info("Uploaded '%s' → Drive ID: %s", filename, file_id)
    return file_id
