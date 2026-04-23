import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { workoutsApi } from '../api/workouts'
import { Badge } from './Badge'
import { Spinner } from './Spinner'
import { formatPace, formatDistance, formatDuration, formatDate, paceZoneColor } from '../lib/utils'
import { X, Heart, Zap } from 'lucide-react'

interface Props {
  id: string
  onClose: () => void
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-sm font-medium text-white">{value}</p>
    </div>
  )
}

export function WorkoutDetail({ id, onClose }: Props) {
  const { data: workout, isLoading } = useQuery({
    queryKey: ['workout', id],
    queryFn: () => workoutsApi.get(id).then(r => r.data),
  })

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 sticky top-0 bg-slate-900 z-10">
          <div className="flex items-center gap-2 flex-wrap">
            {workout && (
              <Badge variant={workout.workout_type as any}>{workout.workout_type.toUpperCase()}</Badge>
            )}
            {workout?.route_name && (
              <span className="text-sm text-slate-300 font-medium">{workout.route_name}</span>
            )}
            {workout && (
              <span className="text-sm text-slate-400">{formatDate(workout.started_at)}</span>
            )}
            {workout && (
              <Badge variant={workout.status as any}>{workout.status}</Badge>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-500 hover:text-white rounded-md hover:bg-slate-800 transition-colors flex-shrink-0"
          >
            <X size={16} />
          </button>
        </div>

        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size={28} />
          </div>
        )}

        {workout && !isLoading && (
          <div className="p-5 space-y-5">
            {/* Metrics grid */}
            <div className="grid grid-cols-3 gap-3">
              <MetricCell label="Duration" value={formatDuration(workout.duration_seconds)} />

              {workout.workout_type === 'run' ? (
                <>
                  <MetricCell label="Distance" value={formatDistance(workout.distance_meters)} />
                  <MetricCell label="Avg pace" value={formatPace(workout.avg_pace_sec_per_km)} />
                  {workout.avg_hr != null && (
                    <MetricCell label="Avg HR" value={`${workout.avg_hr} bpm`} />
                  )}
                  {workout.elevation_gain_m != null && (
                    <MetricCell label="Elevation" value={`+${workout.elevation_gain_m} m`} />
                  )}
                  {workout.pace_zone && (
                    <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3">
                      <p className="text-xs text-slate-500 mb-1">Pace zone</p>
                      <p className={`text-sm font-medium ${paceZoneColor(workout.pace_zone)}`}>
                        {workout.pace_zone.replace(/_/g, ' ')}
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <MetricCell
                    label="Volume"
                    value={workout.total_volume_kg ? `${workout.total_volume_kg.toLocaleString()} kg` : '—'}
                  />
                  {workout.workout_template && (
                    <MetricCell label="Template" value={workout.workout_template} />
                  )}
                  {workout.muscle_groups?.length ? (
                    <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 col-span-2">
                      <p className="text-xs text-slate-500 mb-1">Muscle groups</p>
                      <p className="text-sm font-medium text-white">{workout.muscle_groups.join(', ')}</p>
                    </div>
                  ) : null}
                </>
              )}

              {workout.tss != null && (
                <MetricCell label="TSS" value={Number(workout.tss).toFixed(0)} />
              )}
              {workout.perceived_effort != null && (
                <MetricCell label="RPE" value={`${workout.perceived_effort}/10`} />
              )}
              {workout.intensity_factor != null && (
                <MetricCell label="IF" value={workout.intensity_factor.toFixed(2)} />
              )}
            </div>

            {/* Run splits */}
            {workout.workout_type === 'run' && workout.splits.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-white mb-3">Splits</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-slate-500 border-b border-slate-800">
                        <th className="text-left pb-2 font-medium">Split</th>
                        <th className="text-right pb-2 font-medium">Pace</th>
                        <th className="text-right pb-2 font-medium">
                          <span className="flex items-center justify-end gap-1">
                            <Heart size={10} /> HR
                          </span>
                        </th>
                        <th className="text-right pb-2 font-medium">Duration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {workout.splits.map(split => (
                        <tr key={split.id} className="text-slate-300">
                          <td className="py-2 text-slate-400">km {split.split_number}</td>
                          <td className="py-2 text-right font-medium">
                            {formatPace(split.avg_pace_sec_per_km)}
                          </td>
                          <td className="py-2 text-right">
                            {split.avg_hr != null ? split.avg_hr : '—'}
                          </td>
                          <td className="py-2 text-right text-slate-400">
                            {formatDuration(split.duration_seconds)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Gym sets */}
            {workout.workout_type === 'gym' && workout.sets.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-white mb-3">Sets</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-slate-500 border-b border-slate-800">
                        <th className="text-left pb-2 font-medium">#</th>
                        <th className="text-left pb-2 font-medium">Exercise</th>
                        <th className="text-right pb-2 font-medium">Reps</th>
                        <th className="text-right pb-2 font-medium">kg</th>
                        <th className="text-right pb-2 font-medium">Warmup</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {workout.sets.map(set => (
                        <tr key={set.id} className="text-slate-300">
                          <td className="py-2 text-slate-500 text-xs">{set.set_number}</td>
                          <td className="py-2 font-medium">{set.exercise_name}</td>
                          <td className="py-2 text-right">{set.reps ?? '—'}</td>
                          <td className="py-2 text-right">{set.weight_kg ?? '—'}</td>
                          <td className="py-2 text-right">
                            {set.is_warmup ? (
                              <Zap size={13} className="text-yellow-400 ml-auto" />
                            ) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Notes */}
            {workout.notes && (
              <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl px-4 py-3">
                <p className="text-xs text-slate-500 mb-1">Notes</p>
                <p className="text-sm text-slate-300 leading-relaxed">{workout.notes}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
