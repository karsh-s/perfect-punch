# Quick Fix - Make Dashboard Show Your Data

## Simple Steps:

1. **Open Browser Console** (Press F12)

2. **Clear old data** (in console):
```javascript
localStorage.clear()
```

3. **Play a NEW game**:
   - Start camera session
   - Hit some targets (watch score increase)
   - Click "End Game"

4. **Check console** - You should see:
   - "✅ Demo session data saved to localStorage"
   - "🚀 Navigating to dashboard with session_id: demo-xxxxx"

5. **On Dashboard** - Check console for:
   - "🔍 Dashboard fetching data for sessionId: demo-xxxxx"
   - "✅ Loading demo session data from localStorage"

6. **If still showing demo_001**:
   - Check what session_id the dashboard is looking for
   - Check if that session exists in localStorage

## Quick Test in Console:

```javascript
// See all saved sessions
Object.keys(localStorage).filter(k => k.startsWith('demo_session_'))

// See the latest one
const keys = Object.keys(localStorage).filter(k => k.startsWith('demo_session_'));
if (keys.length > 0) {
  const latest = keys.sort().reverse()[0];
  const data = JSON.parse(localStorage.getItem(latest));
  console.log('Latest session:', data.session_id, 'Score:', data.summary.score);
}
```

## The Real Issue:

The dashboard shows `demo_001` because it can't find YOUR session. This happens when:
- session_id is null/undefined
- The session isn't in localStorage
- You're viewing an old session

**Solution**: Play a FRESH game (don't refresh), end it, and check the console logs to see if the session_id matches.

