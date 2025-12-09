from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import existing routers
from perfectpunch_backend.api.routers import health, upload, inference, analysis, game

app = FastAPI(title="PerfectPunch API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(inference.router)
app.include_router(analysis.router)
app.include_router(game.router)  # New game router

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PerfectPunch API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)