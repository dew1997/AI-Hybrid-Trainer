import { api } from './client'
import type { Workout } from '../types'

export const workoutsApi = {
  list: (params?: { workout_type?: string; limit?: number; cursor?: string }) =>
    api.get<{ data: Workout[]; meta: { total: number; has_more: boolean; next_cursor?: string } }>('/workouts', { params }),

  get: (id: string) => api.get<Workout>(`/workouts/${id}`),

  createRun: (data: {
    started_at: string
    duration_seconds: number
    distance_meters: number
    avg_pace_sec_per_km?: number
    avg_hr?: number
    elevation_gain_m?: number
    perceived_effort?: number
    route_name?: string
  }) => api.post<{ workout: Workout; pipeline_status: string }>('/workouts', {
    workout_type: 'run',
    ...data,
  }),

  createGym: (data: {
    started_at: string
    duration_seconds: number
    workout_template?: string
    muscle_groups?: string[]
    perceived_effort?: number
    sets: { set_number: number; exercise_name: string; reps?: number; weight_kg?: number; is_warmup?: boolean }[]
  }) => api.post<{ workout: Workout; pipeline_status: string }>('/workouts', {
    workout_type: 'gym',
    ...data,
  }),
}
