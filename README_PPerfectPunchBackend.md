# PerfectPunch Backend Setup Guide

Complete guide for setting up the virtual environment, installing dependencies, and running the backend server.

## Overview

The PerfectPunch backend is a FastAPI server that handles:
- Camera initialization and video processing
- MediaPipe pose detection
- PyTorch punch classification (3D CNN model)
- Session metrics collection and analysis
- Dashboard data serving

## Prerequisites

- **Python 3.9** (required for compatibility with our ML models)
- **Conda** (Miniconda or Anaconda)
- **Git**
- **macOS/Linux/Windows** with access to camera

## Quick Start (3 Steps)

### Step 1: Create Conda Environment

```bash
# Create a new conda environment with Python 3.9
conda create -n perfect-punch-env python=3.9

# Activate the environment
conda activate perfect-punch-env
```

### Step 2: Install Python Dependencies

```bash
# Make sure you're in the project root directory
cd perfect-punch

# Install all required packages
pip install -r requirements.txt
```

**What gets installed:**
- FastAPI (web framework)
- Uvicorn (server)
- MediaPipe (pose detection)
- PyTorch 2.8.0 (punch classification)
- OpenCV (camera)
- Torch vision utilities
- And more (see `requirements.txt` for full list)

### Step 3: Start the Backend Server

```bash
# Make sure conda environment is activated
conda activate perfect-punch-env

# Start the backend
python -m uvicorn perfectpunch_backend.main:app --reload --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

✅ **Backend is ready!** Visit `http://127.0.0.1:8000/docs` to see API documentation.

## Complete Setup Instructions (For New Users)

### 1. Install Prerequisites

**macOS:**
```bash
# Install Conda (if not already installed)
# Download from: https://docs.conda.io/en/latest/miniconda.html
# Or use Homebrew:
brew install miniconda
```

**Linux:**
```bash
# Download Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

**Windows:**
- Download Miniconda from: https://docs.conda.io/en/latest/miniconda.html
- Run the installer and follow prompts

### 2. Clone Repository

```bash
git clone https://github.com/gt-big-data/perfect-punch.git
cd perfect-punch
```

### 3. Create Virtual Environment

```bash
# Create conda environment
conda create -n perfect-punch-env python=3.9

# Activate it
conda activate perfect-punch-env
```

Verify it's activated (you should see `(perfect-punch-env)` in your terminal):
```bash
conda info --envs
```

### 4. Install Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt
```

⏳ **This may take 3-5 minutes** (PyTorch and dependencies are large)

Verify installation:
```bash
python -c "import torch; print(torch.__version__)"
# Should print: 2.8.0
```

### 5. Set Up Frontend (in another terminal)

```bash
# DO NOT activate conda environment for Node
# Just use your system Node

npm install
```

### 6. Run the Full Application

**Terminal 1 - Backend:**
```bash
conda activate perfect-punch-env
python -m uvicorn perfectpunch_backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```bash
# Make sure you're in the project root
npm run dev
```

**Terminal 3 (Optional) - Monitor logs:**
```bash
# You can open another terminal to monitor activity
# No need to run anything - just watch the above two terminals
```

Visit `http://localhost:5173` to use the application!

## Architecture

```
perfect-punch/
├── perfectpunch_backend/
│   ├── main.py                    # FastAPI server entry point
│   ├── main_python_analysis.py    # Punch detection engine
│   │   ├── MediaPipe Pose         # Body position detection
│   │   ├── PyTorch 3D CNN         # Punch classification
│   │   └── DefenseGame            # Defense metrics
│   ├── models/
│   │   └── model_state.pt         # Pre-trained 3D CNN weights
│   ├── api/
│   │   └── routers/               # API endpoints
│   ├── services/                  # Business logic
│   └── db/                        # Database utilities
│
├── src/                           # React frontend
│   ├── pages/
│   │   ├── LandingPage.jsx        # Analysis trigger & metrics transform
│   │   └── DashboardPage.jsx      # Results visualization
│   └── components/                # UI components
│
├── requirements.txt               # Python dependencies
├── package.json                   # Node dependencies
├── SETUP.md                       # General setup guide
└── README_PPerfectPunchBackend.md # This file
```

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| FastAPI | Latest | Web framework |
| Uvicorn | Latest | ASGI server |
| MediaPipe | Latest | Pose detection |
| PyTorch | 2.8.0 | Neural networks |
| OpenCV | Latest | Camera/video |
| NumPy | Latest | Array operations |

## Verify Everything Works

### 1. Check Backend is Running

```bash
curl http://127.0.0.1:8000/health
# Should return: {"status":"ok"}
```

