import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { workoutsApi } from '../api/workouts'
import { useToast } from '../hooks/useToast'
import { CheckCircle, Plus, Trash2, Copy, History, ArrowRight } from 'lucide-react'
import { formatWeekDate } from '../lib/utils'

// ── types ──────────────────────────────────────────────────────────────────

type WorkoutType = 'run' | 'gym'

interface SetRow {
  id: string
  reps: string
  weight_kg: string
  is_warmup: boolean
}

interface Exercise {
  id: string
  name: string
  sets: SetRow[]
}

function makeSet(prev?: SetRow): SetRow {
  return {
    id: Math.random().toString(36).slice(2),
    reps: prev?.reps ?? '',
    weight_kg: prev?.weight_kg ?? '',
    is_warmup: false,
  }
}

function makeExercise(): Exercise {
  return { id: Math.random().toString(36).slice(2), name: '', sets: [makeSet()] }
}

// ── RPE selector ───────────────────────────────────────────────────────────

const RPE_LABELS: Record<number, string> = {
  1: 'Very easy', 2: 'Very easy',
  3: 'Easy',      4: 'Easy',
  5: 'Moderate',  6: 'Moderate',
  7: 'Hard',      8: 'Hard',
  9: 'Very hard', 10: 'Max effort',
}

const RPE_COLORS: Record<number, string> = {
  1: 'bg-green-700 border-green-600',   2: 'bg-green-700 border-green-600',
  3: 'bg-green-600 border-green-500',   4: 'bg-green-600 border-green-500',
  5: 'bg-yellow-700 border-yellow-600', 6: 'bg-yellow-600 border-yellow-500',
  7: 'bg-orange-600 border-orange-500', 8: 'bg-orange-500 border-orange-400',
  9: 'bg-red-600 border-red-500',       10: 'bg-red-700 border-red-600',
}

