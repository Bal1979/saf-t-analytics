"""
Analytics route — kører 103 momsanalyser på SAF-T data.
"""

import os
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..analytics.engine import run_analytics

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _validate_file_size(content: bytes):
    """Validér at filindhold ikke er tomt og ikke overskrider grænsen."""
    if len(content) == 0:
        raise HTTPException(400, "Filen er tom")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            400,
            f"Filen er for stor ({len(content) / (1024*1024):.1f} MB). "
            f"Maksimum er {MAX_FILE_SIZE / (1024*1024):.0f} MB.",
        )


@router.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """Kør momsanalyse (103 tests) på en SAF-T fil."""
    if not file.filename or not file.filename.endswith(".xml"):
        raise HTTPException(400, "Kun XML-filer er tilladt (.xml)")

    job_id = str(uuid.uuid4())[:8]
    tmp_path = os.path.join(tempfile.gettempdir(), f"saft_analytics_{job_id}.xml")

    try:
        content = await file.read()
        _validate_file_size(content)

        with open(tmp_path, "wb") as f:
            f.write(content)

        report = run_analytics(tmp_path)

        return report.model_dump()

    except HTTPException:
        raise

    except Exception as e:
        return {"error": f"Fejl ved analyse: {str(e)}"}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/api/validate-and-analyze")
async def validate_and_analyze(file: UploadFile = File(...)):
    """Kør både validering og analytics i ét kald."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from validator.report import generate_report

    if not file.filename or not file.filename.endswith(".xml"):
        raise HTTPException(400, "Kun XML-filer er tilladt (.xml)")

    job_id = str(uuid.uuid4())[:8]
    tmp_path = os.path.join(tempfile.gettempdir(), f"saft_combined_{job_id}.xml")

    try:
        content = await file.read()
        _validate_file_size(content)

        with open(tmp_path, "wb") as f:
            f.write(content)

        # Kør begge
        validation_report = generate_report(tmp_path)
        analytics_report = run_analytics(tmp_path)

        return {
            "job_id": job_id,
            "filename": file.filename,
            "validation": {
                "saft_version": validation_report.get("saft_version", "ukendt"),
                "summary": validation_report["summary"],
                "sections": validation_report["sections"],
                "errors": validation_report["errors"],
                "warnings": validation_report["warnings"],
            },
            "analytics": analytics_report.model_dump(),
        }

    except HTTPException:
        raise

    except Exception as e:
        return {"error": f"Fejl: {str(e)}"}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
