"""
YouTube-to-Drive Telegram Bot
==============================
Downloads audio (MP3) from YouTube links and uploads them to Google Drive or
sends them directly to the user.

Usage
-----
1. Copy ``.env.example`` → ``.env`` and fill in the values.
2. ``pip install -r requirements.txt``
3. ``python main.py``
"""

import asyncio
import logging
import os
import re
import shutil
import tempfile
import unicodedata

import yt_dlp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from drive_utils import (
    create_folder,
    get_drive_service,
    upload_file,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
# Matches standard YouTube video URLs, shorts, and youtu.be short-links.
YOUTUBE_VIDEO_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?.*v=|shorts/)|youtu\.be/)[\w\-]+"
)
# Matches YouTube playlist URLs (must contain a ``list=`` parameter).
YOUTUBE_PLAYLIST_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?youtube\.com/(?:playlist\?|watch\?).*list=[\w\-]+"
)


def is_youtube_url(text: str) -> bool:
    """Return ``True`` if *text* looks like any kind of YouTube URL."""
    return bool(YOUTUBE_VIDEO_RE.search(text) or YOUTUBE_PLAYLIST_RE.search(text))


def is_playlist_url(text: str) -> bool:
    """Return ``True`` if *text* is specifically a YouTube *playlist* URL."""
    return bool(YOUTUBE_PLAYLIST_RE.search(text))


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------
# Patterns considered "garbage" in a title.
_GARBAGE_RE = re.compile(
    r"\s*[\[\(]?\s*(?:"
    r"Official\s*(?:Music\s*)?Video|Official\s*Audio|Official\s*Lyric\s*Video|"
    r"Lyrics?\s*(?:Video)?|Music\s*Video|HD|HQ|4K|MV|Audio|"
    r"Visualizer|Visualiser|Remastered(?:\s*\d{4})?|"
    r"Live|Acoustic|Remix|Karaoke"
    r")\s*[\]\)]?",
    re.IGNORECASE,
)

_SPECIAL_CHARS_RE = re.compile(r'[|/\\:*?"<>]')


def sanitize_filename(name: str) -> str:
    """Clean a video title into a safe, readable filename (without extension).

    * Removes emoji / non-Latin symbols.
    * Strips common "garbage" tags (``(Official Video)``, ``[4K]``, etc.).
    * Removes dangerous filesystem characters.
    * Collapses redundant whitespace and trims.
    """
    # Remove emoji and symbols outside Basic Latin + Latin Supplement.
    name = "".join(
        ch for ch in name
        if unicodedata.category(ch)[0] not in ("S", "C")  # Symbol / Control
        or ch in ("-", "'", "&", ",", ".", "!", "?")
    )
    name = _GARBAGE_RE.sub("", name)
    name = _SPECIAL_CHARS_RE.sub("", name)
    name = re.sub(r"\s{2,}", " ", name).strip(" -_()")
    return name


