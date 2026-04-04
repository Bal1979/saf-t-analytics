#!/usr/bin/env python3
"""
SAF-T Validator & Analytics — FastAPI Backend
"""

import os
import uuid
import secrets
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from validator.report import generate_report
from analytics.engine import analyze_file

app = FastAPI(title="SAF-T Validator & Analytics", version="1.0.0")
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


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _save_upload(file: UploadFile) -> str:
    """Gem uploadet fil og returner stien."""
    if not file.filename.endswith(".xml"):
        raise HTTPException(400, "Kun XML-filer er tilladt")

    job_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(400, "Filen er tom")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            400,
            f"Filen er for stor ({len(content) / (1024*1024):.1f} MB). "
            f"Maksimum er {MAX_FILE_SIZE / (1024*1024):.0f} MB.",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


def _cleanup(file_path: str):
    """Slet uploadet fil."""
    if os.path.exists(file_path):
        os.remove(file_path)


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
    """Validér en SAF-T fil (eksisterende validator-logik)."""
    file_path = await _save_upload(file)
    try:
        saft_version = version if version in ("1.0", "2.0") else None
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
    """Kør 103 momsanalyser på en SAF-T fil."""
    file_path = await _save_upload(file)
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
    """Kør både validering og analytics i ét kald."""
    file_path = await _save_upload(file)
    try:
        # Validering
        saft_version = version if version in ("1.0", "2.0") else None
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
