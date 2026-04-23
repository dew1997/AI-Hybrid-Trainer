import { api } from './client'
import type { CoachingResponse, TrainingPlan, TrainingPlanDetail } from '../types'

export const agentApi = {
  coachingQuery: (query: string, context_weeks = 4) =>
    api.post<CoachingResponse>('/agent/coaching-query', { query, context_weeks }),

  generatePlan: (data: {
    goal: string
    weeks?: number
    weekly_hours?: number
    constraints?: string[]
  }) => api.post('/agent/generate-plan', data),

  listPlans: () => api.get<TrainingPlan[]>('/agent/plans'),

  getPlan: (id: string) => api.get<TrainingPlanDetail>(`/agent/plans/${id}`),

  activatePlan: (id: string) => api.patch(`/agent/plans/${id}/activate`),
}
