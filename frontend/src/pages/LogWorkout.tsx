import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { workoutsApi } from '../api/workouts'
import { useToast } from '../hooks/useToast'
import { CheckCircle, Plus, Trash2 } from 'lucide-react'

type WorkoutType = 'run' | 'gym'

interface GymSet {
  exercise_name: string
  reps: string
  weight_kg: string
  is_warmup: boolean
}

export function LogWorkout() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { toast } = useToast()
  const [type, setType] = useState<WorkoutType>('run')
  const [success, setSuccess] = useState(false)

  // Shared
  const [startedAt, setStartedAt] = useState(() => new Date().toISOString().slice(0, 16))
  const [durationMin, setDurationMin] = useState('')
  const [rpe, setRpe] = useState('')

  // Run
  const [distanceKm, setDistanceKm] = useState('')
  const [avgPace, setAvgPace] = useState('')
  const [avgHr, setAvgHr] = useState('')
  const [elevation, setElevation] = useState('')
  const [routeName, setRouteName] = useState('')

  // Gym
  const [template, setTemplate] = useState('')
  const [muscles, setMuscles] = useState('')
  const [sets, setSets] = useState<GymSet[]>([
    { exercise_name: '', reps: '', weight_kg: '', is_warmup: false },
  ])

  const mutation = useMutation({
    mutationFn: () => {
      const durationSec = durationMin ? Math.round(+durationMin * 60) : undefined

      if (type === 'run') {
        return workoutsApi.createRun({
          started_at: new Date(startedAt).toISOString(),
          duration_seconds: durationSec ?? 0,
          distance_meters: +distanceKm * 1000,
          avg_pace_sec_per_km: avgPace
            ? (() => { const [m, s] = avgPace.split(':').map(Number); return m * 60 + (s || 0) })()
            : undefined,
          avg_hr: avgHr ? +avgHr : undefined,
          elevation_gain_m: elevation ? +elevation : undefined,
          perceived_effort: rpe ? +rpe : undefined,
          route_name: routeName || undefined,
        })
      } else {
        return workoutsApi.createGym({
          started_at: new Date(startedAt).toISOString(),
          duration_seconds: durationSec ?? 3600,
          workout_template: template || undefined,
          muscle_groups: muscles ? muscles.split(',').map(s => s.trim()) : undefined,
          perceived_effort: rpe ? +rpe : undefined,
          sets: sets
            .filter(s => s.exercise_name)
            .map((s, i) => ({
              set_number: i + 1,
              exercise_name: s.exercise_name,
              reps: s.reps ? +s.reps : undefined,
              weight_kg: s.weight_kg ? +s.weight_kg : undefined,
              is_warmup: s.is_warmup,
            })),
        })
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workouts'] })
      qc.invalidateQueries({ queryKey: ['analytics-summary'] })
      toast('success', 'Workout logged! Pipeline is processing your data.')
      setSuccess(true)
      setTimeout(() => navigate('/workouts'), 2000)
    },
    onError: () => toast('error', 'Failed to log workout'),
  })

  const inputCls = 'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors'
  const labelCls = 'block text-xs text-slate-400 mb-1'

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <CheckCircle size={48} className="text-green-400" />
        <p className="text-white font-medium">Workout logged!</p>
        <p className="text-slate-400 text-sm">Pipeline is processing your data…</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Log Workout</h1>
        <p className="text-sm text-slate-400 mt-0.5">Record your training session</p>
      </div>

      {/* Type toggle */}
      <div className="flex gap-2 p-1 bg-slate-800 rounded-xl w-fit">
        {(['run', 'gym'] as WorkoutType[]).map(t => (
          <button
            key={t}
            onClick={() => setType(t)}
            className={`px-5 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${
              type === t ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <form
        onSubmit={e => { e.preventDefault(); mutation.mutate() }}
        className="space-y-5"
      >
        {/* Shared fields */}
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-4">
          <h2 className="text-sm font-medium text-slate-300">Session details</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Start time</label>
              <input
                type="datetime-local"
                value={startedAt}
                onChange={e => setStartedAt(e.target.value)}
                required
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Duration (min)</label>
              <input
                type="number"
                value={durationMin}
                onChange={e => setDurationMin(e.target.value)}
                className={inputCls}
                placeholder="57"
              />
            </div>
          </div>
          <div>
            <label className={labelCls}>Perceived effort (RPE 1–10)</label>
            <input
              type="number"
              min={1} max={10}
              value={rpe}
              onChange={e => setRpe(e.target.value)}
              className={inputCls}
              placeholder="7"
            />
          </div>
        </div>

        {/* Run-specific */}
        {type === 'run' && (
          <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-4">
            <h2 className="text-sm font-medium text-slate-300">Run data</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Distance (km) *</label>
                <input
                  type="number" step="0.01"
                  value={distanceKm}
                  onChange={e => setDistanceKm(e.target.value)}
                  required
                  className={inputCls}
                  placeholder="10.5"
                />
              </div>
              <div>
                <label className={labelCls}>Avg pace (mm:ss /km)</label>
                <input
                  type="text"
                  value={avgPace}
                  onChange={e => setAvgPace(e.target.value)}
                  className={inputCls}
                  placeholder="5:30"
                />
              </div>
              <div>
                <label className={labelCls}>Avg heart rate (bpm)</label>
                <input
                  type="number"
                  value={avgHr}
                  onChange={e => setAvgHr(e.target.value)}
                  className={inputCls}
                  placeholder="148"
                />
              </div>
              <div>
                <label className={labelCls}>Elevation gain (m)</label>
                <input
                  type="number"
                  value={elevation}
                  onChange={e => setElevation(e.target.value)}
                  className={inputCls}
                  placeholder="45"
                />
              </div>
            </div>
            <div>
              <label className={labelCls}>Route name</label>
              <input
                value={routeName}
                onChange={e => setRouteName(e.target.value)}
                className={inputCls}
                placeholder="Morning loop"
              />
            </div>
          </div>
        )}

        {/* Gym-specific */}
        {type === 'gym' && (
          <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-4">
            <h2 className="text-sm font-medium text-slate-300">Gym data</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Template / session type</label>
                <input
                  value={template}
                  onChange={e => setTemplate(e.target.value)}
                  className={inputCls}
                  placeholder="Push A"
                />
              </div>
              <div>
                <label className={labelCls}>Muscle groups (comma-sep)</label>
                <input
                  value={muscles}
                  onChange={e => setMuscles(e.target.value)}
                  className={inputCls}
                  placeholder="chest, triceps"
                />
              </div>
            </div>

            {/* Sets */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs text-slate-400">Sets</label>
                <button
                  type="button"
                  onClick={() => setSets(s => [...s, { exercise_name: '', reps: '', weight_kg: '', is_warmup: false }])}
                  className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
                >
                  <Plus size={12} /> Add set
                </button>
              </div>

              <div className="grid grid-cols-[1fr_80px_80px_auto_auto] gap-2 text-xs text-slate-500 px-1">
                <span>Exercise</span><span className="text-center">Reps</span>
                <span className="text-center">kg</span>
                <span className="text-center">Warmup</span>
                <span />
              </div>

              {sets.map((s, i) => (
                <div key={i} className="grid grid-cols-[1fr_80px_80px_auto_auto] gap-2 items-center">
                  <input
                    value={s.exercise_name}
                    onChange={e => setSets(prev => prev.map((p, j) => j === i ? { ...p, exercise_name: e.target.value } : p))}
                    className={inputCls}
                    placeholder="Bench press"
                  />
                  <input
                    type="number"
                    value={s.reps}
                    onChange={e => setSets(prev => prev.map((p, j) => j === i ? { ...p, reps: e.target.value } : p))}
                    className={inputCls + ' text-center'}
                    placeholder="5"
                  />
                  <input
                    type="number" step="0.5"
                    value={s.weight_kg}
                    onChange={e => setSets(prev => prev.map((p, j) => j === i ? { ...p, weight_kg: e.target.value } : p))}
                    className={inputCls + ' text-center'}
                    placeholder="80"
                  />
                  <input
                    type="checkbox"
                    checked={s.is_warmup}
                    onChange={e => setSets(prev => prev.map((p, j) => j === i ? { ...p, is_warmup: e.target.checked } : p))}
                    className="w-4 h-4 accent-indigo-500 mx-auto"
                  />
                  <button
                    type="button"
                    onClick={() => setSets(prev => prev.filter((_, j) => j !== i))}
                    className="text-slate-600 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {mutation.isError && (
          <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
            {(mutation.error as any)?.response?.data?.detail?.errors?.join(', ') || 'Failed to log workout'}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
        >
          {mutation.isPending ? 'Saving…' : 'Log workout'}
        </button>
      </form>
    </div>
  )
}
