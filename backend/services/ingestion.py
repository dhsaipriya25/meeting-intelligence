"""
Ingestion service: handles file uploads, YouTube audio download,
audio extraction from video, and text extraction from documents.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".webm", ".mov", ".txt", ".pdf", ".docx", ".doc"}
TEMP_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")


def _job_dir(job_id: str) -> str:
    path = os.path.join(TEMP_BASE, job_id)
    os.makedirs(path, exist_ok=True)
    return path


async def save_upload(file: UploadFile, job_id: str) -> str:
    """
    Save an uploaded file to ./temp/{job_id}/. Returns the saved file path.
    Accepts .mp3, .mp4, .txt, .pdf, .docx only.
    """
    job_dir = _job_dir(job_id)
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

    dest = os.path.join(job_dir, filename)
    async with aiofiles.open(dest, "wb") as out_file:
        while True:
            chunk = await file.read(1024 * 1024)  # 1 MB chunks
            if not chunk:
                break
            await out_file.write(chunk)

    return dest


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_transcript(url: str) -> Optional[str]:
    """
    Fetch captions from YouTube using youtube-transcript-api v1.x.
    Returns a timestamped transcript string, or None if unavailable.
    SSL verification is disabled globally in main.py before this runs.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("[YOUTUBE] youtube-transcript-api not installed.", flush=True)
        return None

    video_id = _extract_video_id(url)
    if not video_id:
        print(f"[YOUTUBE] Could not extract video ID from: {url}", flush=True)
        return None

    print(f"[YOUTUBE] Fetching captions for video ID: {video_id}", flush=True)

    api = YouTubeTranscriptApi()

    # Try preferred languages first, then fall back to any available
    for langs in (["en", "en-US", "en-GB"], None):
        try:
            if langs is not None:
                fetched = api.fetch(video_id, languages=langs)
            else:
                # List all transcripts and pick the first available
                transcript_list = api.list(video_id)
                first = next(iter(transcript_list), None)
                if first is None:
                    print("[YOUTUBE] No transcripts available.", flush=True)
                    return None
                fetched = first.fetch()

            snippets = list(fetched)
            if not snippets:
                continue

            lines = []
            for s in snippets:
                # v1.x returns TranscriptSnippet objects with .text .start .duration
                start = int(getattr(s, "start", 0))
                text  = str(getattr(s, "text", "")).strip().replace("\n", " ")
                if text:
                    h, m, sec = start // 3600, (start % 3600) // 60, start % 60
                    lines.append(f"[{h:02d}:{m:02d}:{sec:02d}] {text}")

            if lines:
                print(f"[YOUTUBE] Got {len(lines)} caption segments.", flush=True)
                return "\n".join(lines)

        except Exception as exc:
            if langs is not None:
                print(f"[YOUTUBE] No {langs} captions, trying fallback. ({exc})", flush=True)
            else:
                print(f"[YOUTUBE] Caption fetch failed: {exc}", flush=True)
                return None

    return None


def download_youtube(url: str, job_id: str) -> str:
    """
    Download best audio from a YouTube URL as MP3 to ./temp/{job_id}/audio.mp3.
    Returns the path to the downloaded file.
    Raises RuntimeError on failure (geo-restriction, private video, etc.).
    """
    import yt_dlp

    job_dir = _job_dir(job_id)
    output_path = os.path.join(job_dir, "audio.%(ext)s")

    ffmpeg_dir = os.path.dirname(_get_ffmpeg_path())

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
        # Retry aggressively — Windows gets ConnectionResetError(10054) from YouTube CDN
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 5,
        "file_access_retries": 5,
        "socket_timeout": 30,
        # Mimic a real browser so YouTube doesn't reset the connection
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        # Force HTTP/1.1 — avoids Windows TLS/HTTP2 reset issues
        "legacy_server_connect": True,
        "ffmpeg_location": ffmpeg_dir,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise RuntimeError("yt-dlp could not extract video info.")
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(f"YouTube download failed: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Unexpected error downloading YouTube audio: {exc}") from exc

    # Locate the converted mp3 file
    final_path = os.path.join(job_dir, "audio.mp3")
    if not os.path.isfile(final_path):
        for f in os.listdir(job_dir):
            if f.endswith(".mp3"):
                final_path = os.path.join(job_dir, f)
                break
        else:
            raise RuntimeError(
                "YouTube download appeared to succeed but no MP3 file was found. "
                "Check that ffmpeg is installed and working."
            )

    return final_path


