# Perfect Punch - Setup Guide

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- conda (Miniconda/Anaconda)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/gt-big-data/perfect-punch.git
cd perfect-punch
```

### 2. Backend Setup

Create and activate a Conda environment:
```bash
conda create -n perfect-punch-env python=3.9
conda activate perfect-punch-env
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Frontend Setup

Install Node dependencies:
```bash
npm install
```

### 4. Environment Configuration

Copy `.env.example` to `.env` and update with your settings:
```bash
cp .env.example .env
```

### 5. Run the Application

**Terminal 1 - Backend:**
```bash
conda activate perfect-punch-env
uvicorn perfectpunch_backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

Open your browser to `http://localhost:5174/` (or the port shown in terminal output)

## Usage

1. Click "Start Punch Analysis" on the landing page
2. Allow camera permissions when prompted
3. Complete the calibration phase
4. Perform 30-second punch analysis
5. View your metrics on the dashboard

## Project Structure

```
perfect-punch/
├── perfectpunch_backend/    # FastAPI backend
│   ├── main.py             # API server
│   ├── main_python_analysis.py  # Punch detection engine
│   ├── models/             # ML models
│   └── ...
├── src/                     # React frontend
│   ├── pages/              # Page components
│   ├── components/         # UI components
│   └── ...
├── public/                  # Static files
├── requirements.txt         # Python dependencies
├── package.json            # Node dependencies
└── ...
```

## Tech Stack

**Backend:**
- FastAPI
- MediaPipe (pose detection)
- PyTorch (punch classification)
- OpenCV (camera)

**Frontend:**
- React
- TypeScript
- Vite
- Recharts

## Troubleshooting

### Camera not working
- Grant camera permissions in system settings
- macOS: System Preferences > Security & Privacy > Camera

### Port already in use
- Backend: `lsof -i :8000` to find process using port 8000
- Frontend: The dev server will automatically try alternate ports (5174, 5175, etc.)

### Dependencies not installing
- Clear pip cache: `pip cache purge`
- Reinstall: `pip install --upgrade -r requirements.txt`

### ModuleNotFoundError with Python
- Verify conda environment is activated: `conda activate perfect-punch-env`
- Reinstall packages: `pip install -r requirements.txt`

## Development

### Adding a Python package
```bash
conda activate perfect-punch-env
pip install <package_name>
# Update requirements.txt with the new package name (without version)
echo "<package_name>" >> requirements.txt
```

### Adding a Node package
```bash
npm install <package_name>
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Test locally
4. Submit a pull request

## License

Proprietary - All rights reserved
