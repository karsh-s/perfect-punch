# Dashboard Statistics Guide

## Overview
The dashboard displays real-time and historical punch training statistics with detailed breakdowns by punch type, defensive performance, and time-based analysis.

## Data Flow

```
Camera Input
    ↓
MediaPipe Pose Detection
    ↓
PyTorch 3D CNN Classification
    ↓
main_python_analysis.py (generates metrics)
    ↓
session_metrics.json
    ↓
Backend API (/analysis/start)
    ↓
LandingPage Transformation
    ↓
Transformed Metrics Object
    ↓
DashboardPage Rendering
```

## Metrics Structure

### Summary Metrics (overview.summary)
These are high-level performance indicators:

| Metric | Unit | Description | Formula |
|--------|------|-------------|---------|
| **score** | count | Number of correct punches thrown | correct_punches |
| **accuracy** | % | Overall punch accuracy rate | (correct_punches / total_punches) × 100 |
| **avg_velocity** | m/s | Average punch velocity converted from pixels | (punch_speed.derived.average / 100) |
| **avg_reaction_time** | ms | Best reaction time achieved | punch_reaction_time.derived.best |
| **critical_prevention** | % | Percentage of incoming targets blocked or dodged | punches_avoided percentage |
| **total_punches** | count | Total number of punch attempts | punches_thrown |

### Punch Accuracy by Type
Shows accuracy percentage for each punch type individually:

```javascript
{
  "jab": 0,          // % of jabs that were correct
  "hook": 0,         // % of hooks that were correct
  "uppercut": 100.0  // % of uppercuits that were correct
}
```

**Dashboard Display**: Bar chart showing accuracy (0-100%) for each punch type

### Reaction Times by Type
Shows average reaction time (in milliseconds) for each punch type:

```javascript
{
  "jab": 2990,       // Average reaction time for jabs (ms)
  "hook": 1117,      // Average reaction time for hooks (ms)
  "uppercut": 1068   // Average reaction time for upperccuts (ms)
}
```

**Dashboard Display**: Bar chart showing reaction time (ms) for each punch type

### Defense Breakdown
Shows counts of defensive outcomes from the flying blocks drill:

```javascript
{
  "blocked": 1,  // Number of targets successfully blocked
  "dodged": 2,   // Number of targets successfully dodged
  "hit": 1       // Number of targets that hit (not defended)
}
```

**Dashboard Display**: Pie chart showing distribution of defense outcomes

### Punch Speed by Type
Shows average punch speed (in pixels per second) for each punch type:

```javascript
{
  "jab": 2895.16,      // Average punch speed for jabs (px/s)
  "hook": 5256.07,     // Average punch speed for hooks (px/s)
  "uppercut": 6484.06  // Average punch speed for upperccuts (px/s)
}
```

## Transformation Logic (LandingPage.jsx)

The LandingPage component transforms the raw `session_metrics.json` data into a dashboard-ready format:

### Key Transformations

1. **Accuracy Calculation**
   ```javascript
   accuracy = (correct_punches / punches_thrown) × 100
   ```

2. **Velocity Conversion**
   ```javascript
   avg_velocity = punch_speed.derived.average / 100  // px/s to m/s
   ```

3. **Reaction Time**
   ```javascript
   avg_reaction_time = punch_reaction_time.derived.best
   // Uses best time, or falls back to average if best is null
   ```

4. **Critical Prevention**
   ```javascript
   critical_prevention = punches_avoided.value  // Direct percentage
   ```

5. **Defense Breakdown**
   ```javascript
   defense = flying_blocks_summary.values  // { blocked, dodged, hit }
   ```

### Null Handling

The transformation uses optional chaining and nullish coalescing to safely handle incomplete data:

```javascript
// Safe property access
const speedValue = punchSpeed?.derived?.average || 0;

// Fallback values for metrics
const reactionTimeBest = reactionTime?.derived?.best || reactionTime?.derived?.average || 250;
const accuracyJab = punchAccuracy?.types?.jab || 0;
```

## Example Output

For a session with:
- 7 punches thrown, 2 correct
- Punch speed average: 4595.1 px/s
- Reaction times: jab=2990ms, hook=1117ms, uppercut=1068ms
- Defense: 1 blocked, 2 dodged, 1 hit

**Dashboard will display:**

### Summary
- Score: 2 correct punches
- Accuracy: 28.6%
- Avg Velocity: 45.95 m/s
- Avg Reaction Time: 1001 ms
- Critical Prevention: 75%
- Total Punches: 7

### Punch Accuracy Chart
- Jab: 0%
- Hook: 0%
- Uppercut: 100%

### Reaction Times Chart
- Jab: 2990 ms
- Hook: 1117 ms
- Uppercut: 1068 ms

### Defense Breakdown Chart
- Blocked: 1 (25%)
- Dodged: 2 (50%)
- Hit: 1 (25%)

## Units Reference

All units are preserved from the backend and match the JSON structure:

| Data Type | Unit | Symbol |
|-----------|------|--------|
| Accuracy | Percentage | % |
| Reaction Time | Milliseconds | ms |
| Punch Speed | Pixels per second | px/s |
| Velocity (converted) | Meters per second | m/s |
| Defense | Count | integer |
| Prevention | Percentage | % |

## Debugging

To verify the transformation is working correctly:

1. **Check LandingPage console logs**
   ```
   📊 metricsArray: [...]
   ✅ Transformed single session: {...}
   ✅ All transformedMetrics: [...]
   ```

2. **Check DashboardPage console logs**
   ```
   🔍 Fetching session data...
   ✅ Using metrics data from analysis: {...}
   📊 sessionData.punch_accuracy: {...}
   📊 sessionData.reaction_times: {...}
   📊 sessionData.defense: {...}
   ```

3. **Verify data structure in React DevTools**
   - Check `sessionData` prop in DashboardPage
   - Verify `punch_accuracy`, `reaction_times`, `defense` objects
   - Confirm `summary` object has all required fields

## Known Limitations

1. **Incomplete Sessions**: If no punches are thrown, accuracy defaults to 0%
2. **Null Values**: Null metrics are replaced with sensible defaults (0 or 250ms)
3. **Defense Stats**: Only show flying blocks outcomes, not all defensive actions
4. **Timeline**: Currently empty array placeholder for future expansion

## Future Enhancements

- [ ] Add punch count breakdown by type (jabs vs hooks vs upperccuts)
- [ ] Add fatigue analysis (accuracy degradation over time)
- [ ] Add recovery time between punches
- [ ] Add power consistency metrics
- [ ] Add form/technique analysis
