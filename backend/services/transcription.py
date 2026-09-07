"""
Audio transcription using AWS Transcribe.
Uploads the audio file to S3, starts a transcription job, polls until
complete, downloads the result, and returns a timestamped transcript string.
No local model download required.
"""

import os
import json
import time
import uuid

import boto3
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET_NAME", "meeting-intelligence-site")
S3_PREFIX = "transcribe-jobs"
REGION    = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# AWS Transcribe supported media formats
_FORMAT_MAP = {
    "mp3":  "mp3",
    "mp4":  "mp4",
    "wav":  "wav",
    "m4a":  "mp4",
    "webm": "webm",
    "mov":  "mp4",
    "flac": "flac",
    "ogg":  "ogg",
    "amr":  "amr",
}


def _get_clients():
    kwargs = dict(
        region_name          = REGION,
        aws_access_key_id    = os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key= os.getenv("AWS_SECRET_ACCESS_KEY", ""),
    )
    token = os.getenv("AWS_SESSION_TOKEN", "")
    if token:
        kwargs["aws_session_token"] = token
    return (
        boto3.client("s3",         **kwargs),
        boto3.client("transcribe", **kwargs),
    )


def transcribe(audio_path: str) -> str:
    """
    Transcribe an audio file with AWS Transcribe.
    Returns a timestamped transcript string  ([HH:MM:SS] text …).
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    s3, tc = _get_clients()

    ext        = os.path.splitext(audio_path)[1].lower().lstrip(".")
    job_name   = f"meeting-{uuid.uuid4().hex[:16]}"
    s3_key     = f"{S3_PREFIX}/{job_name}/audio.{ext}"
    result_key = f"{S3_PREFIX}/{job_name}/transcript.json"

    # 1 ── Upload audio to S3
    print(f"[TRANSCRIBE] Uploading → s3://{S3_BUCKET}/{s3_key}", flush=True)
    s3.upload_file(audio_path, S3_BUCKET, s3_key)

    media_format = _FORMAT_MAP.get(ext, "mp4")
    media_uri    = f"s3://{S3_BUCKET}/{s3_key}"

    # 2 ── Start transcription job
    print(f"[TRANSCRIBE] Starting job: {job_name}", flush=True)
    tc.start_transcription_job(
        TranscriptionJobName = job_name,
        Media                = {"MediaFileUri": media_uri},
        MediaFormat          = media_format,
        IdentifyLanguage     = True,
        OutputBucketName     = S3_BUCKET,
        OutputKey            = result_key,
    )

    # 3 ── Poll until COMPLETED or FAILED (max 30 min)
    deadline = time.time() + 1800
    while time.time() < deadline:
        resp   = tc.get_transcription_job(TranscriptionJobName=job_name)
        job    = resp["TranscriptionJob"]
        status = job["TranscriptionJobStatus"]
        print(f"[TRANSCRIBE] Status: {status}", flush=True)

        if status == "COMPLETED":
            break
        if status == "FAILED":
            reason = job.get("FailureReason", "No reason provided by AWS.")
            print(f"[TRANSCRIBE] *** FAILED *** Reason: {reason}", flush=True)
            raise RuntimeError(f"AWS Transcribe failed: {reason}")

        time.sleep(5)
    else:
        raise RuntimeError("AWS Transcribe timed out after 30 minutes.")

    # 4 ── Download transcript JSON from S3
    print("[TRANSCRIBE] Downloading transcript from S3...", flush=True)
    obj  = s3.get_object(Bucket=S3_BUCKET, Key=result_key)
    data = json.loads(obj["Body"].read())

    # 5 ── Format with timestamps
    transcript = _format_transcript(data)

    # 6 ── Cleanup temp S3 objects
    for key in (s3_key, result_key):
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=key)
        except Exception:
            pass

    print(f"[TRANSCRIBE] Done — {len(transcript)} chars", flush=True)
    return transcript


def _format_transcript(data: dict) -> str:
    """Convert AWS Transcribe JSON into  [HH:MM:SS] segment  lines."""
    try:
        items = data["results"]["items"]
        plain = data["results"]["transcripts"][0]["transcript"]
    except (KeyError, IndexError):
        return ""

    if not items:
        return plain

    lines: list[str] = []
    words: list[str] = []
    seg_start: float = 0.0
    WORDS_PER_SEG = 12

    for item in items:
        if item["type"] == "pronunciation":
            t     = float(item.get("start_time", 0))
            word  = item["alternatives"][0]["content"]
            if not words:
                seg_start = t
            words.append(word)
            if len(words) >= WORDS_PER_SEG:
                lines.append(f"[{_ts(seg_start)}] {' '.join(words)}")
                words = []

        elif item["type"] == "punctuation":
            if words:
                words[-1] += item["alternatives"][0]["content"]

    if words:
        lines.append(f"[{_ts(seg_start)}] {' '.join(words)}")

    return "\n".join(lines) if lines else plain


def _ts(seconds: float) -> str:
    t = int(seconds)
    return f"{t // 3600:02d}:{(t % 3600) // 60:02d}:{t % 60:02d}"