def _get_ffmpeg_path() -> str:
    """Get ffmpeg binary path — uses bundled imageio-ffmpeg, no system install needed."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"  # fallback to system ffmpeg if available


def extract_audio_from_mp4(video_path: str) -> str:
    """
    Extract audio from an MP4 file using bundled ffmpeg (imageio-ffmpeg).
    Returns path to the extracted .wav file.
    """
    video_path = os.path.abspath(video_path)
    audio_path = os.path.splitext(video_path)[0] + ".wav"

    cmd = [
        _get_ffmpeg_path(),
        "-y",                  # overwrite output
        "-i", video_path,
        "-vn",                 # no video
        "-acodec", "pcm_s16le",
        "-ar", "16000",        # 16 kHz — good for Whisper
        "-ac", "1",            # mono
        audio_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,           # 5-minute timeout for large files
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg exited with code {result.returncode}: "
            f"{result.stderr.decode(errors='replace')}"
        )

    return audio_path


def read_text_file(file_path: str) -> str:
    """Read a plain .txt file and return its content."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_pdf_file(file_path: str) -> str:
    """Extract text from all pages of a PDF using PyPDF2."""
    import PyPDF2

    pages_text = []
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

    return "\n\n".join(pages_text)


def read_docx_file(file_path: str) -> str:
    """Extract text from all paragraphs of a DOCX file using python-docx."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n\n".join(paragraphs)


def prepare_input(
    input_type: str,
    file_path: Optional[str] = None,
    raw_text: Optional[str] = None,
    job_id: Optional[str] = None,
) -> dict:
    """
    Normalise the varied input types into a uniform dict:
        {"audio_path": str | None, "text": str | None}

    input_type values: mp4 | mp3 | youtube | text_file | raw_text

    For text-based inputs (text_file, raw_text), returns text content.
    For audio/video inputs (mp3, mp4, youtube), returns audio_path.
    """
    result = {"audio_path": None, "text": None}

    if input_type == "raw_text":
        if not raw_text:
            raise ValueError("raw_text is required for input_type='raw_text'.")
        result["text"] = raw_text

    elif input_type == "text_file":
        if not file_path:
            raise ValueError("file_path is required for input_type='text_file'.")
        ext = Path(file_path).suffix.lower()
        if ext == ".txt":
            result["text"] = read_text_file(file_path)
        elif ext == ".pdf":
            result["text"] = read_pdf_file(file_path)
        elif ext == ".docx":
            result["text"] = read_docx_file(file_path)
        else:
            raise ValueError(f"Unsupported text file extension: {ext}")

    elif input_type == "mp3":
        if not file_path:
            raise ValueError("file_path is required for input_type='mp3'.")
        result["audio_path"] = file_path

    elif input_type == "mp4":
        if not file_path:
            raise ValueError("file_path is required for input_type='mp4'.")
        audio_path = extract_audio_from_mp4(file_path)
        result["audio_path"] = audio_path

    elif input_type == "youtube":
        if not job_id:
            raise ValueError("job_id is required for input_type='youtube'.")
        if not raw_text:  # raw_text used as the URL in this context
            raise ValueError("YouTube URL is required.")
        audio_path = download_youtube(raw_text, job_id)
        result["audio_path"] = audio_path

    else:
        raise ValueError(f"Unknown input_type: {input_type}")

    return result
