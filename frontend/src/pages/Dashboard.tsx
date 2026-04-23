import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { analyticsApi } from '../api/analytics'
import { workoutsApi } from '../api/workouts'
import { StatCard } from '../components/StatCard'
import { Badge } from '../components/Badge'
import { Spinner } from '../components/Spinner'
import { formatPace, formatDistance, formatDuration, formatDate, tsbColor } from '../lib/utils'
import { TrendingUp, TrendingDown, Minus, Activity, Dumbbell, Flame } from 'lucide-react'

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
  const tsb = freshness?.current?.tsb ?? null

  const chartData = (freshness?.data ?? []).map(p => ({
    week: p.week_start.slice(5),
    CTL: p.chronic_load,
    ATL: p.acute_load,
    TSB: p.tsb,
  }))

  if (loadingSummary) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size={32} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-slate-400 mt-0.5">This week's overview</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Weekly TSS"
          value={cw?.weekly_tss?.toFixed(0) ?? '—'}
          sub="training stress"
          icon={<Flame size={14} />}
        />
        <StatCard
          label="Run volume"
          value={cw ? `${Number(cw.total_run_km).toFixed(1)} km` : '—'}
          sub={`${cw?.run_workouts ?? 0} runs`}
          icon={<Activity size={14} />}
        />
        <StatCard
          label="Gym volume"
          value={cw ? `${Number(cw.total_gym_volume_kg / 1000).toFixed(1)}t` : '—'}
          sub={`${cw?.gym_workouts ?? 0} sessions`}
          icon={<Dumbbell size={14} />}
        />
        <StatCard
          label="Form (TSB)"
          value={tsb !== null ? tsb.toFixed(1) : '—'}
          valueClass={tsbColor(tsb)}
          sub={tsb !== null ? (tsb > 5 ? 'Fresh' : tsb < -10 ? 'Fatigued' : 'Neutral') : 'no data'}
        />
      </div>

      {/* Fitness freshness chart */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Performance Management Chart</h2>
            <p className="text-xs text-slate-400 mt-0.5">CTL = fitness · ATL = fatigue · TSB = form</p>
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
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 0, left: -10 }}>
              <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
              <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="CTL" stroke="#6366f1" strokeWidth={2} dot={false} name="CTL (fitness)" />
              <Line type="monotone" dataKey="ATL" stroke="#f59e0b" strokeWidth={2} dot={false} name="ATL (fatigue)" />
              <Line type="monotone" dataKey="TSB" stroke="#22c55e" strokeWidth={1.5} dot={false} name="TSB (form)" strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Weekly summary trailing */}
      {(summary?.trailing_4_weeks?.length ?? 0) > 0 && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Last 4 weeks</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-400 border-b border-slate-700">
                  <th className="text-left pb-2 font-medium">Week</th>
                  <th className="text-right pb-2 font-medium">Workouts</th>
                  <th className="text-right pb-2 font-medium">Run km</th>
                  <th className="text-right pb-2 font-medium">TSS</th>
                  <th className="text-right pb-2 font-medium">Avg pace</th>
                  <th className="text-right pb-2 font-medium">RPE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {summary!.trailing_4_weeks.map(w => (
                  <tr key={w.week_start_date} className="text-slate-300">
                    <td className="py-2 text-slate-400 text-xs">{w.week_start_date}</td>
                    <td className="py-2 text-right">{w.total_workouts}</td>
                    <td className="py-2 text-right">{Number(w.total_run_km).toFixed(1)}</td>
                    <td className="py-2 text-right">{w.weekly_tss?.toFixed(0) ?? '—'}</td>
                    <td className="py-2 text-right">{formatPace(w.avg_pace_sec_per_km)}</td>
                    <td className="py-2 text-right">{w.avg_rpe?.toFixed(1) ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent workouts */}
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
                        ? formatDistance(w.distance_meters)
                        : w.total_volume_kg
                          ? `${w.total_volume_kg.toLocaleString()} kg volume`
                          : formatDuration(w.duration_seconds)}
                    </p>
                    <p className="text-xs text-slate-500">{formatDate(w.started_at)}</p>
                  </div>
                </div>
                <div className="text-right">
                  {w.workout_type === 'run' && (
                    <p className="text-sm text-slate-300">{formatPace(w.avg_pace_sec_per_km)}</p>
                  )}
                  <Badge variant={w.status as any}>{w.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
