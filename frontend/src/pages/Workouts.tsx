import { useState, useEffect, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { workoutsApi } from '../api/workouts'
import { Badge } from '../components/Badge'
import { Spinner } from '../components/Spinner'
import { WorkoutDetail } from '../components/WorkoutDetail'
import { formatPace, formatDistance, formatDuration, formatDate, paceZoneColor } from '../lib/utils'
import { Plus, Heart, Zap, TrendingUp, Calendar, List, ChevronLeft, ChevronRight } from 'lucide-react'
import type { Workout } from '../types'

const PAGE_SIZE = 20

// ── Workout card ──────────────────────────────────────────────────────────────

function WorkoutRow({ w, onClick, hasPR }: { w: Workout; onClick: () => void; hasPR?: boolean }) {
  const isRun = w.workout_type === 'run'
  const workingSets = w.sets?.filter(s => !s.is_warmup) ?? []
  const exerciseCount = new Set(w.sets?.map(s => s.exercise_name) ?? []).size

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-slate-800/40 border border-slate-700/60 rounded-xl p-4 hover:border-indigo-500/40 hover:bg-slate-800/70 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${isRun ? 'bg-blue-500/20' : 'bg-purple-500/20'}`}>
            {isRun
              ? <TrendingUp size={16} className="text-blue-400" />
              : <Zap size={16} className="text-purple-400" />
            }
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={w.workout_type as any}>{w.workout_type.toUpperCase()}</Badge>
              {!isRun && w.workout_template && (
                <span className="text-xs font-medium text-purple-300 bg-purple-500/10 border border-purple-500/20 rounded px-2 py-0.5">
                  {w.workout_template}
                </span>
              )}
              {isRun && w.pace_zone && (
                <span className={`text-xs font-medium ${paceZoneColor(w.pace_zone)}`}>
                  {w.pace_zone.replace('_', ' ')}
                </span>
              )}
              {hasPR && (
                <span className="text-xs font-bold text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 rounded px-2 py-0.5">
                  🏆 PR
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{formatDate(w.started_at)}</p>
          </div>
        </div>
        <Badge variant={w.status as any}>{w.status}</Badge>
      </div>

      {/* Metrics grid */}
      <div className={`grid gap-3 mt-3 ${isRun ? 'grid-cols-4' : 'grid-cols-3'}`}>
        {isRun ? (
          <>
            <div>
              <p className="text-xs text-slate-500">Distance</p>
              <p className="text-sm font-medium text-white">{formatDistance(w.distance_meters)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Avg pace</p>
              <p className="text-sm font-medium text-white">{formatPace(w.avg_pace_sec_per_km)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Avg HR</p>
              <p className="text-sm font-medium text-white">
                {w.avg_hr ? <span className="flex items-center gap-1"><Heart size={11} className="text-red-400" />{w.avg_hr} bpm</span> : '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-sm font-medium text-white">{formatDuration(w.duration_seconds)}</p>
            </div>
          </>
        ) : (
          <>
            <div>
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-sm font-medium text-white">{formatDuration(w.duration_seconds)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Exercises</p>
              <p className="text-sm font-medium text-white">
                {exerciseCount > 0 ? `${exerciseCount} exercises` : (w.muscle_groups?.join(', ') || '—')}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Working sets</p>
              <p className="text-sm font-medium text-white">{workingSets.length > 0 ? `${workingSets.length} sets` : '—'}</p>
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-700/50">
        {w.tss != null && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Zap size={11} className="text-yellow-400" />
            TSS {Number(w.tss).toFixed(0)}
          </span>
        )}
        {w.perceived_effort != null && (
          <span className="text-xs text-slate-400">RPE {w.perceived_effort}/10</span>
        )}
      </div>
    </button>
  )
}

// ── Calendar ──────────────────────────────────────────────────────────────────

function WorkoutCalendar({
  dayMap,
  onSelectDay,
}: {
  dayMap: Record<string, Workout[]>
  onSelectDay: (date: string) => void
}) {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth()) // 0-indexed
  const [selected, setSelected] = useState<string | null>(null)

  const monthLabel = new Date(year, month, 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (month === 11) { setMonth(0); setYear(y => y + 1) }
    else setMonth(m => m + 1)
  }

  // Build calendar grid
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  // Start grid on Monday (ISO week)
  const startOffset = (firstDay.getDay() + 6) % 7 // Mon=0
  const totalCells = Math.ceil((startOffset + lastDay.getDate()) / 7) * 7

  const cells: (Date | null)[] = []
  for (let i = 0; i < totalCells; i++) {
    const dayNum = i - startOffset + 1
    if (dayNum < 1 || dayNum > lastDay.getDate()) cells.push(null)
    else cells.push(new Date(year, month, dayNum))
  }

  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  const todayStr = fmt(today)

  const handleClick = (d: Date) => {
    const key = fmt(d)
    setSelected(key)
    onSelectDay(key)
  }

  return (
    <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
      {/* Month navigation */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={prevMonth} className="p-1 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition-colors">
          <ChevronLeft size={16} />
        </button>
        <span className="text-sm font-medium text-white">{monthLabel}</span>
        <button onClick={nextMonth} className="p-1 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition-colors">
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'].map(d => (
          <div key={d} className="text-center text-xs text-slate-500 py-1">{d}</div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((d, i) => {
          if (!d) return <div key={i} className="aspect-square" />
          const key = fmt(d)
          const dayWorkouts = dayMap[key] ?? []
          const hasRun = dayWorkouts.some(w => w.workout_type === 'run')
          const hasGym = dayWorkouts.some(w => w.workout_type === 'gym')
          const isToday = key === todayStr
          const isSelected = key === selected

          return (
            <button
              key={key}
              onClick={() => handleClick(d)}
              className={`aspect-square flex flex-col items-center justify-center rounded-lg transition-colors relative ${
                isSelected ? 'bg-indigo-600/30 border border-indigo-500' :
                isToday ? 'ring-2 ring-indigo-500 ring-inset bg-slate-800' :
                dayWorkouts.length > 0 ? 'bg-slate-800 hover:bg-slate-700' :
                'hover:bg-slate-800/60'
              }`}
            >
              <span className={`text-xs ${isToday ? 'font-bold text-indigo-400' : dayWorkouts.length > 0 ? 'text-white' : 'text-slate-500'}`}>
                {d.getDate()}
              </span>
              {dayWorkouts.length > 0 && (
                <div className="flex gap-0.5 mt-0.5">
                  {hasRun && <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />}
                  {hasGym && <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />}
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-3 justify-center">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-blue-400" /> Run
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-purple-400" /> Gym
        </div>
      </div>
    </div>
  )
}

// ── Main Workouts page ────────────────────────────────────────────────────────

export function Workouts() {
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('list')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [accumulated, setAccumulated] = useState<Workout[]>([])
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const prevFilter = useRef(typeFilter)

  // PR map for badge detection
  const [prMap, setPrMap] = useState<Record<string, number>>({})
  useEffect(() => {
    workoutsApi.exercisePRs().then(r => {
      const map: Record<string, number> = {}
      for (const pr of r.data) map[pr.exercise_name] = pr.estimated_1rm
      setPrMap(map)
    }).catch(() => {})
  }, [])

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['workouts', typeFilter, cursor],
    queryFn: () =>
      workoutsApi.list({
        workout_type: typeFilter === 'all' ? undefined : typeFilter,
        limit: PAGE_SIZE,
        cursor,
      }).then(r => r.data),
  })

  // For calendar: fetch a large batch independent of filters/pagination
  const { data: calendarData } = useQuery({
    queryKey: ['workouts-calendar'],
    queryFn: () => workoutsApi.list({ limit: 100 }).then(r => r.data),
    enabled: viewMode === 'calendar',
  })

  useEffect(() => {
    if (!data) return
    if (prevFilter.current !== typeFilter) {
      prevFilter.current = typeFilter
      setAccumulated(data.data)
    } else if (cursor) {
      setAccumulated(prev => {
        const ids = new Set(prev.map(w => w.id))
        return [...prev, ...data.data.filter(w => !ids.has(w.id))]
      })
    } else {
      setAccumulated(data.data)
    }
  }, [data])

  const handleFilterChange = (newFilter: string) => {
    if (newFilter === typeFilter) return
    setCursor(undefined)
    setTypeFilter(newFilter)
  }

  // Build dayMap for calendar
  const dayMap = useMemo(() => {
    const map: Record<string, Workout[]> = {}
    for (const w of calendarData?.data ?? []) {
      const day = w.started_at.slice(0, 10)
      if (!map[day]) map[day] = []
      map[day].push(w)
    }
    return map
  }, [calendarData])

  // PR detection: does a gym workout contain a set matching the current PR 1RM?
  const hasPR = (w: Workout): boolean => {
    if (w.workout_type !== 'gym') return false
    for (const s of w.sets ?? []) {
      if (s.is_warmup || !s.weight_kg || !s.reps) continue
      const e1rm = s.reps === 1 ? s.weight_kg : s.weight_kg * (1 + s.reps / 30)
      const best = prMap[s.exercise_name]
      if (best && Math.abs(e1rm - best) < 0.5) return true
    }
    return false
  }

  const dayWorkouts = selectedDay ? (dayMap[selectedDay] ?? []) : []

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Workouts</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {data?.meta.total != null ? `${data.meta.total} total logged` : '—'}
          </p>
        </div>
        <Link
          to="/log"
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus size={15} /> Log workout
        </Link>
      </div>

      {/* Controls: view toggle + type filter */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Type filter (list view only) */}
        {viewMode === 'list' && (
          <div className="flex gap-2">
            {['all', 'run', 'gym'].map(t => (
              <button
                key={t}
                onClick={() => handleFilterChange(t)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
                  typeFilter === t
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        )}
        {viewMode === 'calendar' && <div />}

        {/* View toggle */}
        <div className="flex gap-1 p-1 bg-slate-800 rounded-lg">
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'list' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            <List size={13} /> List
          </button>
          <button
            onClick={() => setViewMode('calendar')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'calendar' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Calendar size={13} /> Calendar
          </button>
        </div>
      </div>

      {/* ── Calendar view ── */}
      {viewMode === 'calendar' && (
        <div className="space-y-4">
          <WorkoutCalendar
            dayMap={dayMap}
            onSelectDay={day => setSelectedDay(prev => prev === day ? null : day)}
          />

          {/* Selected day workouts */}
          {selectedDay && (
            <div>
              <p className="text-xs text-slate-500 mb-2">
                {dayWorkouts.length === 0
                  ? `No workouts on ${selectedDay}`
                  : `${dayWorkouts.length} workout${dayWorkouts.length > 1 ? 's' : ''} on ${new Date(selectedDay + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}`
                }
              </p>
              <div className="grid gap-3">
                {dayWorkouts.map(w => (
                  <WorkoutRow key={w.id} w={w} onClick={() => setSelectedId(w.id)} hasPR={hasPR(w)} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── List view ── */}
      {viewMode === 'list' && (
        <>
          {isLoading && !accumulated.length ? (
            <div className="flex justify-center py-16"><Spinner size={28} /></div>
          ) : !accumulated.length ? (
            <div className="text-center py-16">
              <p className="text-slate-500 mb-3">No workouts found</p>
              <Link to="/log" className="text-indigo-400 hover:text-indigo-300 text-sm">
                Log your first workout →
              </Link>
            </div>
          ) : (
            <>
              <div className="grid gap-3">
                {accumulated.map(w => (
                  <WorkoutRow key={w.id} w={w} onClick={() => setSelectedId(w.id)} hasPR={hasPR(w)} />
                ))}
              </div>

              {data?.meta.has_more && (
                <div className="flex justify-center pt-2">
                  <button
                    onClick={() => data.meta.next_cursor && setCursor(data.meta.next_cursor)}
                    disabled={isFetching}
                    className="flex items-center gap-2 text-sm text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isFetching ? <><Spinner size={14} /> Loading…</> : 'Load more'}
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {selectedId && (
        <WorkoutDetail id={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  )
}
