from supabase_client import supabase

def save_game_session(data: dict):
    """Save a game session to Supabase."""
    try:
        result = supabase.table("game_sessions").insert(data).execute()
        return result.data
    except Exception as e:
        print(f"Error saving game session to Supabase: {e}")
        raise

def get_game_session(session_id: str):
    """Get a game session from Supabase by session_id."""
    try:
        result = supabase.table("game_sessions").select("*").eq("session_id", session_id).order("end_time", desc=True).limit(1).execute()
        return result.data[0] if result.data and len(result.data) > 0 else None
    except Exception as e:
        print(f"Error getting game session from Supabase: {e}")
        return None

def get_latest_session(user_id: str = None):
    """Get the latest game session from Supabase."""
    try:
        query = supabase.table("game_sessions").select("*").order("end_time", desc=True).limit(1)
        if user_id:
            query = query.eq("user_id", user_id)
        result = query.execute()
        return result.data[0] if result.data and len(result.data) > 0 else None
    except Exception as e:
        print(f"Error getting latest session from Supabase: {e}")
        return None