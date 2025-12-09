'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { supabase } from '../lib/supabaseClient'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Trophy, Activity, Shield } from 'lucide-react'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any[]>([])

  useEffect(() => {
    const fetchData = async () => {
      const { data } = await supabase.from('punch_metrics').select('*')
      setMetrics(data || [])
    }
    fetchData()
  }, [])

  const chartData = {
    labels: metrics.map((m) => m.session_date || ''),
    datasets: [
      {
        label: 'Reaction Time (ms)',
        data: metrics.map((m) => m.reaction_time || 0),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.15)',
        fill: true,
        tension: 0.4,
      },
    ],
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-white to-red-50 py-12 px-6 flex justify-center">
      <div className="max-w-6xl w-full space-y-10">
        {/* Navigation */}
        <nav className="flex justify-end gap-4 mb-4">
          <Link 
            href="/dashboard" 
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-semibold"
          >
            View Detailed Dashboard
          </Link>
        </nav>
        
        {/* Header */}
        <div className="text-center">
          <h1 className="text-5xl font-extrabold text-gray-800 mb-3">Dashboard</h1>
          <p className="text-gray-600 text-lg">
            Track your training progress, punch accuracy, and performance trends.
          </p>
        </div>

        {/* Stat Boxes */}
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-2xl shadow-md text-center border border-gray-100 hover:shadow-lg transition">
            <Trophy className="mx-auto text-yellow-400 mb-3" size={38} />
            <h2 className="font-bold text-gray-700 text-xl">Average Accuracy</h2>
            <p className="text-3xl font-extrabold text-gray-900 mt-1">
              {metrics.length
                ? `${(
                    metrics.reduce((a, b) => a + (b.accuracy || 0), 0) / metrics.length
                  ).toFixed(1)}%`
                : '—'}
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-md text-center border border-gray-100 hover:shadow-lg transition">
            <Activity className="mx-auto text-red-400 mb-3" size={38} />
            <h2 className="font-bold text-gray-700 text-xl">Avg Reaction Time</h2>
            <p className="text-3xl font-extrabold text-gray-900 mt-1">
              {metrics.length
                ? `${(
                    metrics.reduce((a, b) => a + (b.reaction_time || 0), 0) / metrics.length
                  ).toFixed(0)} ms`
                : '—'}
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-md text-center border border-gray-100 hover:shadow-lg transition">
            <Shield className="mx-auto text-blue-400 mb-3" size={38} />
            <h2 className="font-bold text-gray-700 text-xl">Sessions Logged</h2>
            <p className="text-3xl font-extrabold text-gray-900 mt-1">{metrics.length || 0}</p>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-white p-8 rounded-2xl shadow-md border border-gray-100 hover:shadow-lg transition text-center flex flex-col items-center justify-center">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">Reaction Time Trends</h2>
          <div className="w-full flex justify-center">
            <div className="w-full sm:w-4/5 md:w-3/5 lg:w-2/5">
              <Line
                data={chartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: true,
                  plugins: { legend: { display: false } },
                  scales: {
                    y: { beginAtZero: true },
                    x: { ticks: { color: '#6b7280' } },
                  },
                }}
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl shadow-md border border-gray-100 hover:shadow-lg transition p-6">
          <h2 className="text-2xl font-semibold mb-4 text-gray-800 text-center">
            Punch Session Details
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full border border-gray-200 rounded-xl overflow-hidden text-center">
              <thead className="bg-red-600 text-white text-sm uppercase">
                <tr>
                  <th className="p-3 text-center">Date</th>
                  <th className="p-3 text-center">Punch Type</th>
                  <th className="p-3 text-center">Reaction Time (ms)</th>
                  <th className="p-3 text-center">Accuracy (%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {metrics.length > 0 ? (
                  metrics.map((m) => (
                    <tr key={m.id} className="hover:bg-red-50 transition">
                      <td className="p-3 text-center">{m.session_date}</td>
                      <td className="p-3 text-center">{m.punch_type}</td>
                      <td className="p-3 text-center">{m.reaction_time}</td>
                      <td className="p-3 text-center">{m.accuracy}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="p-6 text-center text-gray-500 italic">
                      No punch data yet — add some in Supabase!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Feedback */}
        <div className="bg-gradient-to-r from-red-500 to-pink-500 text-white p-8 rounded-2xl shadow text-center">
          <h2 className="text-2xl font-bold mb-2">AI Feedback</h2>
          <p className="text-lg opacity-90">
            “Your cross-punch accuracy improved by 9% this week. Keep refining your stance — you’re
            building precision and consistency.”
          </p>
        </div>
      </div>
    </main>
  )
}
