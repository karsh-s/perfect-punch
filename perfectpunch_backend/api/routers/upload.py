from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List
from perfectpunch_backend.services.storage import save_uploaded_video

router = APIRouter()


@router.post("/video", tags=["upload"] )
async def upload_video(files: List[UploadFile] = File(...)):
    """Endpoint to upload one or more videos for analysis. Stores files via storage service stub and returns saved paths."""
    saved = []
    for f in files:
        if not f.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail=f"Invalid content type: {f.content_type}")
        path = await save_uploaded_video(f)
        saved.append({"filename": f.filename, "path": path})
    return {"uploaded": saved}