### 2. Check API Docs

Visit: `http://127.0.0.1:8000/docs`

You should see Swagger UI with all available endpoints.

### 3. Check Frontend is Running

Visit: `http://localhost:5173`

You should see the Perfect Punch landing page.

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'torch'`

**Solution:**
```bash
# Make sure environment is activated
conda activate perfect-punch-env

# Reinstall PyTorch
pip install torch==2.8.0 torchvision
```

### Issue: `Port 8000 already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use a different port
python -m uvicorn perfectpunch_backend.main:app --port 8001
```

### Issue: `ModuleNotFoundError: No module named 'cv2'`

**Solution:**
```bash
# OpenCV should be in requirements.txt
# If missing, install manually
pip install opencv-python
```

### Issue: Camera not working

**Solution:**
1. Check system permissions (macOS: System Preferences > Security & Privacy > Camera)
2. Ensure no other app is using the camera
3. Try restarting the application

### Issue: `Cannot find conda command`

**Solution:**
```bash
# Initialize conda for your shell
conda init bash  # or zsh, fish, etc.

# Then restart your terminal
```

## Using the Application

Once both servers are running:

1. **Open** `http://localhost:5173`
2. **Click** "Start Punch Analysis"
3. **Allow** camera permissions
4. **Complete** calibration (30 seconds)
5. **Perform** punches in front of camera
6. **View** results on dashboard

## Development Workflow

### Adding a Python Package

```bash
# Activate environment
conda activate perfect-punch-env

# Install package
pip install <package_name>

# Update requirements.txt
pip freeze > requirements.txt
```

### Adding a Node Package

```bash
npm install <package_name>
```

### Making Code Changes

Both servers run with `--reload`, so changes auto-refresh:
- Backend: Changes to Python files trigger reload
- Frontend: Changes to React files trigger hot reload

## Project Structure Details

### Backend Entry Points

**Main API Server:**
- `perfectpunch_backend/main.py` - FastAPI app with routes
- Listens on `http://127.0.0.1:8000`
- Endpoints:
  - `POST /analysis/start` - Runs punch analysis
  - `GET /health` - Server status
  - `GET /session/latest` - Get latest session data

**Analysis Engine:**
- `perfectpunch_backend/main_python_analysis.py`
- Handles:
  - Camera initialization
  - MediaPipe pose detection
  - PyTorch model inference
  - Metrics calculation
  - Session data generation

**Pre-trained Model:**
- `perfectpunch_backend/models/model_state.pt`
- 3D CNN model for punch classification
- Trained on MediaPipe pose sequences
- Classifies: Jab, Hook, Uppercut

### Frontend Entry Points

**Landing Page:**
- `src/pages/LandingPage.jsx`
- Triggers analysis
- Transforms metrics for dashboard
- Routes to dashboard

**Dashboard:**
- `src/pages/DashboardPage.jsx`
- Displays metrics
- Shows charts and statistics
- Uses Recharts for visualization

## Environment Variables

Create `.env` file (or copy from `.env.example`):

```bash
# Optional: Backend configuration
BACKEND_PORT=8000
BACKEND_HOST=127.0.0.1

# Optional: Frontend configuration
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Next Steps

After successful setup:

1. **Test the full pipeline** - Run analysis and check dashboard
2. **Review documentation** - See `DASHBOARD_STATS_GUIDE.md` for metrics details
3. **Check test results** - See `TEST_RESULTS.md` for known working configurations
4. **Explore code** - Review `main_python_analysis.py` to understand the analysis engine

## Troubleshooting

### Conda environment not activating

```bash
# Check what shells conda supports
conda info

# Initialize your shell
conda init zsh  # or bash, fish, etc.

# Restart terminal
```

### Python version mismatch

```bash
# Check installed version
python --version

# Should be 3.9.x
# If not, create environment again with explicit version:
conda create -n perfect-punch-env python=3.9.13
```

### GPU support (optional)

For CUDA GPU acceleration:
```bash
# Install PyTorch with CUDA
conda install pytorch::pytorch torchvision -c pytorch
```

## Getting Help

- Check `SETUP.md` for general setup
- Check `BACKEND_FUNCTIONALITY.md` for API details
- Check console logs for specific errors
- Review test documentation in `TEST_RESULTS.md`

## Notes

- This project uses **Conda** (not venv) for Python environment management
- Python **3.9** is required for PyTorch model compatibility
- Frontend uses **Node.js** separately (not in conda environment)
- Model inference uses **CPU** by default (GPU optional)
- Camera access required for punch detection
