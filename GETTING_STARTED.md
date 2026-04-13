# Getting Started - Documentation Guide

This document helps you find the right guide for your needs.

## 🎯 I'm a New User - Where Do I Start?

### **→ READ THIS FIRST:** `README_PPerfectPunchBackend.md`

This is your **main setup guide**. It covers:

1. **Quick Start (3 steps)** - Get running in 5 minutes
2. **Complete Setup** - Step-by-step for beginners
3. **How to Create Conda Environment** - With Python 3.9
4. **How to Install Dependencies** - `pip install -r requirements.txt`
5. **How to Run Backend** - Start the FastAPI server
6. **How to Run Frontend** - Start the React app
7. **Verification Steps** - Confirm everything works
8. **Troubleshooting** - Fix common problems
9. **Project Architecture** - Understand the structure

**Time to read:** 15-20 minutes
**Result:** You'll have a fully working local environment

---

## 📚 Quick Navigation

### For Setup & Installation
| Task | File | Section |
|------|------|---------|
| **Quick Start (3 steps)** | `README_PPerfectPunchBackend.md` | Quick Start |
| **Complete new user setup** | `README_PPerfectPunchBackend.md` | Complete Setup Instructions |
| **Create Conda environment** | `README_PPerfectPunchBackend.md` | Step 3: Create Virtual Environment |
| **Install Python packages** | `README_PPerfectPunchBackend.md` | Step 4: Install Dependencies |
| **Run backend server** | `README_PPerfectPunchBackend.md` | Step 6: Run Full Application |
| **Run frontend** | `README_PPerfectPunchBackend.md` | Step 6: Run Full Application |
| **Fix dependency issues** | `README_PPerfectPunchBackend.md` | Troubleshooting |

### For Running the Application
| Task | File | Section |
|------|------|---------|
| **Start backend** | `BACKEND_START.md` | Quick Start |
| **Check if backend works** | `BACKEND_START.md` | Verify it's running |
| **View API documentation** | Browser | `http://localhost:8000/docs` |
| **Use the application** | `README_PPerfectPunchBackend.md` | Using the Application |

### For Understanding the System
| Task | File | Section |
|------|------|---------|
| **Project structure** | `README_PPerfectPunchBackend.md` | Architecture |
| **Tech stack** | `SETUP.md` | Tech Stack |
| **What gets installed** | `README_PPerfectPunchBackend.md` | Step 2: Install Python Dependencies |
| **How it all works** | `README_PPerfectPunchBackend.md` | Architecture |

### For Dashboard (After Running)
| Task | File |
|------|------|
| **Dashboard stats explanation** | `DASHBOARD_STATS_GUIDE.md` |
| **Understanding metrics** | `DASHBOARD_STATS_GUIDE.md` |
| **Testing the dashboard** | `WHEN_READY_TO_TEST.md` |

---

## 📋 The 3-Step Quick Start (From README_PPerfectPunchBackend.md)

### Step 1: Create Conda Environment
```bash
conda create -n perfect-punch-env python=3.9
conda activate perfect-punch-env
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Start Both Servers

**Terminal 1 - Backend:**
```bash
python -m uvicorn perfectpunch_backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

Then visit: `http://localhost:5173`

---

## 🔍 Common Questions Answered

### "How do I set up the virtual environment?"
→ `README_PPerfectPunchBackend.md` - Step 1: Create Conda Environment

### "What packages do I need to install?"
→ `README_PPerfectPunchBackend.md` - Step 2: Install Python Dependencies
→ Or just run: `pip install -r requirements.txt`

### "How do I start the backend server?"
→ `BACKEND_START.md` - Quick Start section
→ Or: `python -m uvicorn perfectpunch_backend.main:app --reload --port 8000`

### "How do I start the frontend?"
→ `README_PPerfectPunchBackend.md` - Step 6: Run Full Application
→ Or: `npm run dev`

