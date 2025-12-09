from fastapi import APIRouter
from perfectpunch_backend.supabase_client import supabase

router = APIRouter()

@router.get("/stats")
def get_stats():
    response = supabase.table("game_sessions").select("*").order("created_at", desc=True).execute()
    return response.data