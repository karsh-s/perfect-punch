from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os, json, time, subprocess
from datetime import datetime

# Load environment
load_dotenv()

app = FastAPI(title="PerfectPunch API")

# ---- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try loading game router
try:
    from .api.routers import game
    from .api.routers.game import game_manager
    app.include_router(game.router)
    GAME_MANAGER_AVAILABLE = True
    print("✅ Game router loaded successfully")
except Exception as e:
    GAME_MANAGER_AVAILABLE = False
    game_manager = None
    print(f"⚠️ Error loading game router: {e}")

# Optional OpenAI setup
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# -----------------------------
#  LOCAL SESSION STORAGE ADDED
# -----------------------------
SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

@app.post("/session/upload")
def upload_session(payload: dict):
    """Save session data coming from run_model.py."""
    filename = f"{SESSIONS_DIR}/session_{int(time.time())}.json"
    with open(filename, "w") as f:
        json.dump(payload, f)
        f.flush()
        os.fsync(f.fileno())
    print(f"💾 Saved session file: {filename}")
    return {"status": "saved", "file": filename}


@app.get("/")
def root():
    return {"status": "backend running 🚀"}


# -----------------------------
#  RUN PUNCH ANALYSIS ENDPOINT
# -----------------------------
@app.post("/analysis/start")
def start_punch_analysis():
    """Start the punch analysis camera session."""
    try:
        print("🎥 Starting punch analysis...")
        
        # Run the main_python_analysis script
        # Use subprocess to run it as a module within the conda environment
        # Set SHOW_DISPLAY=true to enable camera window
        env = os.environ.copy()
        env['SHOW_DISPLAY'] = 'true'
        
        result = subprocess.run(
            ["python", "-m", "perfectpunch_backend.main_python_analysis"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            # Don't capture output so camera window can display
            timeout=120,  # 2 minute timeout
            env=env  # Pass the environment with SHOW_DISPLAY=true
        )
        
        # Check if the script ran successfully
        if result.returncode != 0:
            print(f"❌ Analysis failed with return code {result.returncode}")
            raise HTTPException(status_code=500, detail=f"Analysis failed with return code {result.returncode}")
        
        print("✅ Analysis completed successfully")
        
        # Load and return the results from session_metrics.json
        metrics_file = "session_metrics.json"
        if os.path.exists(metrics_file):
            with open(metrics_file, "r") as f:
                metrics = json.load(f)
            print(f"📊 Loaded metrics from {metrics_file}")
            return {"status": "success", "metrics": metrics}
        else:
            raise HTTPException(status_code=500, detail="session_metrics.json not found")
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Analysis timeout - took too long")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
#  GET ANALYSIS RESULTS ENDPOINT
# -----------------------------
@app.get("/analysis/results")
def get_analysis_results():
    """Get the latest punch analysis results from session_metrics.json."""
    try:
        metrics_file = "session_metrics.json"
        if os.path.exists(metrics_file):
            with open(metrics_file, "r") as f:
                metrics = json.load(f)
            return {"status": "success", "metrics": metrics}
        else:
            return {"status": "no_data", "metrics": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
#  PATCHED /session/latest
# -----------------------------
@app.get("/session/latest")
def get_latest_session(session_id: str = Query(None, description="Optional session ID to fetch")):
    """Return the most recent REAL session in dashboard format."""

    # 1️⃣ FIRST: Try loading local saved session files (this is needed for run_model.py!)
    try:
        files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
        if files:
            latest = max(files, key=lambda x: os.path.getctime(os.path.join(SESSIONS_DIR, x)))
            path = os.path.join(SESSIONS_DIR, latest)

            with open(path) as f:
                session_data = json.load(f)

            # Only accept valid sessions
            if session_data.get("total_punches", 0) > 0:
                print(f"📄 Loaded LOCAL session: {latest}")
                return session_data
    except Exception as e:
        print("⚠️ Error loading local session:", e)

    # If session_id is provided → try Supabase
    if session_id:
        try:
            from perfectpunch_backend.supabase_client import supabase
            
            result = supabase.table("game_sessions").select("*") \
                .eq("session_id", session_id).order("end_time", desc=True).limit(1).execute()

            if result.data:
                saved_session = result.data[0]
            else:
                saved_session = None

            if saved_session:
                print("📄 Loaded Supabase session by session_id")
                return saved_session

        except Exception as e:
            print(f"⚠️ Error fetching from Supabase: {e}")

    # No session_id → try latest Supabase session
    if not session_id:
        try:
            from perfectpunch_backend.services.game_session_service import get_latest_session
            latest = get_latest_session()
            if latest:
                print("📄 Loaded latest Supabase session")
                return latest
        except Exception as e:
            print(f"⚠️ Error fetching latest Supabase session: {e}")

    # Try in-memory game manager sessions
    if session_id and GAME_MANAGER_AVAILABLE and game_manager:
        stats = game_manager.get_session_stats(session_id)
        session = game_manager.get_session(session_id)

        if stats and session:
            print("📄 Loaded in-memory GameManager session")
            return {
                "session_id": session_id,
                "summary": stats,
                "punches": [vars(a) for a in session.punch_attempts]
            }

    # ⚠️ FINAL FALLBACK — static demo (only if everything failed)
    print("⚠️ Falling back to static demo session.")
    return {
        "session_id": "demo_001",
        "timestamp": "2025-11-17T14:00:00Z",
        "summary": {
            "score": 82,
            "avg_velocity": 5.87,
            "avg_reaction_time": 242,
            "accuracy": 93.2,
            "critical_prevention": 63.1,
            "total_punches": 23
        },
        "punch_accuracy": {"jab": 91, "hook": 88, "uppercut": 94},
        "reaction_times": {"jab": 210, "hook": 250, "uppercut": 266},
        "defense": {"blocked": 28, "dodged": 36, "hit": 36},
        "timeline": [
            {"t": 5, "velocity": 6.2, "accuracy": 95},
            {"t": 10, "velocity": 5.8, "accuracy": 93},
            {"t": 15, "velocity": 6.1, "accuracy": 92},
            {"t": 20, "velocity": 5.4, "accuracy": 90},
            {"t": 25, "velocity": 5.1, "accuracy": 88}
        ]
    }


# -----------------------------
# FEEDBACK ROUTE
# -----------------------------
class SessionData(BaseModel):
    summary: dict
    punches: list

@app.post("/session/feedback")
async def generate_feedback(session: SessionData):
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a boxing coach."},
            {"role": "user", "content": f"Analyze this: {session.json()}"}
        ],
        temperature=0.7,
    )

    return {"feedback": response.choices[0].message.content}
