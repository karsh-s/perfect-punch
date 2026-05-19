# Where Data is Saved & How Dashboard Gets It

## Data Storage Locations

### 1. **With Backend Running** (Your Current Setup)
✅ **Supabase Database** (Primary Storage)
- Location: Cloud database (Supabase)
- Table: `game_sessions`
- When: Automatically when you click "End Game"
- What's saved:
  - Session ID
  - Score, accuracy, total punches
  - All punch attempts with details
  - Targets hit/spawned
  - Reaction times
  - Timestamps

✅ **In-Memory** (Temporary)
- Location: Backend server memory
- When: While game is active
- What: Current game state (score, targets, etc.)
- Note: Lost when backend restarts

### 2. **Without Backend** (Demo Mode)
✅ **Browser localStorage** (Fallback)
- Location: Your browser's local storage
- When: When you click "End Game" in demo mode
- Key format: `demo_session_{session_id}`
- What's saved: Same data structure as Supabase

## How Dashboard Gets Data

### Flow When Backend is Running:

1. **You play game** → Backend tracks everything in memory
2. **You click "End Game"** → Backend saves to Supabase
3. **Dashboard loads** → Calls `/session/latest?session_id={your_session_id}`
4. **Backend fetches** → Gets data from Supabase
5. **Dashboard displays** → Shows your actual game data

### Flow Without Backend (Demo Mode):

1. **You play game** → Frontend tracks in state
2. **You click "End Game"** → Frontend saves to localStorage
3. **Dashboard loads** → Reads from localStorage
4. **Dashboard displays** → Shows your demo session data

## Will Your Dashboard Metrics Change?

### ✅ YES, if:
- You play a new game session (each session has unique ID)
- Backend is running and saves to Supabase
- Dashboard fetches the correct session_id
- Data is actually saved (check console logs)

### ❌ NO, if:
- You're viewing the same old session
- Backend failed to save (check console for errors)
- Dashboard is loading cached/old data
- Supabase connection failed

## How to Verify Data is Saving

### Check Backend Logs:
Look for these messages in the backend terminal:
```
Session {session_id} saved to Supabase
```

### Check Browser Console:
Look for:
```
✅ Demo session data saved to localStorage
📊 Score saved: X, Targets hit: Y
```

### Check Supabase (if configured):
1. Go to your Supabase dashboard
2. Check `game_sessions` table
3. See your saved sessions

### Check localStorage (demo mode):
In browser console:
```javascript
// See all saved sessions
Object.keys(localStorage).filter(k => k.startsWith('demo_session_'))

// See latest session data
const keys = Object.keys(localStorage).filter(k => k.startsWith('demo_session_'));
const latest = keys.sort().reverse()[0];
console.log(JSON.parse(localStorage.getItem(latest)));
```

## Current Status

✅ **Backend is running** → Will save to Supabase  
✅ **Supabase credentials set** → Connection should work  
✅ **Dashboard configured** → Will fetch from Supabase or localStorage

## What Happens When You Play Now:

1. **Start game** → Backend creates session
2. **Play game** → Backend tracks via WebSocket
3. **Hit targets** → Backend updates score in memory
4. **End game** → Backend saves to Supabase ✅
5. **Dashboard** → Fetches from Supabase ✅
6. **Metrics change** → Shows your new game data ✅

**Your dashboard metrics WILL change** when you play a new game session!

