# Dashboard Stats - Quick Reference Card

## ⚡ Quick Start

```bash
# 1. Make sure servers are running
ps aux | grep -E "uvicorn|vite" | grep -v grep

# 2. Run a test analysis
curl -X POST http://localhost:8000/analysis/start 2>&1 | python3 -m json.tool | head -50

# 3. Open dashboard
open http://localhost:5173  # macOS
# or
xdg-open http://localhost:5173  # Linux

# 4. Check browser console (F12) for transformation logs
# Look for: ✅ Transformed single session
```

## 📊 Dashboard Metrics

### Summary Cards
| Metric | Formula | Example |
|--------|---------|---------|
| **Score** | correct_punches | 2 |
| **Accuracy** | (correct / total) × 100 | 28.6% |
| **Velocity** | punch_speed.average / 100 | 45.95 m/s |
| **Reaction Time** | punch_reaction_time.best | 1001 ms |
| **Prevention** | punches_avoided | 75% |
| **Total Punches** | punches_thrown | 7 |

### Chart Data

**Punch Accuracy (%)** - By punch type
```
Jab: 0%
Hook: 0%
Uppercut: 100%
```

**Reaction Times (ms)** - By punch type
```
Jab: 2990 ms
Hook: 1117 ms
Uppercut: 1068 ms
```

**Defense Breakdown** - Counts
```
Blocked: 1
Dodged: 2
Hit: 1
```

## 🐛 Debugging

### Console Logs to Check
```javascript
// In LandingPage (after hitting "Start Analysis")
✅ Transformed single session: {...}
✅ All transformedMetrics: [...]

// In DashboardPage
Using metrics data from analysis: {...}
📊 sessionData.punch_accuracy: {...}
📊 sessionData.reaction_times: {...}
📊 sessionData.defense: {...}
```

### Quick Problem Solver

| Issue | Check |
|-------|-------|
| No data on dashboard | ❌ Is API returning metrics? `curl -X POST http://localhost:8000/analysis/start` |
| Browser errors | ❌ Check DevTools console (F12) for transformation errors |
| Wrong values | ❌ Compare to expected calculations in DASHBOARD_STATS_GUIDE.md |
| Charts empty | ❌ Verify data structure in React DevTools |

## 🔧 Key Files

```
src/pages/LandingPage.jsx (lines 150-220)
└─ Transformation logic - converts API response to dashboard format

src/pages/DashboardPage.jsx (lines 240-270)
└─ Chart preparation - creates data for Recharts

DASHBOARD_STATS_GUIDE.md
└─ Complete reference - all metrics and calculations

DASHBOARD_STATS_FIX.md
└─ Technical details - what was fixed and why

DASHBOARD_VERIFICATION_CHECKLIST.md
└─ Testing procedure - step-by-step verification
```

## ✅ Verification Checklist

### Before Opening Dashboard
- [ ] Backend running: `ps aux | grep uvicorn`
- [ ] Frontend running: `ps aux | grep vite`
- [ ] API responds: `curl -X POST http://localhost:8000/analysis/start`
- [ ] Response has metrics array with valid data

### After Opening Dashboard
- [ ] No red errors in DevTools console
- [ ] Transformation logs show ✅ success
- [ ] Dashboard loads without errors
- [ ] All metric cards visible
- [ ] All charts render with data

### Expected Values
For session with 7 throws, 2 correct:
- [ ] Score: 2
- [ ] Accuracy: 28.6%
- [ ] Velocity: 45.95 m/s
- [ ] Reaction Time: ~1001 ms
- [ ] Prevention: 75%

## 📱 Data Structure

### Input (from API)
```javascript
{
  "punches_thrown": 7,
  "correct_punches": 2,
  "metrics": {
    "offense": {
      "punch_accuracy": { "types": {...}, "derived": {...} },
      "punch_reaction_time": { "types": {...}, "derived": {...} },
      "punch_speed": { "types": {...}, "derived": {...} }
    },
    "defense": { "punches_avoided": { "value": 75.0 } },
    "miscellaneous": { "flying_blocks_summary": { "values": {...} } }
  }
}
```

### Output (to Dashboard)
```javascript
{
  "summary": {
    "score": 2,
    "accuracy": 28.6,
    "avg_velocity": 45.95,
    "avg_reaction_time": 1001,
    "critical_prevention": 75.0,
    "total_punches": 7
  },
  "punch_accuracy": { "jab": 0, "hook": 0, "uppercut": 100.0 },
  "reaction_times": { "jab": 2990, "hook": 1117, "uppercut": 1068 },
  "defense": { "blocked": 1, "dodged": 2, "hit": 1 },
  "punch_speed": { "jab": 2895.16, "hook": 5256.07, "uppercut": 6484.06 }
}
```

## 🎯 What Was Fixed

**Before**: Direct property access crashed on null values
```javascript
❌ const speed = punchSpeed.derived.average / 100;  // CRASH if null
```

**After**: Safe property access with fallbacks
```javascript
✅ const speed = punchSpeed?.derived?.average || 0;  // Safe
```

## 📚 Further Reading

- **Complete Guide**: DASHBOARD_STATS_GUIDE.md
- **Fix Details**: DASHBOARD_STATS_FIX.md
- **Testing**: DASHBOARD_VERIFICATION_CHECKLIST.md
- **Summary**: DASHBOARD_FIX_SUMMARY.md

## 🚀 Next Steps

1. Verify with actual punch session
2. Check all values display correctly
3. Test edge cases (0 punches, perfect accuracy, etc.)
4. Review defensive stats are accurate

---

**Status**: ✅ Dashboard stats calculation fixed and ready for testing
**Last Updated**: 2026-04-13
**Branch**: fix/pytorch-model-loading
