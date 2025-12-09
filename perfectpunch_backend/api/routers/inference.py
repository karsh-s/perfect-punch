from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from perfectpunch_backend.services.inference import PunchInferenceService

router = APIRouter()


class InferenceRequest(BaseModel):
    session_id: str
    video_path: str
    frames: List[int] = []


@router.post("/punch-classify", tags=["inference"] )
async def classify_punch(req: InferenceRequest):
    """Run punch classification on a video path (stubbed). Returns predictions."""
    svc = PunchInferenceService()
    try:
        preds = svc.classify_video(req.video_path, req.frames)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"session_id": req.session_id, "predictions": preds}
