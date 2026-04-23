import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { workoutsApi } from '../api/workouts'
import { Badge } from '../components/Badge'
import { Spinner } from '../components/Spinner'
import { WorkoutDetail } from '../components/WorkoutDetail'
import { formatPace, formatDistance, formatDuration, formatDate, paceZoneColor } from '../lib/utils'
import { Plus, Heart, Zap, TrendingUp } from 'lucide-react'
import type { Workout } from '../types'

const PAGE_SIZE = 20

function WorkoutRow({ w, onClick }: { w: Workout; onClick: () => void }) {
  const isRun = w.workout_type === 'run'

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
            <div className="flex items-center gap-2">
              <Badge variant={w.workout_type as any}>{w.workout_type.toUpperCase()}</Badge>
              {w.pace_zone && (
                <span className={`text-xs font-medium ${paceZoneColor(w.pace_zone)}`}>
                  {w.pace_zone}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{formatDate(w.started_at)}</p>
          </div>
        </div>
        <Badge variant={w.status as any}>{w.status}</Badge>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-3">
        {isRun ? (
          <>
            <div>
              <p className="text-xs text-slate-500">Distance</p>
              <p className="text-sm font-medium text-white">{formatDistance(w.distance_meters)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Avg Pace</p>
              <p className="text-sm font-medium text-white">{formatPace(w.avg_pace_sec_per_km)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-sm font-medium text-white">{formatDuration(w.duration_seconds)}</p>
            </div>
          </>
        ) : (
          <>
            <div>
              <p className="text-xs text-slate-500">Volume</p>
              <p className="text-sm font-medium text-white">
                {w.total_volume_kg ? `${w.total_volume_kg.toLocaleString()} kg` : '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-sm font-medium text-white">{formatDuration(w.duration_seconds)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Muscles</p>
              <p className="text-sm font-medium text-white truncate">
                {w.muscle_groups?.join(', ') || '—'}
              </p>
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-700/50">
        {w.avg_hr != null && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Heart size={11} className="text-red-400" />
            {w.avg_hr} bpm
          </span>
        )}
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

export function Workouts() {
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [accumulated, setAccumulated] = useState<Workout[]>([])
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const prevFilter = useRef(typeFilter)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['workouts', typeFilter, cursor],
    queryFn: () =>
      workoutsApi.list({
        workout_type: typeFilter === 'all' ? undefined : typeFilter,
        limit: PAGE_SIZE,
        cursor,
      }).then(r => r.data),
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

  const loadMore = () => {
    if (data?.meta.next_cursor) setCursor(data.meta.next_cursor)
  }

  return (
    <div className="space-y-5">
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
          <Plus size={15} />
          Log workout
        </Link>
      </div>

      {/* Filter tabs */}
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
              <WorkoutRow key={w.id} w={w} onClick={() => setSelectedId(w.id)} />
            ))}
          </div>

          {data?.meta.has_more && (
            <div className="flex justify-center pt-2">
              <button
                onClick={loadMore}
                disabled={isFetching}
                className="flex items-center gap-2 text-sm text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
              >
                {isFetching ? <><Spinner size={14} /> Loading…</> : 'Load more'}
              </button>
            </div>
          )}
        </>
      )}

      {selectedId && (
        <WorkoutDetail id={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  )
}
