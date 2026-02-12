"""Unit tests for main.py – URL validation & filename sanitization."""

import pytest
from main import is_youtube_url, is_playlist_url, sanitize_filename, _ydl_opts


# -----------------------------------------------------------------------
# URL validation
# -----------------------------------------------------------------------
class TestIsYoutubeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abc123DEF",
            "https://youtube.com/watch?v=abc&list=PLxyz",
            "https://youtube.com/playlist?list=PLxyz",
        ],
    )
    def test_valid_youtube_urls(self, url):
        assert is_youtube_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.google.com",
            "https://vimeo.com/12345",
            "not a url at all",
            "https://youtu.be/",
            "",
        ],
    )
    def test_non_youtube_urls(self, url):
        assert is_youtube_url(url) is False


class TestIsPlaylistUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://youtube.com/playlist?list=PLxyz123",
            "https://www.youtube.com/watch?v=abc&list=PLxyz123",
        ],
    )
    def test_playlist_urls(self, url):
        assert is_playlist_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abc123",
        ],
    )
    def test_non_playlist_urls(self, url):
        assert is_playlist_url(url) is False


# -----------------------------------------------------------------------
# Filename sanitization
# -----------------------------------------------------------------------
class TestSanitizeFilename:
    def test_removes_official_video_tag(self):
        assert sanitize_filename("Linkin Park - Numb (Official Video)") == "Linkin Park - Numb"

    def test_removes_4k_tag(self):
        assert sanitize_filename("Artist - Song [4K]") == "Artist - Song"

    def test_removes_lyrics_tag(self):
        assert sanitize_filename("Artist - Song (Lyrics)") == "Artist - Song"

    def test_removes_official_music_video_tag(self):
        result = sanitize_filename("Artist - Song (Official Music Video)")
        assert result == "Artist - Song"

    def test_removes_hd_tag(self):
        assert sanitize_filename("Artist - Song [HD]") == "Artist - Song"

    def test_removes_special_characters(self):
        result = sanitize_filename('Song: The | Best / Ever \\ "Now"')
        assert "|" not in result
        assert "/" not in result
        assert "\\" not in result
        assert ":" not in result
        assert '"' not in result

    def test_collapses_whitespace(self):
        assert sanitize_filename("Artist  -   Song") == "Artist - Song"

    def test_strips_surrounding_junk(self):
        result = sanitize_filename("  - Song Title - ")
        assert result == "Song Title"

    def test_empty_string(self):
        assert sanitize_filename("") == ""

    def test_preserves_basic_punctuation(self):
        result = sanitize_filename("Rock & Roll, Baby!")
        assert "Rock & Roll, Baby!" == result


# -----------------------------------------------------------------------
# yt-dlp options
# -----------------------------------------------------------------------
class TestYdlOpts:
    def test_format_has_fallback_chain(self):
        """Format string should try multiple audio formats before falling back."""
        opts = _ydl_opts("/tmp/test")
        assert "bestaudio" in opts["format"]
        assert "best" in opts["format"]

    def test_retries_configured(self):
        opts = _ydl_opts("/tmp/test")
        assert opts["retries"] == 3
        assert opts["fragment_retries"] == 3

    def test_ignoreerrors_enabled(self):
        opts = _ydl_opts("/tmp/test")
        assert opts["ignoreerrors"] is True