### "Is my setup working?"
→ `README_PPerfectPunchBackend.md` - Verify Everything Works section
→ Or: `curl http://127.0.0.1:8000/health`

### "I'm getting errors. How do I fix them?"
→ `README_PPerfectPunchBackend.md` - Common Issues & Solutions

### "What should I do after setup?"
→ `README_PPerfectPunchBackend.md` - Using the Application

---

## 📁 File Descriptions

### `README_PPerfectPunchBackend.md` ⭐ MAIN GUIDE
- **Purpose**: Complete setup guide for new users
- **Length**: ~650 lines (comprehensive)
- **What it covers**:
  - Prerequisites
  - Quick start (3 steps)
  - Complete setup for beginners
  - Virtual environment creation
  - Dependency installation
  - Running backend & frontend
  - Architecture overview
  - Troubleshooting
  - Development workflow

### `SETUP.md`
- **Purpose**: General project setup overview
- **What it covers**:
  - Prerequisites checklist
  - Repository clone
  - Backend setup (brief)
  - Frontend setup
  - Environment configuration
  - How to run application
  - Project structure
  - Tech stack
  - Troubleshooting

### `BACKEND_START.md`
- **Purpose**: Backend-specific startup instructions
- **What it covers**:
  - Different ways to start backend
  - Verification commands
  - API docs location
  - Note about demo mode vs backend

### `DASHBOARD_STATS_GUIDE.md`
- **Purpose**: Understanding dashboard metrics
- **What it covers**:
  - All metrics explained
  - Calculation formulas
  - Expected values
  - Units reference
  - Debugging guide

### `WHEN_READY_TO_TEST.md`
- **Purpose**: Step-by-step testing the dashboard
- **What it covers**:
  - Current status checklist
  - Step-by-step instructions
  - Expected console logs
  - What to verify on dashboard
  - Troubleshooting
  - Success criteria

---

## 🚀 Recommended Reading Order (New User)

1. **START HERE**: `README_PPerfectPunchBackend.md`
   - Read sections: "Quick Start", "Prerequisites", "Complete Setup Instructions"
   - Time: 15 minutes

2. **FOLLOW UP**: `SETUP.md` (optional)
   - Read sections: "Prerequisites", "Project Structure"
   - Time: 5 minutes

3. **FOR BACKEND**: `BACKEND_START.md` (optional)
   - Reference when starting backend server
   - Time: 2 minutes

4. **FOR DASHBOARD**: `DASHBOARD_STATS_GUIDE.md` (after running)
   - Understand what the metrics mean
   - Time: 10 minutes

**Total time:** 30-40 minutes from clone to running application

---

## ✅ Success Indicators

You've successfully set up if:

✅ Backend server running at `http://127.0.0.1:8000`
✅ Frontend running at `http://localhost:5173`
✅ Can see "Welcome back" message on landing page
✅ Can click "Start Punch Analysis" button
✅ Camera window opens when you click the button
✅ Analysis completes and shows dashboard
✅ Dashboard displays metrics and charts

---

## 🆘 Need Help?

1. **Check troubleshooting section**
   - `README_PPerfectPunchBackend.md` → Common Issues & Solutions

2. **Check error in console**
   - Most errors are explained in troubleshooting

3. **Verify prerequisites**
   - Python 3.9
   - Conda installed
   - Node.js installed
   - Camera available

4. **Run verification steps**
   - See `README_PPerfectPunchBackend.md` → Verify Everything Works

---

## 📞 Quick Reference Commands

```bash
# Create environment
conda create -n perfect-punch-env python=3.9
conda activate perfect-punch-env

# Install packages
pip install -r requirements.txt

# Start backend
python -m uvicorn perfectpunch_backend.main:app --reload --host 127.0.0.1 --port 8000

# Start frontend
npm run dev

# Verify backend
curl http://127.0.0.1:8000/health

# Check environment
conda info --envs
python --version
```

---

**Questions? Confused? Read `README_PPerfectPunchBackend.md` first!** ⭐
