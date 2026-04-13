# Dashboard Stats Verification Checklist

## Pre-Test Setup

- [ ] Backend running on port 8000
  ```bash
  ps aux | grep "uvicorn\|python.*main:app" | grep -v grep
  ```

- [ ] Frontend running on port 5173
  ```bash
  ps aux | grep "vite\|npm run dev" | grep -v grep
  ```

- [ ] Both servers responding
  ```bash
  curl -s http://localhost:8000/health
  curl -s http://localhost:5173 | head -5
  ```

## Testing Punch Session

### Step 1: Run Analysis
```bash
curl -X POST http://localhost:8000/analysis/start 2>&1 | python3 -m json.tool | head -100
```

**Expected Output:**
- `"status": "success"`
- `"metrics": [...]` array with session data
- `"punches_thrown"`: positive integer (0 or more)
- `"correct_punches"`: integer ≤ punches_thrown
- All nested metrics populated

### Step 2: Verify API Response Structure

Check that the response includes:

```json
{
  "status": "success",
  "metrics": [{
    "fighter_id": "...",
    "session_id": "...",
    "timestamp": "...",
    "punches_thrown": <number>,
    "correct_punches": <number>,
    "metrics": {
      "offense": {
        "punch_accuracy": {
          "unit": "%",
          "types": {
            "jab": <number or null>,
            "hook": <number or null>,
            "uppercut": <number or null>
          },
          "derived": { "average": <number>, ... }
        },
        "punch_reaction_time": {
          "unit": "ms",
          "types": { ... },
          "derived": { "best": <number>, ... }
        },
        "punch_speed": {
          "unit": "px/s",
          "types": { ... },
          "derived": { "average": <number>, ... }
        }
      },
      "defense": {
        "punches_avoided": { "value": <number> },
        ...
      },
      "miscellaneous": {
        "flying_blocks_summary": {
          "values": {
            "blocked": <number>,
            "dodged": <number>,
            "hit": <number>
          }
        }
      }
    }
  }]
}
```

- [ ] Response has `status: "success"`
- [ ] Response has `metrics` array with at least one session
- [ ] Session has `punches_thrown` and `correct_punches`
- [ ] Offense metrics have all three sub-metrics (accuracy, reaction_time, speed)
- [ ] Defense metrics have `punches_avoided` with a value
- [ ] Miscellaneous has `flying_blocks_summary` with counts

### Step 3: Open Dashboard in Browser

Visit: `http://localhost:5173`

- [ ] Page loads without console errors
- [ ] "Go to Landing Page" button visible
- [ ] Click button to navigate to landing page

### Step 4: Check Browser Console

Open DevTools (F12 or Cmd+Option+I):

**In LandingPage (after clicking "Start Punch Analysis"):**
- [ ] See "✅ Transformed single session:" message
- [ ] See "✅ All transformedMetrics:" message
- [ ] No red error messages

**In DashboardPage (after analysis completes):**
- [ ] See "Using metrics data from analysis:" message
- [ ] See "📊 sessionData.punch_accuracy: {...}"
- [ ] See "📊 sessionData.reaction_times: {...}"
- [ ] See "📊 sessionData.defense: {...}"

### Step 5: Verify Dashboard Displays Correctly

Check these sections appear:

#### Summary Metrics
- [ ] "Score" card showing: number of correct punches
- [ ] "Accuracy" card showing: percentage (e.g., 28.6%)
- [ ] "Avg Velocity" card showing: m/s value (e.g., 45.95)
- [ ] "Avg Reaction Time" card showing: milliseconds (e.g., 1001)
- [ ] "Critical Prevention" card showing: percentage (e.g., 75%)

#### Punch Accuracy Chart
- [ ] Bar chart visible
- [ ] Three bars labeled: "Jab", "Hook", "Uppercut"
- [ ] Y-axis shows 0-100%
- [ ] Each bar shows accuracy % for that punch type
  - Expected: Could be 0%, 50%, 100% depending on punches thrown

#### Reaction Times Chart
- [ ] Bar chart visible
- [ ] Three bars labeled: "Jab", "Hook", "Uppercut"
- [ ] Y-axis shows milliseconds
- [ ] Each bar shows average reaction time in ms
  - Expected: Values like 1000-3000 ms

#### Defense Breakdown Chart
- [ ] Pie chart or breakdown visible
- [ ] Shows "Blocked", "Dodged", "Hit" segments
- [ ] Each segment shows count and percentage
- [ ] Percentages should add to ~100%
  - Expected: Blocked + Dodged + Hit = total interactions

