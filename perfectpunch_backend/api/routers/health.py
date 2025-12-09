from fastapi import APIRouter

router = APIRouter()


@router.get("/ping", tags=["health"])
def ping():
    """Simple health check"""
    return {"status": "ok"}
