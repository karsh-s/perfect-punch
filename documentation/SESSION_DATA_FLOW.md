# Session Data Flow - How New Data is Displayed

## Overview
Each camera session now automatically saves data to Supabase and the dashboard fetches and displays new data after each session.

## How It Works

### 1. **During Game Session**
- User plays the game (with or without backend)
- All punch attempts, targets hit, and timing data are tracked in real-time

### 2. **When Session Ends**
- **With Backend**: When you click "End Game", the backend saves all session data to Supabase automatically
- **Demo Mode** (no backend): Session data is saved to localStorage and can be retrieved by the dashboard

### 3. **Dashboard Display**
- Dashboard first checks localStorage for demo sessions (if session_id starts with 'demo-')
- Then checks Supabase for saved sessions
- Finally falls back to static sample data if neither is available
- **Each session gets its own unique session_id**, so each game session will show different data

## Data Storage

### Supabase Table: `game_sessions`
The backend automatically saves to Supabase with this structure:
- `session_id`: Unique ID for each session
- `user_id`: User who played
- `start_time` / `end_time`: Session timestamps
- `score`, `accuracy`, `total_punches`: Summary stats
- `punch_attempts`: Array of all punch attempts with details
- `targets_hit` / `targets_spawned`: Target statistics

### LocalStorage (Demo Mode)
- Key format: `demo_session_{session_id}`
- Stores formatted dashboard data for offline viewing

## To See New Data After Each Session:

1. **Make sure backend is running** (for Supabase saving):
   ```bash
   ./start_backend.sh
   ```

2. **Play a session** - The game will track all your punches, targets, and timing

3. **Click "End Game"** - This triggers:
   - Backend saves to Supabase (if connected)
   - Dashboard navigation with session_id

4. **Dashboard loads** - It will:
   - Fetch the session data using the session_id
   - Calculate all metrics (accuracy, reaction times, etc.)
   - Display your actual session data

## Important Notes:

- **Each session is unique** - Every time you play, you get a new session_id
- **Data persists** - Saved sessions in Supabase can be viewed later
- **Demo mode works** - Even without backend, data is saved locally and dashboard will show it
- **Real-time updates** - The dashboard reflects the actual game you just played

## Troubleshooting:

If you're seeing the same data repeatedly:
1. Check if backend is running: `http://localhost:8000/health`
2. Check browser console for any errors when ending game
3. Verify Supabase credentials are set in backend `.env`:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
4. Check that `game_sessions` table exists in Supabase

