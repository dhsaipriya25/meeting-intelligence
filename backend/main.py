"""
Meeting Intelligence API — main application entry point.
"""

# ── SSL bypass (corporate network fix — must be before ALL other imports) ──
import ssl
import os
import urllib3

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests as _req
_orig_session_request = _req.Session.request
def _no_ssl_request(self, method, url, **kwargs):
    kwargs["verify"] = False
    return _orig_session_request(self, method, url, **kwargs)
_req.Session.request = _no_ssl_request

os.environ.setdefault("PYTHONHTTPSVERIFY", "0")
# ──────────────────────────────────────────────────────────────────────────

import traceback
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Meeting Intelligence API",
    description=(
        "Upload an MP4, MP3, YouTube link, or text file and get back "
        "a transcript, summary, action items, risks, MOM, and email draft."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.process import router
app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"\n===== UNHANDLED ERROR =====\n{tb}\n===========================\n")
    return JSONResponse(status_code=500, content={"detail": str(exc), "traceback": tb})


@app.on_event("startup")
def _startup():
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    print("[STARTUP] Meeting Intelligence API ready.", flush=True)
    print(f"[STARTUP] S3 Bucket : {os.getenv('S3_BUCKET_NAME', 'NOT SET')}", flush=True)
    print(f"[STARTUP] Bedrock   : {os.getenv('BEDROCK_MODEL_ID', 'NOT SET')}", flush=True)
    print(f"[STARTUP] Region    : {os.getenv('AWS_DEFAULT_REGION', 'NOT SET')}", flush=True)


@app.get("/")
def root():
    return {"status": "running", "message": "Meeting Intelligence API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
