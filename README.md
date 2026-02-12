# ytdl-playlist

A Telegram bot that downloads audio (MP3) from YouTube links and uploads them to Google Drive with organised folder structure.

## Features

- **YouTube support** — videos, shorts, and full playlists.
- **MP3 conversion** — best audio quality at 192 kbps with embedded thumbnail and metadata.
- **Google Drive upload** — automatic folder creation for playlists and duplicate detection.
- **Filename sanitization** — strips "(Official Video)", "[4K]", emoji, and special characters.
- **Progress bars** — real-time download / upload progress in the Telegram chat.
- **Friendly errors** — human-readable messages for private, geo-restricted, or unavailable videos.
- **Retry logic** — automatic retries on transient download failures.

## Quick Start

### 1. Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.9+** | Tested on 3.9 – 3.12 |
| **ffmpeg** | Must be installed and on your `PATH` ([download](https://ffmpeg.org/download.html)) |
| **Telegram bot token** | Create one via [@BotFather](https://t.me/BotFather) |
| **Google Cloud service account** | *(Optional)* Required only for Drive upload |

### 2. Install Dependencies

```bash
git clone https://github.com/VINCENTIUSALBERTO/ytdl-playlist.git
cd ytdl-playlist
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | Bot token from [@BotFather](https://t.me/BotFather) |
| `GOOGLE_DRIVE_FOLDER_ID` | ❌ Optional | Root Google Drive folder ID for uploads. If not set, MP3 files are sent directly via Telegram. |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | ❌ Optional | Path to your Google service account JSON key (default: `service_account.json`) |
| `COOKIES_FILE` | ❌ Optional | Path to `cookies.txt` for yt-dlp authentication (default: `cookies.txt`) |

> **Note:** If `GOOGLE_DRIVE_FOLDER_ID` or the service account file is not configured, the bot falls back to sending MP3 files directly to the Telegram chat.

### 4. Run the Bot

```bash
python main.py
```

The bot will start polling for messages. You should see:

```
Bot started. Listening for messages…
```

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and introduction |
| `/help`  | Detailed usage guide with supported URL formats |
| `/menu`  | Quick-reference command list |

Or simply **paste a YouTube URL** into the chat to start downloading.

## Supported YouTube URL Formats

| Format | Example |
|---|---|
| Standard video | `https://youtube.com/watch?v=dQw4w9WgXcQ` |
| Short link | `https://youtu.be/dQw4w9WgXcQ` |
| Shorts | `https://youtube.com/shorts/abc123` |
| Playlist | `https://youtube.com/playlist?list=PLxyz123` |
| Video in playlist | `https://youtube.com/watch?v=abc&list=PLxyz123` |

## Setting Up Google Drive Upload

### Step 1 — Create a Service Account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Enable the **Google Drive API** for the project.
4. Go to **IAM & Admin → Service Accounts** and create a new service account.
5. Create a JSON key for the service account and download it.
6. Save it in the project root as `service_account.json` (or set the path in `.env`).

### Step 2 — Share a Drive Folder

1. Open Google Drive and create a folder for your uploads.
2. Right-click the folder → **Share** → add the service account email (e.g. `bot@project.iam.gserviceaccount.com`) as an **Editor**.
3. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/<FOLDER_ID>`.
4. Set `GOOGLE_DRIVE_FOLDER_ID=<FOLDER_ID>` in your `.env`.

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

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `YouTube is requesting sign-in verification` | YouTube needs authentication | Set up `cookies.txt` (see above) |
| `Requested format is not available` | Audio format unavailable for this video | Usually a region/rights restriction; try another video |
| `This video is private` | Video is set to private | Ask the uploader to make it public/unlisted |
| `This video is geo-restricted` | Blocked in your server's region | Use a VPN or server in another region |
| `TELEGRAM_BOT_TOKEN is not set` | Missing `.env` config | Copy `.env.example` to `.env` and fill in the token |