import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { analyticsApi } from '../api/analytics'
import { workoutsApi } from '../api/workouts'
import { agentApi } from '../api/agent'
import { StatCard } from '../components/StatCard'
import { Badge } from '../components/Badge'
import { Spinner } from '../components/Spinner'
import { formatPace, formatDistance, formatDuration, formatDate, formatDurationShort, formatWeekDate } from '../lib/utils'
import { TrendingUp, TrendingDown, Minus, Activity, Clock, BarChart2, Bot, Sparkles } from 'lucide-react'

function TrendIcon({ trend }: { trend: string | null }) {
  if (trend === 'increasing') return <TrendingUp size={14} className="text-green-400" />
  if (trend === 'decreasing') return <TrendingDown size={14} className="text-red-400" />
  return <Minus size={14} className="text-slate-400" />
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs space-y-1">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="text-white font-medium">{p.value?.toFixed(1)}</span>
        </div>
      ))}
    </div>
  )
}

// ── AI Daily Briefing ─────────────────────────────────────────────────────────

const TODAY_KEY = `ai_briefing_${new Date().toISOString().slice(0, 10)}`

function AiBriefing() {
  const cached = localStorage.getItem(TODAY_KEY)
  const [briefing, setBriefing] = useState<string | null>(cached)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  const fetch = async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await agentApi.coachingQuery(
        'Give me a 2-sentence personalised training briefing for today based on my recent workouts. Be specific and actionable.',
        4
      )
      const text = res.data.answer
      setBriefing(text)
      localStorage.setItem(TODAY_KEY, text)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-slate-800/60 border border-indigo-500/20 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-7 h-7 rounded-lg bg-indigo-600/30 flex items-center justify-center">
          <Bot size={14} className="text-indigo-400" />
        </div>
        <span className="text-sm font-medium text-white">Today's training insight</span>
      </div>

      {briefing ? (
        <p className="text-sm text-slate-300 leading-relaxed">{briefing}</p>
      ) : error ? (
        <p className="text-sm text-slate-500">Couldn't load insight — check your OpenRouter key or try again later.</p>
      ) : (
        <p className="text-sm text-slate-500">Get a personalised AI insight based on your recent training history.</p>
      )}

      {!briefing && (
        <button
          onClick={fetch}
          disabled={loading}
          className="mt-3 flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? <><Spinner size={11} /> Thinking…</> : <><Sparkles size={11} /> Get today's insight</>}
        </button>
      )}
    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function Dashboard() {
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => analyticsApi.summary().then(r => r.data),
  })

  const { data: freshness } = useQuery({
    queryKey: ['fitness-freshness'],
    queryFn: () => analyticsApi.fitnessFreshness(16).then(r => r.data),
  })

  const { data: workouts } = useQuery({
    queryKey: ['workouts', { limit: 5 }],
    queryFn: () => workoutsApi.list({ limit: 5 }).then(r => r.data),
  })

  const cw = summary?.current_week
  const trailing = summary?.trailing_4_weeks ?? []

  // Consistency: how many of the last 4 weeks had at least 1 workout
  const consistentWeeks = trailing.filter(w => w.total_workouts >= 1).length

  const chartData = (freshness?.data ?? []).map(p => ({
    week: p.week_start.slice(5),
    CTL: p.chronic_load,
    ATL: p.acute_load,
    TSB: p.tsb,
  }))

  if (loadingSummary) {
    return <div className="flex items-center justify-center h-64"><Spinner size={32} /></div>
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-slate-400 mt-0.5">This week's overview</p>
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="This week"
          value={`${cw?.total_workouts ?? 0} workouts`}
          sub={cw
            ? `${cw.run_workouts} run${cw.run_workouts !== 1 ? 's' : ''} · ${cw.gym_workouts} gym`
            : 'no workouts yet'}
          icon={<Activity size={14} />}
        />
        <StatCard
          label="Run distance"
          value={cw ? `${Number(cw.total_run_km ?? 0).toFixed(1)} km` : '0 km'}
          sub={cw?.avg_pace_sec_per_km
            ? `avg ${formatPace(cw.avg_pace_sec_per_km)}`
            : `${cw?.run_workouts ?? 0} runs`}
          icon={<TrendingUp size={14} />}
        />
        <StatCard
          label="Training time"
          value={formatDurationShort(cw?.total_duration_min ?? 0)}
          sub="this week"
          icon={<Clock size={14} />}
        />
        <StatCard
          label="Consistency"
          value={`${consistentWeeks}/4 weeks`}
          sub={summary?.fitness_trend
            ? `trend: ${summary.fitness_trend}`
            : 'last 4 weeks'}
          valueClass={consistentWeeks >= 3 ? 'text-green-400' : consistentWeeks >= 2 ? 'text-yellow-400' : 'text-slate-300'}
          icon={<BarChart2 size={14} />}
        />
      </div>

      {/* ── AI briefing ── */}
      <AiBriefing />

      {/* ── Training load chart ── */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Training load</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Blue = fitness built · Orange = recent fatigue · Green = how fresh you feel
            </p>
          </div>
          {summary?.fitness_trend && (
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <TrendIcon trend={summary.fitness_trend} />
              <span className="capitalize">{summary.fitness_trend}</span>
            </div>
          )}
        </div>

        {chartData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
            Log workouts to see your fitness trends here
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 0, left: -10 }}>
              <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
              <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="CTL" stroke="#6366f1" strokeWidth={2} dot={false} name="Fitness (CTL)" />
              <Line type="monotone" dataKey="ATL" stroke="#f59e0b" strokeWidth={2} dot={false} name="Fatigue (ATL)" />
              <Line type="monotone" dataKey="TSB" stroke="#22c55e" strokeWidth={1.5} dot={false} name="Freshness (TSB)" strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Weekly summary table ── */}
      {trailing.length > 0 && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Last 4 weeks</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-400 border-b border-slate-700">
                  <th className="text-left pb-2 font-medium">Week</th>
                  <th className="text-right pb-2 font-medium">Workouts</th>
                  <th className="text-right pb-2 font-medium">Run km</th>
                  <th className="text-right pb-2 font-medium">Active time</th>
                  <th className="text-right pb-2 font-medium">Avg pace</th>
                  <th className="text-right pb-2 font-medium">Gym sessions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {trailing.map(w => (
                  <tr key={w.week_start_date} className="text-slate-300">
                    <td className="py-2 text-slate-400 text-xs">{formatWeekDate(w.week_start_date)}</td>
                    <td className="py-2 text-right">{w.total_workouts}</td>
                    <td className="py-2 text-right">{Number(w.total_run_km).toFixed(1)}</td>
                    <td className="py-2 text-right">{formatDurationShort(w.total_duration_min)}</td>
                    <td className="py-2 text-right">{formatPace(w.avg_pace_sec_per_km)}</td>
                    <td className="py-2 text-right">{w.gym_workouts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Recent workouts ── */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Recent workouts</h2>
        {!workouts?.data?.length ? (
          <p className="text-slate-500 text-sm">No workouts yet — log your first one!</p>
        ) : (
          <div className="space-y-2">
            {workouts.data.map(w => (
              <div key={w.id} className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                <div className="flex items-center gap-3">
                  <Badge variant={w.workout_type as any}>{w.workout_type}</Badge>
                  <div>
                    <p className="text-sm text-slate-200">
                      {w.workout_type === 'run'
                        ? `${formatDistance(w.distance_meters)} · ${formatPace(w.avg_pace_sec_per_km)}`
                        : w.workout_template
                          ? w.workout_template
                          : formatDuration(w.duration_seconds)}
                    </p>
                    <p className="text-xs text-slate-500">{formatDate(w.started_at)}</p>
                  </div>
                </div>
                <Badge variant={w.status as any}>{w.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