function RpeSelector({ value, onChange }: { value: number | null; onChange: (v: number) => void }) {
  return (
    <div className="space-y-2">
      <div className="flex gap-1.5">
        {[1,2,3,4,5,6,7,8,9,10].map(n => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            title={RPE_LABELS[n]}
            className={`flex-1 h-9 rounded-lg border text-sm font-bold transition-all ${
              value === n
                ? RPE_COLORS[n] + ' text-white scale-105'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      <div className="flex justify-between text-xs text-slate-500">
        <span>Very easy</span>
        <span>Moderate</span>
        <span>Hard</span>
        <span>Max effort</span>
      </div>
      {value && (
        <p className="text-xs text-slate-400 text-center">
          RPE <span className="font-semibold text-white">{value}</span> — {RPE_LABELS[value]}
        </p>
      )}
    </div>
  )
}

// ── chip components ────────────────────────────────────────────────────────

function ChipGroup<T extends string>({
  label, options, selected, onToggle,
}: {
  label: string
  options: T[]
  selected: T[]
  onToggle: (v: T) => void
}) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map(o => {
          const active = selected.includes(o)
          return (
            <button
              key={o}
              type="button"
              onClick={() => onToggle(o)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                active
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500'
              }`}
            >
              {o}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── ExercisePicker ─────────────────────────────────────────────────────────

type HistoryMap = Record<string, { date: string; sets: { reps: number | null; weight_kg: number | null }[] }>

function ExercisePicker({
  value,
  historyMap,
  onChange,
  onPickFromHistory,
}: {
  value: string
  historyMap: HistoryMap
  onChange: (name: string) => void
  onPickFromHistory: (name: string, sets: SetRow[]) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const lower = value.toLowerCase()
  const matches = Object.keys(historyMap)
    .filter(k => lower.length === 0 || k.toLowerCase().includes(lower))
    .slice(0, 8)

  const pick = (name: string) => {
    const history = historyMap[name]
    const sets: SetRow[] = history
      ? history.sets.map(s => ({
          id: Math.random().toString(36).slice(2),
          reps: s.reps?.toString() ?? '',
          weight_kg: s.weight_kg?.toString() ?? '',
          is_warmup: false,
        }))
      : [makeSet()]
    onPickFromHistory(name, sets)
    setOpen(false)
  }

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative flex-1">
      <input
        value={value}
        onChange={e => { onChange(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        className="w-full bg-transparent text-sm font-medium text-white placeholder-slate-500 focus:outline-none"
        placeholder="Exercise name…"
        autoComplete="off"
      />
      {open && matches.length > 0 && (
        <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded-xl shadow-xl max-h-56 overflow-y-auto">
          {value.length === 0 && (
            <p className="px-3 pt-2 pb-1 text-xs text-slate-500">Your exercises — tap to add with previous weights</p>
          )}
          {matches.map(name => {
            const h = historyMap[name]
            const preview = h.sets.slice(0, 3).map(s => `${s.reps}×${s.weight_kg}`).join(' · ')
            return (
              <button
                key={name}
                type="button"
                onMouseDown={() => pick(name)}
                className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-slate-700 transition-colors text-left"
              >
                <div>
                  <span className="text-sm text-white">{name}</span>
                  <p className="text-xs text-slate-500 mt-0.5">{preview}</p>
                </div>
                <span className="text-xs text-slate-600">{formatWeekDate(h.date)}</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── constants ──────────────────────────────────────────────────────────────

// A/B variants so users can track PPL rotation
const SESSION_TYPES = ['Push A', 'Push B', 'Pull A', 'Pull B', 'Legs A', 'Legs B', 'Upper', 'Lower', 'Full Body', 'Cardio', 'Other']
const MUSCLE_OPTIONS = ['Chest', 'Back', 'Shoulders', 'Biceps', 'Triceps', 'Core', 'Quads', 'Hamstrings', 'Glutes', 'Calves']

// ── main component ──────────────────────────────────────────────────────────

export function LogWorkout() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { toast } = useToast()
  const [type, setType] = useState<WorkoutType>('run')
  const [success, setSuccess] = useState(false)

  // Shared
  const [startedAt, setStartedAt] = useState(() => new Date().toISOString().slice(0, 16))
  const [durationMin, setDurationMin] = useState('')
  const [rpe, setRpe] = useState<number | null>(null)
  const [notes, setNotes] = useState('')

  // Run
  const [distanceKm, setDistanceKm] = useState('')
  const [avgPace, setAvgPace] = useState('')
  const [avgHr, setAvgHr] = useState('')
  const [elevation, setElevation] = useState('')
  const [routeName, setRouteName] = useState('')

  // Gym
  const [sessionType, setSessionType] = useState<string[]>([])
  const [muscles, setMuscles] = useState<string[]>([])
  const [exercises, setExercises] = useState<Exercise[]>([makeExercise()])

  // Exercise history + PR maps (fetched once on mount)
  const [historyMap, setHistoryMap] = useState<HistoryMap>({})
  const [prMap, setPrMap] = useState<Record<string, { estimated_1rm: number; weight_kg: number; reps: number }>>({})
  const [nextSession, setNextSession] = useState<{ label: string; date: string } | null>(null)

  useEffect(() => {
    workoutsApi.exerciseHistory().then(r => {
      const map: HistoryMap = {}
      for (const item of r.data) map[item.exercise_name] = { date: item.date, sets: item.sets }
      setHistoryMap(map)
    }).catch(() => {})
    workoutsApi.exercisePRs().then(r => {
      const map: typeof prMap = {}
      for (const pr of r.data) map[pr.exercise_name] = { estimated_1rm: pr.estimated_1rm, weight_kg: pr.weight_kg, reps: pr.reps }
      setPrMap(map)
    }).catch(() => {})
    // A/B rotation: find the last gym session's template
    workoutsApi.list({ workout_type: 'gym', limit: 5 }).then(r => {
      const lastTemplate = r.data.data.find(w => w.workout_template)?.workout_template
      if (!lastTemplate) return
      // Suggest the other variant: Push A→Push B, Pull B→Pull A, Legs A→Legs B, etc.
      const match = lastTemplate.match(/^(Push|Pull|Legs|Upper|Lower)\s*([AB])$/i)
      if (match) {
        const base = match[1]
        const variant = match[2].toUpperCase() === 'A' ? 'B' : 'A'
        const lastDate = r.data.data.find(w => w.workout_template === lastTemplate)?.started_at ?? ''
        setNextSession({ label: `${base} ${variant}`, date: lastDate })
      }
    }).catch(() => {})
  }, [])

  // ── exercise helpers ─────────────────────────────────────────────────────

  const updateExerciseName = (exId: string, name: string) =>
    setExercises(prev => prev.map(e => e.id === exId ? { ...e, name } : e))

  const updateSet = (exId: string, setId: string, field: keyof SetRow, value: string | boolean) =>
    setExercises(prev => prev.map(e =>
      e.id === exId
        ? { ...e, sets: e.sets.map(s => s.id === setId ? { ...s, [field]: value } : s) }
        : e
    ))

  const addSet = (exId: string) =>
    setExercises(prev => prev.map(e => {
      if (e.id !== exId) return e
      const last = e.sets[e.sets.length - 1]
      return { ...e, sets: [...e.sets, makeSet(last)] }
    }))

  const removeSet = (exId: string, setId: string) =>
    setExercises(prev => prev.map(e =>
      e.id === exId ? { ...e, sets: e.sets.filter(s => s.id !== setId) } : e
    ).filter(e => e.sets.length > 0))

  const removeExercise = (exId: string) =>
    setExercises(prev => prev.filter(e => e.id !== exId))

  const pickExercise = (exId: string, name: string, sets: SetRow[]) => {
    setExercises(prev => prev.map(e =>
      e.id === exId ? { ...e, name, sets: sets.length > 0 ? sets : e.sets } : e
    ))
  }

  const duplicateExercise = (exId: string) =>
    setExercises(prev => {
      const idx = prev.findIndex(e => e.id === exId)
      if (idx < 0) return prev
      const copy: Exercise = { ...prev[idx], id: Math.random().toString(36).slice(2), sets: prev[idx].sets.map(s => ({ ...s, id: Math.random().toString(36).slice(2) })) }
      return [...prev.slice(0, idx + 1), copy, ...prev.slice(idx + 1)]
    })

  // live volume calculation
  const totalVolume = exercises.reduce((sum, e) =>
    sum + e.sets.reduce((s2, s) =>
      s2 + (s.is_warmup ? 0 : (+s.reps || 0) * (+s.weight_kg || 0)), 0), 0)

  const workingSets = exercises.reduce((sum, e) => sum + e.sets.filter(s => !s.is_warmup).length, 0)

  // ── submit ───────────────────────────────────────────────────────────────

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
          perceived_effort: rpe ?? undefined,
          route_name: routeName || undefined,
          notes: notes || undefined,
        })
      } else {
        // flatten exercise blocks → flat set list
        let setNum = 1
        const flatSets = exercises
          .filter(e => e.name)
          .flatMap(e =>
            e.sets.map(s => ({
              set_number: setNum++,
              exercise_name: e.name,
              reps: s.reps ? +s.reps : undefined,
              weight_kg: s.weight_kg ? +s.weight_kg : undefined,
              is_warmup: s.is_warmup,
            }))
          )

        return workoutsApi.createGym({
          started_at: new Date(startedAt).toISOString(),
          duration_seconds: durationSec ?? 3600,
          workout_template: sessionType[0] || undefined,
          muscle_groups: muscles.length ? muscles.map(m => m.toLowerCase()) : undefined,
          perceived_effort: rpe ?? undefined,
          notes: notes || undefined,
          sets: flatSets,
        })
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workouts'] })
      qc.invalidateQueries({ queryKey: ['analytics-summary'] })

      // PR detection for gym workouts
      if (type === 'gym') {
        const newPrs: string[] = []
        for (const ex of exercises.filter(e => e.name)) {
          const workingSets = ex.sets.filter(s => !s.is_warmup && s.weight_kg && s.reps)
          for (const s of workingSets) {
            const w = +s.weight_kg, r = +s.reps
            if (w > 0 && r > 0) {
              const e1rm = r === 1 ? w : w * (1 + r / 30)
              const existing = prMap[ex.name]?.estimated_1rm ?? 0
              if (e1rm > existing + 0.1) {
                newPrs.push(`${ex.name}: ${e1rm.toFixed(1)} kg est. 1RM`)
              }
            }
          }
        }
        if (newPrs.length > 0) {
          newPrs.forEach(pr => toast('success', `🏆 New PR! ${pr}`))
        }
      }

      toast('success', 'Workout logged!')
      setSuccess(true)
      setTimeout(() => navigate('/workouts'), 2000)
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map((e: any) => e.msg).join('. ')
        : typeof detail === 'string' ? detail : 'Failed to log workout'
      toast('error', msg)
    },
  })

  const inputCls = 'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors'
  const labelCls = 'block text-xs text-slate-400 mb-1'
  const sectionCls = 'bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-4'

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <CheckCircle size={48} className="text-green-400" />
        <p className="text-white font-medium">Workout logged!</p>
        <p className="text-slate-400 text-sm">Processing your data…</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Log Workout</h1>
        <p className="text-sm text-slate-400 mt-0.5">Record your training session</p>
      </div>

      {/* Type toggle */}
      <div className="flex gap-2 p-1 bg-slate-800 rounded-xl w-fit">
        {(['run', 'gym'] as WorkoutType[]).map(t => (
          <button key={t} type="button" onClick={() => setType(t)}
            className={`px-6 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${
              type === t ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {t === 'run' ? '🏃 Run' : '🏋️ Gym'}
          </button>
        ))}
      </div>

      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }} className="space-y-4">

        {/* ── Session meta ─────────────────────────────────────────────── */}
        <div className={sectionCls}>
          <h2 className="text-sm font-medium text-slate-300">When</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Date & time</label>
              <input type="datetime-local" value={startedAt}
                onChange={e => setStartedAt(e.target.value)} required className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Duration (minutes)</label>
              <input type="number" value={durationMin}
                onChange={e => setDurationMin(e.target.value)}
                className={inputCls} placeholder="60" />
            </div>
          </div>
        </div>

        {/* ── Run specifics ─────────────────────────────────────────────── */}
        {type === 'run' && (
          <div className={sectionCls}>
            <h2 className="text-sm font-medium text-slate-300">Run details</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Distance (km) *</label>
                <input type="number" step="0.01" value={distanceKm}
                  onChange={e => setDistanceKm(e.target.value)} required
                  className={inputCls} placeholder="10.0" />
              </div>
              <div>
                <label className={labelCls}>Avg pace (min:sec / km)</label>
                <input type="text" value={avgPace}
                  onChange={e => setAvgPace(e.target.value)}
                  className={inputCls} placeholder="5:30" />
              </div>
              <div>
                <label className={labelCls}>Avg heart rate (bpm)</label>
                <input type="number" value={avgHr}
                  onChange={e => setAvgHr(e.target.value)}
                  className={inputCls} placeholder="148" />
              </div>
              <div>
                <label className={labelCls}>Elevation gain (m)</label>
                <input type="number" value={elevation}
                  onChange={e => setElevation(e.target.value)}
                  className={inputCls} placeholder="45" />
              </div>
            </div>
            <div>
              <label className={labelCls}>Route name</label>
              <input value={routeName} onChange={e => setRouteName(e.target.value)}
                className={inputCls} placeholder="Morning loop, Park 5K…" />
            </div>
          </div>
        )}

        {/* ── Gym: A/B suggestion + session type + muscles ─────────────── */}
        {type === 'gym' && (
          <div className={sectionCls}>
            {/* A/B rotation suggestion */}
            {nextSession && (
              <div className="flex items-center justify-between bg-indigo-600/10 border border-indigo-500/20 rounded-lg px-3 py-2.5">
                <div className="text-xs">
                  <span className="text-slate-400">Last session: </span>
                  <span className="text-slate-300">
                    {SESSION_TYPES.find(s => s === sessionType[0]) ?? 'Gym'} on {formatWeekDate(nextSession.date)}
                  </span>
                  <span className="text-slate-400"> → Next up: </span>
                  <span className="text-white font-medium">{nextSession.label}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSessionType([nextSession.label])}
                  className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-600/20 px-2 py-1 rounded transition-colors ml-3"
                >
                  <ArrowRight size={11} /> Use
                </button>
              </div>
            )}
            <ChipGroup
              label="Session type"
              options={SESSION_TYPES as any}
              selected={sessionType}
              onToggle={v => setSessionType(prev => prev.includes(v) ? prev.filter(x => x !== v) : [v])}
            />
            <ChipGroup
              label="Muscle groups"
              options={MUSCLE_OPTIONS as any}
              selected={muscles}
              onToggle={v => setMuscles(prev => prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v])}
            />
          </div>
        )}

        {/* ── Gym: exercises ────────────────────────────────────────────── */}
        {type === 'gym' && (
          <div className="space-y-3">
            {/* Volume summary */}
            {workingSets > 0 && (
              <div className="flex gap-4 px-1 text-xs text-slate-500">
                <span><span className="text-white font-medium">{exercises.filter(e=>e.name).length}</span> exercises</span>
                <span><span className="text-white font-medium">{workingSets}</span> working sets</span>
                <span><span className="text-white font-medium">{Math.round(totalVolume).toLocaleString()}</span> kg total volume</span>
              </div>
            )}

            {exercises.map((ex, exIdx) => (
              <div key={ex.id} className="bg-slate-800/60 border border-slate-700 rounded-xl overflow-hidden">
                {/* Exercise header with autocomplete picker */}
                <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-700/60">
                  <span className="text-xs text-slate-500 font-medium w-5">{exIdx + 1}</span>
                  <ExercisePicker
                    value={ex.name}
                    historyMap={historyMap}
                    onChange={name => updateExerciseName(ex.id, name)}
                    onPickFromHistory={(name, sets) => pickExercise(ex.id, name, sets)}
                  />
                  <button type="button" onClick={() => duplicateExercise(ex.id)}
                    title="Duplicate exercise"
                    className="text-slate-600 hover:text-slate-300 transition-colors p-1">
                    <Copy size={13} />
                  </button>
                  {exercises.length > 1 && (
                    <button type="button" onClick={() => removeExercise(ex.id)}
                      className="text-slate-600 hover:text-red-400 transition-colors p-1">
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>

                {/* Previous session inline (shown when name is set and matches history) */}
                {ex.name && historyMap[ex.name] && (
                  <div className="px-4 py-1.5 bg-slate-900/40 flex items-center gap-2 text-xs text-slate-500">
                    <History size={10} />
                    <span>
                      Last ({formatWeekDate(historyMap[ex.name].date)}):&nbsp;
                      {historyMap[ex.name].sets.slice(0, 4).map((s, i) => (
                        <span key={i}>{i > 0 && ' · '}{s.reps}×{s.weight_kg}kg</span>
                      ))}
                      {historyMap[ex.name].sets.length > 4 && ' …'}
                    </span>
                  </div>
                )}

                {/* Set rows */}
                <div className="px-4 py-2 space-y-1.5">
                  {/* Column headers */}
                  <div className="grid grid-cols-[32px_1fr_1fr_56px_28px] gap-2 text-xs text-slate-600 px-1 pb-0.5">
                    <span className="text-center">Set</span>
                    <span className="text-center">Reps</span>
                    <span className="text-center">Weight (kg)</span>
                    <span className="text-center">Warmup</span>
                    <span />
                  </div>

                  {ex.sets.map((s, sIdx) => (
                    <div key={s.id} className={`grid grid-cols-[32px_1fr_1fr_56px_28px] gap-2 items-center rounded-lg px-1 py-1 ${s.is_warmup ? 'opacity-60' : ''}`}>
                      <span className={`text-xs font-medium text-center rounded-md py-1 ${
                        s.is_warmup ? 'text-slate-500 bg-slate-700/40' : 'text-indigo-300 bg-indigo-600/20'
                      }`}>
                        {s.is_warmup ? 'W' : sIdx - ex.sets.slice(0, sIdx).filter(x => x.is_warmup).length + 1}
                      </span>
                      <input
                        type="number"
                        value={s.reps}
                        onChange={e => updateSet(ex.id, s.id, 'reps', e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white text-center focus:outline-none focus:border-indigo-500 transition-colors"
                        placeholder="—"
                      />
                      <input
                        type="number" step="0.5"
                        value={s.weight_kg}
                        onChange={e => updateSet(ex.id, s.id, 'weight_kg', e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white text-center focus:outline-none focus:border-indigo-500 transition-colors"
                        placeholder="—"
                      />
                      <button
                        type="button"
                        onClick={() => updateSet(ex.id, s.id, 'is_warmup', !s.is_warmup)}
                        className={`text-xs rounded-md py-1 px-2 border transition-colors ${
                          s.is_warmup
                            ? 'bg-amber-600/20 border-amber-500/40 text-amber-300'
                            : 'bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-500'
                        }`}
                      >
                        W
                      </button>
                      <button
                        type="button"
                        onClick={() => removeSet(ex.id, s.id)}
                        disabled={ex.sets.length === 1}
                        className="text-slate-600 hover:text-red-400 transition-colors disabled:opacity-0"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}

                  {/* Add set */}
                  <button
                    type="button"
                    onClick={() => addSet(ex.id)}
                    className="w-full flex items-center justify-center gap-1.5 text-xs text-slate-500 hover:text-indigo-400 py-2 rounded-lg hover:bg-indigo-600/10 transition-colors mt-1"
                  >
                    <Plus size={12} /> Add set
                  </button>
                </div>
              </div>
            ))}

            {/* Add exercise */}
            <button
              type="button"
              onClick={() => setExercises(prev => [...prev, makeExercise()])}
              className="w-full flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white border border-dashed border-slate-700 hover:border-slate-500 rounded-xl py-3 transition-colors"
            >
              <Plus size={15} /> Add exercise
            </button>
          </div>
        )}

        {/* ── RPE ──────────────────────────────────────────────────────── */}
        <div className={sectionCls}>
          <h2 className="text-sm font-medium text-slate-300">How hard was it?</h2>
          <RpeSelector value={rpe} onChange={setRpe} />
        </div>

        {/* ── Notes ────────────────────────────────────────────────────── */}
        <div className={sectionCls}>
          <h2 className="text-sm font-medium text-slate-300">Notes <span className="text-slate-600">(optional)</span></h2>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={2}
            className={inputCls + ' resize-none'}
            placeholder="How did the session feel? Any PRs, injuries, or things to remember…"
          />
        </div>

        {/* ── Submit ───────────────────────────────────────────────────── */}
        <button
          type="submit"
          disabled={mutation.isPending || (type === 'run' && !distanceKm)}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
        >
          {mutation.isPending ? 'Saving…' : 'Log workout'}
        </button>
      </form>
    </div>
  )
}
