#!/usr/bin/env python3
"""
SAF-T Validator & Analytics — FastAPI Backend

Understøtter filer op til 2 GB med asynkron jobhåndtering:
- Filer < 100 MB: behandles synkront (som hidtil)
- Filer >= 100 MB: behandles i baggrundstråd med job-tracking
"""

import os
import uuid
import secrets
import shutil
import threading
import time
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from validator.report import generate_report
from analytics.engine import analyze_file
from analytics.parser import parse_saft_file

logger = logging.getLogger(__name__)

app = FastAPI(title="SAF-T Validator & Analytics", version="2.0.0")
security = HTTPBasic()

# Brugere med adgang (fra environment variable eller fallback)
def _parse_auth_users(env_str: str) -> dict:
    """Parse 'user1:pass1,user2:pass2' format til dict."""
    users = {}
    for pair in env_str.split(","):
        pair = pair.strip()
        if ":" in pair:
            username, password = pair.split(":", 1)
            users[username.strip()] = password.strip()
    return users

USERS = _parse_auth_users(
    os.environ.get("AUTH_USERS", "admin:balai2025,Fabian:Salvatore")
)


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verificér brugernavn og password."""
    correct_password = USERS.get(credentials.username)
    if not correct_password or not secrets.compare_digest(
        credentials.password.encode("utf-8"), correct_password.encode("utf-8")
    ):
        from fastapi.responses import JSONResponse
        raise HTTPException(
            status_code=401,
            detail="Forkert brugernavn eller adgangskode",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://analytics.balai.dk"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# === Filstørrelsesgrænser ===
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
ASYNC_THRESHOLD = 100 * 1024 * 1024     # 100 MB — filer over denne behandles asynkront


# === Job-tracking ===
jobs = {}  # job_id -> { status, progress, message, result, error, file_size, filename, mode, created_at }
jobs_lock = threading.Lock()


def _update_job(job_id: str, **kwargs):
    """Opdater job-status trådsikkert."""
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(kwargs)


def _progress_callback(job_id: str):
    """Returnerer en progress callback-funktion for et givet job."""
    def callback(percent: int, message: str):
        _update_job(job_id, progress=percent, message=message)
    return callback


async def _save_upload(file: UploadFile) -> tuple:
    """
    Gem uploadet fil og returner (file_path, file_size).
    Streamer til disk for at undgå at loade hele filen i hukommelsen.
    """
    if not file.filename.endswith(".xml"):
        raise HTTPException(400, "Kun XML-filer er tilladt")

    job_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")

    # Stream til disk i chunks for at håndtere store filer
    file_size = 0
    chunk_size = 8 * 1024 * 1024  # 8 MB chunks

    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                f.close()
                os.remove(file_path)
                raise HTTPException(
                    400,
                    f"Filen er for stor ({file_size / (1024*1024*1024):.2f} GB). "
                    f"Maksimum er {MAX_FILE_SIZE / (1024*1024*1024):.0f} GB.",
                )
            f.write(chunk)

    if file_size == 0:
        os.remove(file_path)
        raise HTTPException(400, "Filen er tom")

    return file_path, file_size


def _cleanup(file_path: str):
    """Slet uploadet fil."""
    if os.path.exists(file_path):
        os.remove(file_path)


# === Baggrundsjob-funktioner ===

def _run_validate_job(job_id: str, file_path: str, saft_version: Optional[str], filename: str):
    """Kør validering i baggrundstråd."""
    try:
        _update_job(job_id, status="processing", progress=5, message="Starter validering...")
        report = generate_report(file_path, saft_version)
        result = {
            "type": "validation",
            "filename": filename,
            "saft_version": report.get("saft_version", "ukendt"),
            "summary": report["summary"],
            "sections": report["sections"],
            "errors": report["errors"],
            "warnings": report["warnings"],
        }
        _update_job(job_id, status="completed", progress=100, message="Validering færdig", result=result)
    except Exception as e:
        logger.error(f"Job {job_id} fejlede: {e}")
        _update_job(job_id, status="failed", progress=100, message=str(e), error=str(e))
    finally:
        _cleanup(file_path)


def _run_analyze_job(job_id: str, file_path: str, filename: str):
    """Kør analytics i baggrundstråd."""
    try:
        _update_job(job_id, status="processing", progress=5, message="Starter analyse...")
        report = analyze_file(file_path)
        if report is None:
            _update_job(job_id, status="failed", progress=100, message="Kunne ikke parse SAF-T filen", error="Parse fejl")
        else:
            result = {
                "type": "analytics",
                "filename": filename,
                **report,
            }
            _update_job(job_id, status="completed", progress=100, message="Analyse færdig", result=result)
    except Exception as e:
        logger.error(f"Job {job_id} fejlede: {e}")
        _update_job(job_id, status="failed", progress=100, message=str(e), error=str(e))
    finally:
        _cleanup(file_path)


def _run_validate_and_analyze_job(job_id: str, file_path: str, saft_version: Optional[str], filename: str):
    """Kør både validering og analytics i baggrundstråd."""
    try:
        _update_job(job_id, status="processing", progress=5, message="Starter validering...")

        # Validering
        validation = generate_report(file_path, saft_version)
        _update_job(job_id, progress=40, message="Validering færdig — starter analyse...")

        # Analytics
        analytics = analyze_file(file_path)
        _update_job(job_id, progress=90, message="Analyse færdig — samler resultater...")

        result = {
            "type": "full",
            "filename": filename,
            "validation": {
                "saft_version": validation.get("saft_version", "ukendt"),
                "summary": validation["summary"],
                "sections": validation["sections"],
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            },
            "analytics": analytics,
        }
        _update_job(job_id, status="completed", progress=100, message="Validering og analyse færdig", result=result)
    except Exception as e:
        logger.error(f"Job {job_id} fejlede: {e}")
        _update_job(job_id, status="failed", progress=100, message=str(e), error=str(e))
    finally:
        _cleanup(file_path)


# === Endpoints ===

@app.get("/", response_class=HTMLResponse)
def index(username: str = Depends(verify_credentials)):
    """Serve frontend."""
    template_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(template_path, "r") as f:
        return f.read()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SAF-T Validator & Analytics"}


@app.post("/api/validate")
async def validate(
    file: UploadFile = File(...),
    version: Optional[str] = Form(None),
    username: str = Depends(verify_credentials),
):
    """Validér en SAF-T fil. Store filer behandles asynkront."""
    file_path, file_size = await _save_upload(file)
    saft_version = version if version in ("1.0", "2.0") else None

    # Store filer: kør i baggrunden
    if file_size >= ASYNC_THRESHOLD:
        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {
                "status": "queued",
                "progress": 0,
                "message": "Job er i kø...",
                "result": None,
                "error": None,
                "file_size": file_size,
                "filename": file.filename,
                "mode": "validate",
                "created_at": time.time(),
            }
        thread = threading.Thread(
            target=_run_validate_job,
            args=(job_id, file_path, saft_version, file.filename),
            daemon=True,
        )
        thread.start()
        return {
            "async": True,
            "job_id": job_id,
            "file_size": file_size,
            "message": f"Filen er {file_size / (1024*1024):.1f} MB — behandles i baggrunden.",
        }

    # Små filer: synkron behandling (som hidtil)
    try:
        report = generate_report(file_path, saft_version)
        return {
            "type": "validation",
            "filename": file.filename,
            "saft_version": report.get("saft_version", "ukendt"),
            "summary": report["summary"],
            "sections": report["sections"],
            "errors": report["errors"],
            "warnings": report["warnings"],
        }
    finally:
        _cleanup(file_path)


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    username: str = Depends(verify_credentials),
):
    """Kør 103 momsanalyser på en SAF-T fil. Store filer behandles asynkront."""
    file_path, file_size = await _save_upload(file)

    # Store filer: kør i baggrunden
    if file_size >= ASYNC_THRESHOLD:
        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {
                "status": "queued",
                "progress": 0,
                "message": "Job er i kø...",
                "result": None,
                "error": None,
                "file_size": file_size,
                "filename": file.filename,
                "mode": "analyze",
                "created_at": time.time(),
            }
        thread = threading.Thread(
            target=_run_analyze_job,
            args=(job_id, file_path, file.filename),
            daemon=True,
        )
        thread.start()
        return {
            "async": True,
            "job_id": job_id,
            "file_size": file_size,
            "message": f"Filen er {file_size / (1024*1024):.1f} MB — behandles i baggrunden.",
        }

    # Små filer: synkron behandling
    try:
        report = analyze_file(file_path)
        if report is None:
            raise HTTPException(400, "Kunne ikke parse SAF-T filen")
        return {
            "type": "analytics",
            "filename": file.filename,
            **report,
        }
    finally:
        _cleanup(file_path)


@app.post("/api/validate-and-analyze")
async def validate_and_analyze(
    file: UploadFile = File(...),
    version: Optional[str] = Form(None),
    username: str = Depends(verify_credentials),
):
    """Kør både validering og analytics i ét kald. Store filer behandles asynkront."""
    file_path, file_size = await _save_upload(file)
    saft_version = version if version in ("1.0", "2.0") else None

    # Store filer: kør i baggrunden
    if file_size >= ASYNC_THRESHOLD:
        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {
                "status": "queued",
                "progress": 0,
                "message": "Job er i kø...",
                "result": None,
                "error": None,
                "file_size": file_size,
                "filename": file.filename,
                "mode": "validate-and-analyze",
                "created_at": time.time(),
            }
        thread = threading.Thread(
            target=_run_validate_and_analyze_job,
            args=(job_id, file_path, saft_version, file.filename),
            daemon=True,
        )
        thread.start()
        return {
            "async": True,
            "job_id": job_id,
            "file_size": file_size,
            "message": f"Filen er {file_size / (1024*1024):.1f} MB — behandles i baggrunden.",
        }

    # Små filer: synkron behandling
    try:
        # Validering
        validation = generate_report(file_path, saft_version)

        # Analytics
        analytics = analyze_file(file_path)

        return {
            "type": "full",
            "filename": file.filename,
            "validation": {
                "saft_version": validation.get("saft_version", "ukendt"),
                "summary": validation["summary"],
                "sections": validation["sections"],
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            },
            "analytics": analytics,
        }
    finally:
        _cleanup(file_path)


@app.get("/api/status/{job_id}")
async def job_status(
    job_id: str,
    username: str = Depends(verify_credentials),
):
    """Hent status og fremskridt for et baggrundsjob."""
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        raise HTTPException(404, "Job ikke fundet")

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "file_size": job.get("file_size", 0),
        "filename": job.get("filename", ""),
        "mode": job.get("mode", ""),
    }


@app.get("/api/result/{job_id}")
async def job_result(
    job_id: str,
    username: str = Depends(verify_credentials),
):
    """Hent resultatet af et fuldført baggrundsjob."""
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        raise HTTPException(404, "Job ikke fundet")

    if job["status"] == "failed":
        raise HTTPException(400, job.get("error", "Job fejlede"))

    if job["status"] != "completed":
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "message": "Job er ikke færdigt endnu. Brug /api/status/{job_id} til at følge fremskridt.",
        }

    result = job["result"]

    # Ryd op: fjern fuldførte jobs efter resultat er hentet
    with jobs_lock:
        if job_id in jobs:
            del jobs[job_id]

    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
