from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.game.game_manager import game_manager
from src.auth.auth import get_current_user
from supabase import create_client
from pydantic import BaseModel
import os
import json

# ----------------------
# Supabase Setup
# ----------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ Supabase environment variables not set! Add them to .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

SESSIONS_TABLE = "sessions"  # Make sure this exists in Supabase


# ----------------------
# FastAPI Setup
# ----------------------
app = FastAPI()

# CORS (keep your existing version if you already had one)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------
# WebSocket Connection Manager
# ----------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()


# ----------------------
# API ROUTES
# ----------------------

@app.post("/api/game/start")
async def start_game(user = Depends(get_current_user)):
    """Start a new game session"""
    session = game_manager.create_session(user.id)
    
    return {
        "session_id": session.session_id,
        "max_duration": session.max_duration,
        "initial_target": {
            "x": session.current_target.center_x,
            "y": session.current_target.center_y,
            "type": session.current_target.punch_type,
            "radius": session.current_target.radius
        }
    }


@app.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()

            # Handle punch
            if data["type"] == "punch_detected":
                result = await game_manager.validate_punch(
                    session_id,
                    data["landmark_data"],
                    data["detected_punch"]
                )
                await manager.send_message(session_id, {
                    "type": "punch_result",
                    "data": result
                })

            # Handle live stats request
            elif data["type"] == "get_stats":
                stats = game_manager.get_session_stats(session_id)
                await manager.send_message(session_id, {
                    "type": "stats_update",
                    "data": stats
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        game_manager.end_session(session_id)


@app.get("/api/game/{session_id}/stats")
async def get_game_stats(session_id: str, user = Depends(get_current_user)):
    """Return current game statistics (from memory)"""
    stats = game_manager.get_session_stats(session_id)
    if not stats:
        return {"error": "Session not found"}
    return stats


@app.post("/api/game/{session_id}/end")
async def end_game(session_id: str, user = Depends(get_current_user)):
    """
    End game session and return final stats.
    ALSO saves session data to Supabase.
    """
    stats = game_manager.end_session(session_id)
    if not stats:
        return {"error": "Session not found"}

    # ----------------------
    # Persist to Supabase
    # ----------------------
    try:
        supabase.table(SESSIONS_TABLE).insert({
            "user_id": user.id,
            "session_id": session_id,
            "session_data": stats,  # JSON stored directly
        }).execute()

        print(f"💾 Saved session {session_id} for user {user.id}")
    except Exception as e:
        print("❌ Failed to save session to Supabase:", e)

    return stats


@app.get("/api/game/latest")
async def get_latest_game(user = Depends(get_current_user)):
    """
    Retrieve the most recent completed session for the current user.
    This is the endpoint your React Dashboard should fetch.
    """
    try:
        response = (
            supabase.table(SESSIONS_TABLE)
            .select("session_data, session_id, created_at")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return {"error": "No sessions found"}

        latest = response.data[0]
        return {
            "session_id": latest["session_id"],
            "data": latest["session_data"],
            "timestamp": latest["created_at"],
        }

    except Exception as e:
        print("❌ Error fetching latest session:", e)
        return {"error": "Could not fetch latest session"}
