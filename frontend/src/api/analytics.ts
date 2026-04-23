import { api } from './client'
import type { AnalyticsSnapshot, FitnessFreshnessPoint } from '../types'

export const analyticsApi = {
  summary: () =>
    api.get<{
      current_week: AnalyticsSnapshot | null
      trailing_4_weeks: AnalyticsSnapshot[]
      fitness_trend: string | null
    }>('/analytics/summary'),

  fitnessFreshness: (weeks = 12) =>
    api.get<{ data: FitnessFreshnessPoint[]; current: FitnessFreshnessPoint | null }>(
      '/analytics/fitness-freshness',
      { params: { weeks } }
    ),

  weekly: (limit = 8) =>
    api.get<AnalyticsSnapshot[]>('/analytics/weekly', { params: { limit } }),
}
