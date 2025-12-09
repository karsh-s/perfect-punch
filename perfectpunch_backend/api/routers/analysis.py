from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

from perfectpunch_backend.services.analysis import AnalysisService

router = APIRouter()


class AnalysisRequest(BaseModel):
    session_id: str
    metrics: Dict[str, float] = {}


@router.post("/session-report", tags=["analysis"])
async def session_report(req: AnalysisRequest):
    """Generate an analysis report from metrics (stub)."""
    svc = AnalysisService()
    report = svc.generate_report(req.session_id, req.metrics)
    return {"session_id": req.session_id, "report": report}
