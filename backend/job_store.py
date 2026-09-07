"""
In-memory job store for meeting intelligence pipeline.
Jobs auto-expire after 2 hours and temp files are cleaned up on access.
"""

import uuid
import time
import shutil
import os
from dataclasses import dataclass, field
from typing import Optional

# 2-hour TTL in seconds
JOB_TTL_SECONDS = 7200

JOBS: dict[str, "JobStatus"] = {}


@dataclass
class JobStatus:
    job_id: str
    status: str = "pending"         # pending | transcribing | summarizing | extracting_actions | analyzing_risks | generating_mom | drafting_email | completed | failed
    progress: int = 0               # 0-100
    current_agent: str = ""
    error: Optional[str] = None

    # Results filled as agents complete
    transcript: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[list] = None
    risks: Optional[list] = None
    mom_document: Optional[str] = None
    email_draft: Optional[str] = None
    output_mode: str = "meeting_analysis"   # "meeting_analysis" | "content_analysis"
    detailed_explanation: Optional[str] = None
    steps_detail: Optional[str] = None

    # Temp working directory for cleanup
    temp_dir: Optional[str] = None

    # Internal timestamp for TTL tracking
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


def create_job() -> str:
    """Create a new job entry and return the job_id."""
    job_id = str(uuid.uuid4())
    JOBS[job_id] = JobStatus(job_id=job_id)
    return job_id


def get_job(job_id: str) -> Optional[JobStatus]:
    """
    Return the JobStatus or None.
    If the job is older than JOB_TTL_SECONDS, remove it and return None.
    """
    job = JOBS.get(job_id)
    if job is None:
        return None

    age = time.time() - job.created_at
    if age > JOB_TTL_SECONDS:
        cleanup_job(job_id)
        return None

    return job


def update_job(job_id: str, **kwargs) -> None:
    """Update any fields on a JobStatus by keyword arguments."""
    job = JOBS.get(job_id)
    if job is None:
        return
    for key, value in kwargs.items():
        if hasattr(job, key):
            setattr(job, key, value)
    job.updated_at = time.time()


def cleanup_job(job_id: str) -> None:
    """Delete temp files for the job and remove it from JOBS."""
    job = JOBS.get(job_id)
    if job is None:
        return

    if job.temp_dir and os.path.isdir(job.temp_dir):
        try:
            shutil.rmtree(job.temp_dir, ignore_errors=True)
        except Exception:
            pass  # Best effort cleanup

    JOBS.pop(job_id, None)
