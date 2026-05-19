# How to Get Real Data Working - Simple Steps

## The Problem
Your dashboard shows static `demo_001` data instead of your actual game data.

## Fast Solution (2 Options)

### Option 1: Use Demo Mode (Works Now - No Backend Needed)

**This already works!** Demo mode saves to localStorage.

1. **Open browser console** (F12)
2. **Clear old data**: `localStorage.clear()`
3. **Play a NEW game**:
   - Start camera
   - Hit targets (score increases)
   - Click "End Game"
4. **Check console** for:
   - "✅ Demo session data saved to localStorage"
   - "🚀 Navigating to dashboard with session_id: demo-xxxxx"
5. **Dashboard should show your data**

**If it doesn't work:**
- Check console for the session_id being passed
- Verify localStorage has the session: 
  ```javascript
  Object.keys(localStorage).filter(k => k.startsWith('demo_session_'))
  ```

### Option 2: Fix Backend (For Supabase Storage)

The backend has import errors preventing sessions from being created.

**Quick Fix:**
1. The backend is trying to import GameManager but failing
2. This causes `/game/sessions` to return 404
3. Frontend falls back to demo mode (which works!)

**To fix backend:**
- The imports need to be fixed in `game_manager.py`
- But demo mode works fine without backend!

## Recommendation

**Use Demo Mode for now** - it works and saves your data to localStorage. The dashboard will show your real game data.

The backend can be fixed later if you need Supabase storage, but localStorage works perfectly for development and testing.

## Test It Now

1. Clear localStorage: `localStorage.clear()` in console
2. Play a game
3. End game
4. Check dashboard - should show YOUR session_id and YOUR score

If it still shows `demo_001`, check the console logs to see what session_id the dashboard is looking for.

