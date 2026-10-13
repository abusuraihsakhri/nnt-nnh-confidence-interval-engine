"""REST API for the NNT/NNH calculator and legacy demonstration audit."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StrictInt

from nnt_calc import calculate_metrics
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")
ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(
    title="NNT / NNH Confidence Interval Engine",
    description="Independent-binomial NNT/NNH with Newcombe–Wilson score intervals; legacy audit is demonstrative only.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    query: str


class NNTRequest(BaseModel):
    control_events: StrictInt
    control_total: StrictInt
    treatment_events: StrictInt
    treatment_total: StrictInt
    confidence_level: float = 0.95


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "index.html")


@app.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(ROOT / "app.js", media_type="text/javascript")


@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "service": "nnt-nnh-confidence-interval-engine",
        "audit_configured": bool(os.getenv("AUDIT_SECRET_KEY")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()) if os.getenv("AUDIT_SECRET_KEY") else 0,
        "system_status": "NOMINAL",
    }


@app.post("/api/nnt")
def api_nnt(payload: NNTRequest):
    try:
        return calculate_metrics(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
        return dossier.to_dict()
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        return {"response": supervisor.query_supervisory_chat(req.query)}
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    if not os.getenv("AUDIT_SECRET_KEY"):
        raise HTTPException(status_code=503, detail="Legacy audit system not configured")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
