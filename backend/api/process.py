"""
FastAPI router for the meeting intelligence API.
Prefix: /api

Endpoints:
  POST   /api/process               — submit a new job
  GET    /api/progress/{job_id}     — SSE stream of job progress
  GET    /api/results/{job_id}      — fetch completed results
  GET    /api/download/{job_id}/{file_type} — download an export file
"""

import asyncio
import json
import os
import traceback
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

import job_store
from agents.orchestrator import run_pipeline
from services import ingestion, export as export_svc

router = APIRouter(prefix="/api")

TEMP_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")

# Mapping of file_type → (export_fn, content_type, filename)
_EXPORT_MAP = {
    "transcript_txt": (
        lambda j: export_svc.transcript_to_txt(j.transcript or ""),
        "text/plain; charset=utf-8",
        "transcript.txt",
    ),
    "transcript_docx": (
        lambda j: export_svc.transcript_to_docx(j.transcript or ""),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "transcript.docx",
    ),
    "transcript_pdf": (
        lambda j: export_svc.transcript_to_pdf(j.transcript or ""),
        "application/pdf",
        "transcript.pdf",
    ),
    "summary_txt": (
        lambda j: export_svc.summary_to_txt(j.summary or ""),
        "text/plain; charset=utf-8",
        "summary.txt",
    ),
    "summary_pdf": (
        lambda j: export_svc.summary_to_pdf(j.summary or ""),
        "application/pdf",
        "summary.pdf",
    ),
    "actions_excel": (
        lambda j: export_svc.actions_to_excel(j.action_items or []),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "action_items.xlsx",
    ),
    "actions_pdf": (
        lambda j: export_svc.actions_to_pdf(j.action_items or []),
        "application/pdf",
        "action_items.pdf",
    ),
    "risks_excel": (
        lambda j: export_svc.risks_to_excel(j.risks or []),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "risks.xlsx",
    ),
    "risks_pdf": (
        lambda j: export_svc.risks_to_pdf(j.risks or []),
        "application/pdf",
        "risks.pdf",
    ),
    "mom_docx": (
        lambda j: export_svc.mom_to_docx(j.mom_document or ""),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "minutes_of_meeting.docx",
    ),
    "mom_pdf": (
        lambda j: export_svc.mom_to_pdf(j.mom_document or ""),
        "application/pdf",
        "minutes_of_meeting.pdf",
    ),
    "email_txt": (
        lambda j: export_svc.email_to_txt(j.email_draft or ""),
        "text/plain; charset=utf-8",
        "follow_up_email.txt",
    ),
    "explanation_txt": (
        lambda j: (j.detailed_explanation or "").encode("utf-8"),
        "text/plain; charset=utf-8",
        "explanation.txt",
    ),
    "explanation_pdf": (
        lambda j: export_svc.text_to_pdf("Detailed Explanation", j.detailed_explanation or ""),
        "application/pdf",
        "explanation.pdf",
    ),
    "steps_txt": (
        lambda j: (j.steps_detail or "").encode("utf-8"),
        "text/plain; charset=utf-8",
        "steps.txt",
    ),
    "steps_pdf": (
        lambda j: export_svc.text_to_pdf("Steps Detail", j.steps_detail or ""),
        "application/pdf",
        "steps.pdf",
    ),
}


# ---------------------------------------------------------------------------
# POST /api/process
# ---------------------------------------------------------------------------

