PerfectPunch Backend (minimal starter)

This folder adds a modular FastAPI backend scaffold for the PerfectPunch project.

Files added:
- perfectpunch_backend/: package with routers and service stubs
  - api/routers: health, upload, inference, analysis
  - services: storage, inference, analysis
  - celery_app.py: placeholder for background tasks
- requirements.txt: Python dependencies for the backend

How to run (local dev):

1. Create a virtualenv and install deps

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Start the FastAPI app with uvicorn

   uvicorn main:app --reload

Notes and next steps:
- Replace inference service with real PyTorch model loading and MediaPipe pose extraction.
- Integrate Celery with Redis and move heavy tasks (video preprocessing, segmentation) to background workers.
- Add authentication (Firebase) and persistence (Postgres/Supabase) for sessions and labeled data.
- Hook up Taipy dashboard for visualization and Gemini/LangChain for LLM-driven feedback.
