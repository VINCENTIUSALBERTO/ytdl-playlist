# ytdl-playlist

A Telegram bot that downloads audio (MP3) from YouTube links and uploads them to Google Drive with organised folder structure.

## Features

- **YouTube support** — videos, shorts, and playlists.
- **MP3 conversion** — best audio quality at 192 kbps with embedded thumbnail and metadata.
- **Google Drive upload** — automatic folder creation for playlists and duplicate detection.
- **Filename sanitization** — strips "(Official Video)", "[4K]", emoji, and special characters.
- **Progress bars** — real-time download / upload progress in the Telegram chat.
- **Friendly errors** — human-readable messages for private, geo-restricted, or unavailable videos.

## Quick Start

### 1. Prerequisites

- Python 3.9+
- `ffmpeg` installed and on `PATH`
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- (Optional) A Google Cloud service account with Drive API enabled

### 2. Install

```bash
pip install -r requirements.txt
```

### 3. Configure

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `GOOGLE_DRIVE_FOLDER_ID` | Root Drive folder ID for uploads |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to service account JSON key |
| `COOKIES_FILE` | Path to `cookies.txt` (optional) |

If `GOOGLE_DRIVE_FOLDER_ID` or the service account file is not configured, the bot will send MP3 files directly to the user instead of uploading to Drive.

### 4. Run

```bash
python main.py
```

## Setting Up `cookies.txt` for yt-dlp

YouTube may occasionally require authentication to download certain content. You can export your browser cookies to bypass this.

### Steps

1. Install a browser extension that exports cookies in Netscape format:
   - **Chrome**: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - **Firefox**: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
2. Visit [youtube.com](https://youtube.com) and sign in to your account.
3. Use the extension to export cookies for `youtube.com`.
4. Save the exported file as `cookies.txt` in the project root (or the path set in `.env`).

> **Security note:** `cookies.txt` contains your session credentials. Never commit it to version control — it is already listed in `.gitignore`.

## Project Structure

```
├── main.py             # Telegram bot entry point
├── drive_utils.py      # Google Drive helper (auth, upload, folders)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── tests/
│   ├── test_main.py         # URL validation & filename sanitization tests
│   └── test_drive_utils.py  # Drive utility tests
└── README.md
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```