@router.post("/process")
async def process_meeting(
    request: Request,
    background_tasks: BackgroundTasks,
    input_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    youtube_url: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None),
    output_mode: str = Form("meeting_analysis"),
):
    """
    Submit a meeting for processing.
    Exactly one of: file, youtube_url, or raw_text must be provided.
    Returns {"job_id": "<uuid>"}.
    """
    print(f"DEBUG input_type={input_type!r} file={file} youtube_url={youtube_url!r} raw_text={bool(raw_text)}")

    # Validate exactly one input
    provided = sum([
        file is not None,
        bool(youtube_url),
        bool(raw_text and input_type == "raw_text"),
    ])
    if provided == 0:
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of: file, youtube_url, or raw_text.",
        )
    if provided > 1:
        raise HTTPException(
            status_code=422,
            detail="Provide only one of: file, youtube_url, or raw_text.",
        )

    # Create job and temp directory
    job_id = job_store.create_job()
    temp_dir = os.path.join(TEMP_BASE, job_id)
    os.makedirs(temp_dir, exist_ok=True)
    job_store.update_job(job_id, temp_dir=temp_dir)

    audio_path: Optional[str] = None
    text_content: Optional[str] = None

    try:
        if file is not None:
            ext = Path(file.filename or "").suffix.lower()
            saved_path = await ingestion.save_upload(file, job_id)

            if ext in (".mp4", ".mov", ".mp3", ".wav", ".m4a", ".webm"):
                # Pass audio/video directly to AWS Transcribe — no local ffmpeg needed
                audio_path = saved_path
                input_type = "mp4" if ext in (".mp4", ".mov") else "mp3"
            elif ext in (".txt", ".pdf", ".docx", ".doc"):
                # Read text immediately; pass as raw_text to pipeline
                if ext == ".txt":
                    text_content = ingestion.read_text_file(saved_path)
                elif ext == ".pdf":
                    text_content = ingestion.read_pdf_file(saved_path)
                elif ext in (".docx", ".doc"):
                    text_content = ingestion.read_docx_file(saved_path)
                input_type = "text_file"
            else:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported file type: {ext}. Supported: mp3, mp4, wav, m4a, webm, mov, txt, pdf, docx",
                )

        elif youtube_url:
            # YouTube download happens inside the pipeline (blocking, may be slow)
            # Pass the URL as raw_text; orchestrator routes on input_type="youtube"
            text_content = youtube_url
            input_type = "youtube"
            output_mode = "content_analysis"

        elif raw_text and input_type == "raw_text":
            text_content = raw_text

    except HTTPException:
        raise
    except Exception as exc:
        job_store.update_job(job_id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Input processing error: {exc}")

    # Schedule background pipeline
    background_tasks.add_task(
        run_pipeline,
        job_id=job_id,
        input_type=input_type,
        output_mode=output_mode,
        audio_path=audio_path,
        raw_text=text_content,
    )

    return {"job_id": job_id}


# ---------------------------------------------------------------------------
# GET /api/progress/{job_id}  — SSE
# ---------------------------------------------------------------------------

@router.get("/progress/{job_id}")
async def progress_stream(job_id: str):
    """
    Server-Sent Events stream. Yields progress updates every 2 seconds.
    Closes when job reaches 'completed' or 'failed'.
    """

    async def event_generator():
        while True:
            job = job_store.get_job(job_id)
            if job is None:
                data = json.dumps({
                    "status": "not_found",
                    "progress": 0,
                    "current_agent": "",
                    "error": "Job not found or expired.",
                })
                yield {"data": data}
                return

            payload = {
                "status": job.status,
                "progress": job.progress,
                "current_agent": job.current_agent,
                "error": job.error,
            }
            yield {"data": json.dumps(payload)}

            if job.status in ("completed", "failed"):
                return

            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# GET /api/results/{job_id}
# ---------------------------------------------------------------------------

@router.get("/results/{job_id}")
async def get_results(job_id: str):
    """
    Fetch all results for a completed job.
    Returns 202 if the job is still in progress.
    """
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    if job.status == "failed":
        return JSONResponse(
            status_code=500,
            content={
                "job_id": job_id,
                "status": job.status,
                "error": job.error,
            },
        )

    if job.status != "completed":
        return JSONResponse(
            status_code=202,
            content={
                "job_id": job_id,
                "status": job.status,
                "progress": job.progress,
                "current_agent": job.current_agent,
                "message": "Job is still processing.",
            },
        )

    return {
        "job_id": job_id,
        "status": job.status,
        "transcript": job.transcript,
        "summary": job.summary,
        "output_mode": job.output_mode,
        "action_items": job.action_items,
        "risks": job.risks,
        "mom_document": job.mom_document,
        "email_draft": job.email_draft,
        "detailed_explanation": job.detailed_explanation,
        "steps_detail": job.steps_detail,
    }


# ---------------------------------------------------------------------------
# GET /api/download/{job_id}/{file_type}
# ---------------------------------------------------------------------------

@router.get("/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str):
    """
    Download an exported file for a completed job.

    file_type options:
      transcript_txt, transcript_docx, transcript_pdf,
      summary_txt, summary_pdf,
      actions_excel, actions_pdf,
      risks_excel, risks_pdf,
      mom_docx, mom_pdf,
      email_txt
    """
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not yet completed. Current status: {job.status}",
        )

    if file_type not in _EXPORT_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown file_type '{file_type}'. Valid options: {list(_EXPORT_MAP.keys())}",
        )

    export_fn, content_type, filename = _EXPORT_MAP[file_type]

    try:
        file_bytes = export_fn(job)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Export generation failed: {exc}",
        )

    return StreamingResponse(
        BytesIO(file_bytes),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
