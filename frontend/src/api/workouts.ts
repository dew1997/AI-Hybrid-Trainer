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
    notes?: string
  }) => api.post<{ workout: Workout; pipeline_status: string }>('/workouts', {
    workout_type: 'run',
    ...data,
  }),

  delete: (id: string) => api.delete(`/workouts/${id}`),

  exerciseHistory: () =>
    api.get<{ exercise_name: string; date: string; sets: { reps: number | null; weight_kg: number | null }[] }[]>('/workouts/exercises/history'),

  exercisePRs: () =>
    api.get<{ exercise_name: string; weight_kg: number; reps: number; estimated_1rm: number; date: string }[]>('/workouts/exercises/prs'),

  createGym: (data: {
    started_at: string
    duration_seconds: number
    workout_template?: string
    muscle_groups?: string[]
    perceived_effort?: number
    notes?: string
    sets: { set_number: number; exercise_name: string; reps?: number; weight_kg?: number; is_warmup?: boolean }[]
  }) => api.post<{ workout: Workout; pipeline_status: string }>('/workouts', {
    workout_type: 'gym',
    ...data,
  }),
}
