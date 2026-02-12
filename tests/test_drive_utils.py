"""Unit tests for drive_utils.py – Drive helper functions."""

from unittest.mock import MagicMock, patch
import pytest

from drive_utils import find_file_in_folder, create_folder, upload_file


# -----------------------------------------------------------------------
# find_file_in_folder
# -----------------------------------------------------------------------
class TestFindFileInFolder:
    def test_returns_id_when_file_exists(self):
        service = MagicMock()
        service.files().list().execute.return_value = {
            "files": [{"id": "abc123", "name": "song.mp3"}]
        }
        assert find_file_in_folder(service, "folder1", "song.mp3") == "abc123"

    def test_returns_none_when_file_missing(self):
        service = MagicMock()
        service.files().list().execute.return_value = {"files": []}
        assert find_file_in_folder(service, "folder1", "song.mp3") is None


# -----------------------------------------------------------------------
# create_folder
# -----------------------------------------------------------------------
class TestCreateFolder:
    def test_returns_existing_folder_id(self):
        """If folder already exists, its ID should be returned without creation."""
        service = MagicMock()
        # find_file_in_folder will find the existing folder
        service.files().list().execute.return_value = {
            "files": [{"id": "existing_id", "name": "My Playlist"}]
        }
        result = create_folder(service, "My Playlist", "root_id")
        assert result == "existing_id"
        # create should NOT have been called
        service.files().create.assert_not_called()

    def test_creates_new_folder(self):
        """When folder does not exist, a new one is created."""
        service = MagicMock()
        # First call (find) → nothing; second call (create) → new id
        service.files().list().execute.return_value = {"files": []}
        service.files().create().execute.return_value = {"id": "new_folder_id"}
        result = create_folder(service, "New Playlist", "root_id")
        assert result == "new_folder_id"


# -----------------------------------------------------------------------
# upload_file
# -----------------------------------------------------------------------
class TestUploadFile:
    def test_skips_upload_when_duplicate(self, tmp_path):
        """If the file already exists in Drive, upload is skipped."""
        # Create a dummy file
        dummy = tmp_path / "song.mp3"
        dummy.write_bytes(b"\x00" * 100)

        service = MagicMock()
        service.files().list().execute.return_value = {
            "files": [{"id": "dup_id", "name": "song.mp3"}]
        }
        result = upload_file(service, str(dummy), "folder_id")
        assert result == "dup_id"
