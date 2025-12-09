import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const DashboardPage = ({ onNavigate, sessionId = null }) => {
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);

  // ---------------------------------------------------------
  // 🚀 FETCH REAL SESSION DATA (LOCALSTORAGE FIRST, THEN API)
  // ---------------------------------------------------------
  useEffect(() => {
    setLoading(true);

    async function fetchData() {
      console.log("🔍 Fetching session data...", { sessionId });

      // 1️⃣ FIRST: Try loading from localStorage (for demo sessions)
      if (sessionId && sessionId.startsWith('demo-')) {
        try {
          const storedKey = `demo_session_${sessionId}`;
          const storedData = localStorage.getItem(storedKey);
          
          if (storedData) {
            const data = JSON.parse(storedData);
            console.log("✅ Loaded demo session from localStorage:", data.session_id);
            console.log("📊 Session data structure:", {
              hasSummary: !!data.summary,
              hasPunchAccuracy: !!data.punch_accuracy,
              hasReactionTimes: !!data.reaction_times,
              hasDefense: !!data.defense,
              hasTimeline: !!data.timeline,
              timelineLength: data.timeline?.length || 0
            });
            setSessionData(data);
            setLoading(false);
            return;
          } else {
            console.warn("⚠️ Demo session not found in localStorage:", storedKey);
          }
        } catch (error) {
          console.error("❌ Error loading from localStorage:", error);
        }
      }

      // 2️⃣ SECOND: If no sessionId provided, check for latest demo session
      if (!sessionId) {
        try {
          const demoKeys = Object.keys(localStorage).filter(k => k.startsWith('demo_session_'));
          if (demoKeys.length > 0) {
            // Load all sessions and sort by timestamp (newest first)
            const sessions = demoKeys.map(key => {
              try {
                const storedData = localStorage.getItem(key);
                if (storedData) {
                  const data = JSON.parse(storedData);
                  return {
                    key,
                    data,
                    timestamp: data.timestamp ? new Date(data.timestamp).getTime() : 0
                  };
                }
              } catch (e) {
                console.error(`Error parsing session ${key}:`, e);
              }
              return null;
            }).filter(s => s !== null);
            
            // Sort by timestamp descending (newest first)
            sessions.sort((a, b) => b.timestamp - a.timestamp);
            
            if (sessions.length > 0) {
              const latestSession = sessions[0].data;
              console.log("✅ Loaded latest demo session from localStorage:", latestSession.session_id);
              console.log("📊 Session timestamp:", latestSession.timestamp);
              console.log("📊 Session data structure:", {
                hasSummary: !!latestSession.summary,
                hasPunchAccuracy: !!latestSession.punch_accuracy,
                hasReactionTimes: !!latestSession.reaction_times,
                hasDefense: !!latestSession.defense,
                hasTimeline: !!latestSession.timeline,
                timelineLength: latestSession.timeline?.length || 0,
                score: latestSession.summary?.score,
                totalPunches: latestSession.summary?.total_punches
              });
              setSessionData(latestSession);
              setLoading(false);
              return;
            }
          }
        } catch (error) {
          console.error("❌ Error loading latest demo session:", error);
        }
      }

      // 3️⃣ THIRD: Try API endpoint
      try {
        const API_BASE_URL =
          import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

        let url = `${API_BASE_URL}/session/latest`;
        if (sessionId) {
          url += `?session_id=${encodeURIComponent(sessionId)}`;
        }

        const response = await fetch(url, { cache: "no-store" });

        if (!response.ok) {
          throw new Error(`Backend error: ${response.status}`);
        }

        const data = await response.json();
        console.log("📊 LOADED SESSION FROM API:", data);

        // Accept demo_001 as fallback if no real data is available
        // This allows the dashboard to display something while waiting for real game data
        if (data.session_id === "demo_001") {
          console.warn("⚠️ Backend returned demo data - this is fallback data. Play a game to see your real session data.");
        }

        setSessionData(data);
      } catch (error) {
        console.error("❌ Failed to load session data:", error);
        setSessionData(null);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [sessionId]);

  // ---------------------------------------------------------
  // ⚠️ LOADING OR ERROR STATES
  // ---------------------------------------------------------
  if (loading) {
    return (
      <div
        className="min-h-screen text-white flex items-center justify-center"
        style={{
          background:
            "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 25%, #16213e 50%, #1a1a2e 75%, #0a0a0f 100%)",
        }}
      >
        <div className="text-2xl" style={{ color: "#b0b0b8" }}>
          Loading dashboard...
        </div>
      </div>
    );
  }

  if (!sessionData) {
    return (
      <div
        className="min-h-screen text-white flex items-center justify-center flex-col space-y-6"
        style={{
          background:
            "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 25%, #16213e 50%, #1a1a2e 75%, #0a0a0f 100%)",
        }}
      >
        <div className="text-2xl font-bold text-center" style={{ color: "#ff6b6b" }}>
          ⚠️ Using static data - play a new game to see your data
        </div>
        <div className="text-lg text-center max-w-md" style={{ color: "#b0b0b8" }}>
          No session data found. To see your real game data:
          <ol className="mt-4 text-left list-decimal list-inside space-y-2">
            <li>Go to the Landing page</li>
            <li>Click "Start Analysis" to play a game</li>
            <li>Hit some targets and click "End Game"</li>
            <li>Your data will appear here automatically</li>
          </ol>
        </div>
        <button
          onClick={() => onNavigate("landing")}
          style={{
            backgroundColor: "#ff6b6b",
            color: "white",
            border: "none",
            borderRadius: "16px",
            padding: "12px 24px",
            fontSize: "1rem",
            fontWeight: "700",
            cursor: "pointer",
            boxShadow: "0 8px 24px rgba(255, 107, 107, 0.35)",
          }}
        >
          Go to Landing Page
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------
  // 📊 CHART DATA PREP (with safety checks)
  // ---------------------------------------------------------
  const punchAccuracy = sessionData.punch_accuracy || { jab: 0, hook: 0, uppercut: 0 };
  const punchAccuracyData = [
    { name: "Jab", value: punchAccuracy.jab || 0 },
    { name: "Hook", value: punchAccuracy.hook || 0 },
    { name: "Uppercut", value: punchAccuracy.uppercut || 0 },
  ];

  const reactionTimes = sessionData.reaction_times || { jab: 250, hook: 250, uppercut: 250 };
  const reactionTimeData = [
    { name: "Jab", time: reactionTimes.jab || 250 },
    { name: "Hook", time: reactionTimes.hook || 250 },
    { name: "Uppercut", time: reactionTimes.uppercut || 250 },
  ];

  const defense = sessionData.defense || { blocked: 0, dodged: 0, hit: 0 };
  const defenseData = [
    { name: "Blocked", value: defense.blocked || 0 },
    { name: "Dodged", value: defense.dodged || 0 },
    { name: "Hit", value: defense.hit || 0 },
  ];

  const COLORS = ["#ff6b6b", "#ff8787", "#ff5252", "#ff8a80"];

  const totalDefense =
    (defense.blocked || 0) +
    (defense.dodged || 0) +
    (defense.hit || 0);

  // Ensure timeline exists and is an array
  const timeline = Array.isArray(sessionData.timeline) && sessionData.timeline.length > 0
    ? sessionData.timeline
    : [
        { t: 5, velocity: 5.0, accuracy: 0 },
        { t: 10, velocity: 5.0, accuracy: 0 },
        { t: 15, velocity: 5.0, accuracy: 0 },
        { t: 20, velocity: 5.0, accuracy: 0 },
        { t: 25, velocity: 5.0, accuracy: 0 }
      ];

  // Calculate derived metrics from actual recorded data
  const avgVelocityMph = (sessionData.summary?.avg_velocity ?? 0) * 2.237; // Convert m/s to mph
  const totalPunches = sessionData.summary?.total_punches ?? 0;
  const sessionScore = sessionData.summary?.score ?? 0;

  // Format session date/time for display
  const formatSessionDate = (timestamp) => {
    try {
      if (!timestamp) return "Unknown";
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) return "Invalid Date";
      
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const sessionDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      
      if (sessionDate.getTime() === today.getTime()) {
        // Today - show "Today at [time]"
        return `Today at ${date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
      } else {
        // Another day - show date and time
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          year: 'numeric'
        }) + ` at ${date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
      }
    } catch (error) {
      console.error("Error formatting date:", error);
      return "Unknown";
    }
  };

  // Format timeline for Performance Over Session - only use recorded data
  const performanceTimeline = timeline.map((point) => {
    const minutes = Math.floor(point.t / 60);
    const seconds = point.t % 60;
    return {
      time: `${minutes}:${String(Math.floor(seconds)).padStart(2, '0')}`,
      timeValue: point.t, // Keep numeric for sorting
      velocity: point.velocity ?? 0, // Actual recorded velocity
      accuracy: point.accuracy ?? 0 // Actual recorded accuracy
    };
  }).sort((a, b) => a.timeValue - b.timeValue);

  // ---------------------------------------------------------
  // 🖥️ DASHBOARD UI
  // ---------------------------------------------------------
  return (
    <main
      className="min-h-screen text-white p-10 flex flex-col items-center space-y-8 relative overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 25%, #16213e 50%, #1a1a2e 75%, #0a0a0f 100%)",
      }}
    >
      {/* Background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 20% 50%, rgba(255, 107, 107, 0.1) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(107, 142, 255, 0.08) 0%, transparent 50%)",
          pointerEvents: "none",
        }}
      />

      {/* Navigation */}
      <nav className="w-full flex justify-between items-center mb-4 relative z-10">
        <div style={{ color: "#b0b0b8" }}>
          <div style={{ fontSize: "0.9rem" }}>
            {formatSessionDate(sessionData.timestamp)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "2px" }}>
            Score: {sessionScore} | {totalPunches} punches
          </div>
        </div>

        <button
          onClick={() => onNavigate("landing")}
          style={{
            backgroundColor: "#ff6b6b",
            color: "white",
            border: "none",
            borderRadius: "16px",
            padding: "12px 24px",
            fontSize: "1rem",
            fontWeight: "700",
            cursor: "pointer",
            boxShadow: "0 8px 24px rgba(255, 107, 107, 0.35)",
          }}
        >
          ← Back to Landing
        </button>
      </nav>

      {/* Title */}
      <div className="text-center relative z-10 w-full">
        <h1
          className="text-6xl font-extrabold drop-shadow-lg mb-2"
          style={{
            background:
              "linear-gradient(135deg, #ff6b6b 0%, #ff8787 50%, #ff6b6b 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          🥊 PERFECTPUNCH DASHBOARD
        </h1>
        <p className="text-xl" style={{ color: "#b0b0b8" }}>
          Today's Training Session
        </p>
        <p className="text-lg mt-1" style={{ color: "#9ca3af" }}>
          {totalPunches} total punches
        </p>
      </div>

      {/* SUMMARY CARDS - Only Show Recorded Data */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 w-full relative z-10">
        {/* Score */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#ff6b6b" }}></div>
            <h2 className="text-sm font-semibold" style={{ color: "#b0b0b8" }}>
              Score
            </h2>
          </div>
          <p className="text-3xl font-extrabold" style={{ color: "#ff6b6b" }}>
            {sessionData.summary?.score ?? 0}
          </p>
        </div>

        {/* Average Punch Speed */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#ff6b6b" }}></div>
            <h2 className="text-sm font-semibold" style={{ color: "#b0b0b8" }}>
              Avg Punch Speed
            </h2>
          </div>
          <p className="text-3xl font-extrabold" style={{ color: "#ff6b6b" }}>
            {avgVelocityMph.toFixed(1)} mph
          </p>
        </div>

        {/* Reaction Time */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#ff6b6b" }}></div>
            <h2 className="text-sm font-semibold" style={{ color: "#b0b0b8" }}>
              Reaction Time
            </h2>
          </div>
          <p className="text-3xl font-extrabold" style={{ color: "#ff6b6b" }}>
            {sessionData.summary?.avg_reaction_time ?? 0} ms
          </p>
        </div>

        {/* Accuracy */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#ff6b6b" }}></div>
            <h2 className="text-sm font-semibold" style={{ color: "#b0b0b8" }}>
              Accuracy
            </h2>
          </div>
          <p className="text-3xl font-extrabold" style={{ color: "#ff6b6b" }}>
            {(sessionData.summary?.accuracy ?? 0).toFixed(1)}%
          </p>
        </div>

        {/* Critical Prevention */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#ff6b6b" }}></div>
            <h2 className="text-sm font-semibold" style={{ color: "#b0b0b8" }}>
              Critical Prevention
            </h2>
          </div>
          <p className="text-3xl font-extrabold" style={{ color: "#ff6b6b" }}>
            {(sessionData.summary?.critical_prevention ?? 0).toFixed(1)}%
          </p>
        </div>

        {/* Total Punches */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#ff6b6b" }}></div>
            <h2 className="text-sm font-semibold" style={{ color: "#b0b0b8" }}>
              Total Punches
            </h2>
          </div>
          <p className="text-3xl font-extrabold" style={{ color: "#ff6b6b" }}>
            {totalPunches}
          </p>
        </div>
      </div>

      {/* CHARTS - 3 Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 w-full relative z-10">
        {/* Punch Accuracy */}
        <section
          className="rounded-2xl p-8"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <h2 className="text-2xl font-bold text-center mb-6">
            Punch Accuracy
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={punchAccuracyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#4b5563" />
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" domain={[0, 100]} />
              <Tooltip />
              <Bar dataKey="value" fill="#ff6b6b" />
            </BarChart>
          </ResponsiveContainer>
        </section>

        {/* Reaction Times */}
        <section
          className="rounded-2xl p-8"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <h2 className="text-2xl font-bold text-center mb-6">
            Reaction Times
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={reactionTimeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#4b5563" />
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" label={{ value: 'Time (ms)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Bar dataKey="time" fill="#ff8787" />
            </BarChart>
          </ResponsiveContainer>
        </section>

        {/* Defense Breakdown */}
        <section
          className="rounded-2xl p-8"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <h2 className="text-2xl font-bold text-center mb-6">
            Defense Breakdown
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={defenseData}
                outerRadius={100}
                dataKey="value"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              >
                {defenseData.map((_, idx) => (
                  <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <p className="text-xs text-center mt-2" style={{ color: "#6b7280" }}>
            Hover over the chart for details
          </p>
        </section>
      </div>

      {/* PERFORMANCE OVER SESSION - Full Width */}
      <div className="w-full relative z-10">
        <section
          className="rounded-2xl p-8"
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <h2 className="text-2xl font-bold text-center mb-6">
            Performance Over Session
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={performanceTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#4b5563" />
              <XAxis 
                dataKey="time" 
                stroke="#9ca3af"
                interval={0}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis 
                yAxisId="left" 
                stroke="#9ca3af" 
                label={{ value: 'Velocity (m/s)', angle: -90, position: 'insideLeft' }} 
              />
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                stroke="#9ca3af"
                domain={[0, 100]}
                label={{ value: 'Accuracy (%)', angle: 90, position: 'insideRight' }} 
              />
              <Tooltip />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="velocity"
                stroke="#ff6b6b"
                strokeWidth={3}
                name="Velocity (m/s)"
                dot={{ r: 4 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="accuracy"
                stroke="#fbbf24"
                strokeWidth={3}
                name="Accuracy (%)"
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </section>
      </div>
    </main>
  );
};

export default DashboardPage;
