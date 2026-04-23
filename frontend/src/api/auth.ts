import { api } from './client'
import type { User } from '../types'

export const authApi = {
  register: (data: {
    email: string
    password: string
    display_name?: string
    primary_goal?: string
    experience_level?: string
    weight_kg?: number
    max_hr?: number
    resting_hr?: number
  }) => api.post('/auth/register', data),

  login: (email: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string }>('/auth/login', { email, password }),

  me: () => api.get<User>('/auth/me'),

  updateProfile: (data: Partial<User>) => api.patch<User>('/auth/me', data),
}
