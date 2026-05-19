# How to Start the Backend Server

The backend server needs to be running for the dashboard to show real session data.

## Quick Start

1. **Activate your virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Navigate to the backend directory:**
   ```bash
   cd perfectpunch_backend
   ```

3. **Start the server:**
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

   Or use the provided script:
   ```bash
   ./start_backend.sh
   ```

## Alternative: Start from project root

If you're in the project root:
```bash
source venv/bin/activate
python -m uvicorn perfectpunch_backend.main:app --reload --host 127.0.0.1 --port 8000
```

## Verify it's running

Once started, you should see:
- Server running at `http://127.0.0.1:8000`
- API docs at `http://127.0.0.1:8000/docs`

## Note

The camera will work in "demo mode" even without the backend, but the dashboard will only show real session data when the backend is running.

