import { api } from './client'
import type { CoachingResponse, CoachingSession, CoachingSessionDetail, TrainingPlan, TrainingPlanDetail } from '../types'

export const agentApi = {
  coachingQuery: (query: string, context_weeks = 4, session_id?: string) =>
    api.post<CoachingResponse>('/agent/coaching-query', { query, context_weeks, session_id }),

  generatePlan: (data: {
    goal: string
    weeks: number
    training_days_per_week: number
  }) => api.post('/agent/generate-plan', data),

  listPlans: () => api.get<TrainingPlan[]>('/agent/plans'),

  getPlan: (id: string) => api.get<TrainingPlanDetail>(`/agent/plans/${id}`),

  activatePlan: (id: string) => api.patch(`/agent/plans/${id}/activate`),

  listSessions: () => api.get<CoachingSession[]>('/agent/sessions'),

  getSession: (id: string) => api.get<CoachingSessionDetail>(`/agent/sessions/${id}`),

  deleteSession: (id: string) => api.delete(`/agent/sessions/${id}`),
}
