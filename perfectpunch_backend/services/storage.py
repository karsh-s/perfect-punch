import os
from pathlib import Path
from fastapi import UploadFile

STORAGE_DIR = Path("./uploads")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


async def save_uploaded_video(file: UploadFile) -> str:
    """Save uploaded file to local storage (simple stub).

    Returns the saved file path as a string.
    """
    dest = STORAGE_DIR / file.filename
    with dest.open("wb") as f:
        content = await file.read()
        f.write(content)
    return str(dest.resolve())
