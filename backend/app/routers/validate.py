"""
Valideringsroute — porter eksisterende SAF-T Validator logik til FastAPI.
"""

import os
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

# Fix import sti for validator modulet
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from validator.report import generate_report

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/api/validate")
async def validate(
    file: UploadFile = File(...),
    version: Optional[str] = Form(None),
):
    """Validér en SAF-T fil mod XSD-skema og forretningsregler."""
    if not file.filename or not file.filename.endswith(".xml"):
        raise HTTPException(400, "Kun XML-filer er tilladt (.xml)")

    # Gem fil midlertidigt
    job_id = str(uuid.uuid4())[:8]
    tmp_path = os.path.join(tempfile.gettempdir(), f"saft_{job_id}.xml")

    try:
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(400, "Filen er tom")
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                400,
                f"Filen er for stor ({len(content) / (1024*1024):.1f} MB). "
                f"Maksimum er {MAX_FILE_SIZE / (1024*1024):.0f} MB.",
            )

        with open(tmp_path, "wb") as f:
            f.write(content)

        # Validér version
        saft_version = version if version in ("1.0", "2.0") else None

        # Kør validering
        report = generate_report(tmp_path, saft_version)

        return {
            "job_id": job_id,
            "filename": file.filename,
            "saft_version": report.get("saft_version", "ukendt"),
            "summary": report["summary"],
            "sections": report["sections"],
            "errors": report["errors"],
            "warnings": report["warnings"],
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
