"""
SAF-T Validator & Analytics — FastAPI Backend
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import validate, analytics

app = FastAPI(
    title="SAF-T Validator & Analytics",
    description="Validér og analysér danske SAF-T filer med 103 momsanalysetests.",
    version="1.0.0",
)

# CORS — tillad frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # Next.js dev
        "http://127.0.0.1:3000",
        os.environ.get("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(validate.router)
app.include_router(analytics.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SAF-T Validator & Analytics"}