### Step 6: Verify Calculations Are Correct

**Given example data:**
- Punches thrown: 7
- Correct punches: 2
- Punch speed average: 4595.1 px/s
- Reaction time best: 1000.6 ms
- Punches avoided: 75%
- Defense: blocked=1, dodged=2, hit=1

**Expected dashboard values:**
- [ ] Score: 2 (correct punches)
- [ ] Accuracy: 28.6% (2÷7×100)
- [ ] Avg Velocity: 45.95 m/s (4595.1÷100)
- [ ] Avg Reaction Time: 1001 ms (best ≈ 1000.6)
- [ ] Critical Prevention: 75%
- [ ] Defense breakdown: blocked=1, dodged=2, hit=1

### Step 7: Edge Cases to Test (Optional)

#### Case 1: No Punches Thrown
```bash
# Manually create session with 0 punches
# Check that dashboard shows:
# - Score: 0
# - Accuracy: 0%
# - All charts show 0 or no data
```

#### Case 2: Perfect Accuracy
```bash
# Session with all correct punches
# Expected:
# - Accuracy: 100%
# - All punch types might show 100% or 0% depending on throws
```

#### Case 3: No Defense Success
```bash
# Session where all incoming are hit
# Expected:
# - Critical Prevention: 0%
# - Defense pie: 100% hit
```

## Troubleshooting

### Dashboard Shows No Data
**Steps:**
1. Check browser console for errors
2. Verify API returned data: `curl -X POST http://localhost:8000/analysis/start`
3. Check LandingPage transformation logs
4. Inspect React DevTools for sessionData prop

### Dashboard Shows Wrong Values
**Steps:**
1. Compare actual API values to expected calculations
2. Check transformation in `/src/pages/LandingPage.jsx` lines 150-220
3. Verify DashboardPage metric extraction (lines 240-270)
4. Check DASHBOARD_STATS_GUIDE.md for expected formulas

### Console Shows Null Reference Errors
**Steps:**
1. Ensure LandingPage.jsx has null-handling fixes
2. Run: `git log --oneline | head -5` and verify commits include the null-handling fix
3. Reload browser (Cmd+R or Ctrl+R)
4. Check browser cache: DevTools → Network → Disable cache

### Charts Not Rendering
**Steps:**
1. Check browser console for Recharts errors
2. Verify data structure is valid JSON
3. Check that data arrays have the expected format
4. Test in Chrome if possible (some browsers have rendering issues)

## Success Criteria

Dashboard is working correctly if:

- [ ] All API responses return valid metrics
- [ ] No console errors in browser DevTools
- [ ] All transformation logs show "✅" success messages
- [ ] Dashboard summary cards show reasonable values
- [ ] All three charts render with data
- [ ] Calculated values match expected formulas
- [ ] Numbers are in correct units (%, ms, m/s, count)
- [ ] Edge cases handled gracefully

## Quick Validation Commands

```bash
# Check backend health
curl -s http://localhost:8000/health

# Run test analysis
curl -s -X POST http://localhost:8000/analysis/start | python3 << 'EOF'
import json, sys
data = json.load(sys.stdin)
m = data['metrics'][0]['metrics']
print(f"Accuracy avg: {m['offense']['punch_accuracy']['derived']['average']}%")
print(f"Reaction time best: {m['offense']['punch_reaction_time']['derived']['best']}ms")
print(f"Speed avg: {m['offense']['punch_speed']['derived']['average']}px/s")
print(f"Punches avoided: {m['defense']['punches_avoided']['value']}%")
print(f"Defense: {m['miscellaneous']['flying_blocks_summary']['values']}")
EOF

# Check frontend build
npm run build  # Build will fail if there are syntax errors

# Start development servers
npm run dev  # Frontend
# In another terminal:
python -m uvicorn perfectpunch_backend.main:app --reload
```

## Notes

- First run after deployment may take longer (warm-up time)
- Camera initialization adds ~3-5 seconds
- Pose detection ML model loads on first request
- PyTorch model loads in parallel with camera/pose
- All heavy initialization happens in background

## Reference Documents

- **DASHBOARD_STATS_GUIDE.md** - Complete metrics reference
- **DASHBOARD_STATS_FIX.md** - What was fixed and why
- **LandingPage.jsx** lines 150-220 - Transformation logic
- **DashboardPage.jsx** lines 240-270 - Chart data preparation