# ---------------------------------------------------------------------------
# yt-dlp download helpers
# ---------------------------------------------------------------------------
def _ydl_opts(output_dir: str) -> dict:
    """Return yt-dlp options for best-audio → MP3 at 192 kbps."""
    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
    }
    if os.path.isfile(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


async def download_audio(
    url: str,
    output_dir: str,
    progress_callback=None,
) -> list[dict]:
    """Download audio from *url* into *output_dir*.

    Returns a list of dicts ``{"filepath": ..., "title": ..., "playlist": ...}``
    for each downloaded track.

    The *progress_callback*, if provided, is called with
    ``(current_index, total, title)`` whenever a new track starts downloading.
    """
    opts = _ydl_opts(output_dir)

    results: list[dict] = []

    def _progress_hook(d):
        if d["status"] == "finished" and progress_callback:
            # yt-dlp fires this per file; we accumulate results below.
            pass

    opts["progress_hooks"] = [_progress_hook]

    loop = asyncio.get_event_loop()

    def _do_download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get("entries") or [info]
            playlist_title = info.get("title") if info.get("entries") else None

            for idx, entry in enumerate(entries, 1):
                if entry is None:
                    continue
                raw_title = entry.get("title", "Unknown")
                clean = sanitize_filename(raw_title)
                ext = "mp3"
                # yt-dlp writes <original_title>.mp3 after conversion.
                original_path = os.path.join(
                    output_dir, f"{entry.get('title', raw_title)}.{ext}"
                )
                final_name = f"{clean}.{ext}"
                final_path = os.path.join(output_dir, final_name)
                # Rename to sanitized name (if the file exists).
                if os.path.isfile(original_path) and original_path != final_path:
                    os.rename(original_path, final_path)
                elif not os.path.isfile(final_path):
                    # Fallback: search for any .mp3 that matches loosely.
                    for f in os.listdir(output_dir):
                        if f.endswith(".mp3") and f not in [
                            r["filepath"] for r in results
                        ]:
                            final_path = os.path.join(output_dir, f)
                            final_name = f
                            break

                results.append(
                    {
                        "filepath": final_path,
                        "title": clean,
                        "playlist": sanitize_filename(playlist_title)
                        if playlist_title
                        else None,
                    }
                )
                if progress_callback:
                    progress_callback(idx, len(entries), clean)

    await loop.run_in_executor(None, _do_download)
    return results


# ---------------------------------------------------------------------------
# Progress-bar helper
# ---------------------------------------------------------------------------
def _bar(fraction: float, width: int = 20) -> str:
    filled = int(width * fraction)
    return "█" * filled + "░" * (width - filled)


async def _edit_progress(message, text: str) -> None:
    """Edit a Telegram message, silently ignoring 'message is not modified'."""
    try:
        await message.edit_text(text, parse_mode="HTML")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Telegram command & message handlers
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    await update.message.reply_text(
        "👋 <b>Welcome!</b>\n\n"
        "Send me a YouTube link (video, short, or playlist) and I will:\n"
        "1️⃣  Download the audio as MP3\n"
        "2️⃣  Upload it to Google Drive\n\n"
        "Only YouTube links are accepted.",
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    await update.message.reply_text(
        "📖 <b>How to use this bot</b>\n\n"
        "• Send a YouTube <b>video</b> link → downloads as a single MP3.\n"
        "• Send a YouTube <b>playlist</b> link → downloads all tracks and "
        "organises them in a Drive sub-folder named after the playlist.\n\n"
        "<b>Supported URL formats:</b>\n"
        "  - https://youtube.com/watch?v=...\n"
        "  - https://youtu.be/...\n"
        "  - https://youtube.com/shorts/...\n"
        "  - https://youtube.com/playlist?list=...\n",
        parse_mode="HTML",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process an incoming text message — the main bot logic."""
    text = update.message.text.strip()

    # ------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------
    if not is_youtube_url(text):
        await update.message.reply_text(
            "🚫 Sorry, I only accept <b>YouTube</b> links.\n"
            "Please send a valid YouTube video, short, or playlist URL.",
            parse_mode="HTML",
        )
        return

    playlist = is_playlist_url(text)
    kind = "playlist" if playlist else "video"
    status_msg = await update.message.reply_text(
        f"⏳ Received a YouTube <b>{kind}</b> link. Starting download…",
        parse_mode="HTML",
    )

    tmpdir = tempfile.mkdtemp(prefix="ytdl_")
    try:
        # ------------------------------------------------------------------
        # 2. Download
        # ------------------------------------------------------------------
        def _dl_progress(current, total, title):
            # Fire-and-forget an async edit from the sync callback.
            pct = current / total if total else 0
            asyncio.get_event_loop().call_soon_threadsafe(
                asyncio.ensure_future,
                _edit_progress(
                    status_msg,
                    f"⬇️ Downloading <b>{title}</b>\n"
                    f"{_bar(pct)} {current}/{total}",
                ),
            )

        try:
            tracks = await download_audio(text, tmpdir, progress_callback=_dl_progress)
        except yt_dlp.utils.DownloadError as exc:
            msg = str(exc).lower()
            if "private" in msg:
                friendly = "🔒 This video is private and cannot be downloaded."
            elif "unavailable" in msg or "removed" in msg:
                friendly = "❌ This video is unavailable or has been removed."
            elif "geo" in msg or "country" in msg:
                friendly = "🌍 This video is geo-restricted in your region."
            elif "sign in" in msg or "bot" in msg:
                friendly = (
                    "⚠️ YouTube is requesting sign-in verification. "
                    "Please ensure a valid cookies.txt is configured."
                )
            else:
                friendly = f"⚠️ Download error: {exc}"
            await _edit_progress(status_msg, friendly)
            return

        if not tracks:
            await _edit_progress(status_msg, "⚠️ No tracks were downloaded.")
            return

        await _edit_progress(
            status_msg,
            f"✅ Downloaded <b>{len(tracks)}</b> track(s). Starting upload…",
        )

        # ------------------------------------------------------------------
        # 3. Upload to Google Drive
        # ------------------------------------------------------------------
        if not GOOGLE_DRIVE_FOLDER_ID or not os.path.isfile(GOOGLE_SERVICE_ACCOUNT_FILE):
            # No Drive config → send files directly to the user.
            for t in tracks:
                if os.path.isfile(t["filepath"]):
                    await update.message.reply_audio(
                        audio=open(t["filepath"], "rb"),
                        title=t["title"],
                    )
            await _edit_progress(
                status_msg, "✅ Done! Files sent directly (Google Drive not configured)."
            )
            return

        service = get_drive_service(GOOGLE_SERVICE_ACCOUNT_FILE)
        target_folder = GOOGLE_DRIVE_FOLDER_ID

        # If it is a playlist, create a sub-folder named after the playlist.
        playlist_name = tracks[0].get("playlist")
        if playlist and playlist_name:
            target_folder = create_folder(service, playlist_name, GOOGLE_DRIVE_FOLDER_ID)

        for idx, t in enumerate(tracks, 1):
            if not os.path.isfile(t["filepath"]):
                continue
            pct = idx / len(tracks)
            await _edit_progress(
                status_msg,
                f"⬆️ Uploading <b>{t['title']}</b>\n"
                f"{_bar(pct)} {idx}/{len(tracks)}",
            )
            upload_file(service, t["filepath"], target_folder)

        await _edit_progress(
            status_msg,
            f"✅ All done! <b>{len(tracks)}</b> track(s) uploaded to Google Drive.",
        )

    finally:
        # Clean up temporary files.
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started. Listening for messages…")
    app.run_polling()


if __name__ == "__main__":
    main()
