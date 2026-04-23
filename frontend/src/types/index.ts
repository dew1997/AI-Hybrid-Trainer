export interface User {
  id: string
  email: string
  display_name: string | null
  primary_goal: string | null
  experience_level: string | null
  weight_kg: number | null
  max_hr: number | null
  vo2max_estimate: number | null
}

export interface Workout {
  id: string
  workout_type: 'run' | 'gym' | 'cycle' | 'other'
  status: 'pending' | 'processed' | 'failed' | 'quarantined'
  started_at: string
  duration_seconds: number | null
  perceived_effort: number | null
  notes: string | null
  distance_meters: number | null
  avg_pace_sec_per_km: number | null
  avg_hr: number | null
  max_hr: number | null
  elevation_gain_m: number | null
  route_name: string | null
  pace_zone: string | null
  tss: number | null
  fatigue_score: number | null
  fitness_score: number | null
  intensity_factor: number | null
  total_volume_kg: number | null
  muscle_groups: string[] | null
  workout_template: string | null
  splits: RunSplit[]
  sets: WorkoutSet[]
}

export interface RunSplit {
  id: string
  split_number: number
  duration_seconds: number
  avg_pace_sec_per_km: number | null
  avg_hr: number | null
}

export interface WorkoutSet {
  id: string
  set_number: number
  exercise_name: string
  reps: number | null
  weight_kg: number | null
  is_warmup: boolean
}

export interface AnalyticsSnapshot {
  week_start_date: string
  total_workouts: number
  run_workouts: number
  gym_workouts: number
  total_run_km: number
  total_gym_volume_kg: number
  total_duration_min: number
  weekly_tss: number | null
  acute_load: number | null
  chronic_load: number | null
  training_stress_balance: number | null
  avg_pace_sec_per_km: number | null
  avg_hr_run: number | null
  avg_rpe: number | null
}

export interface FitnessFreshnessPoint {
  week_start: string
  acute_load: number | null
  chronic_load: number | null
  tsb: number | null
  weekly_tss: number | null
}

export interface TrainingPlan {
  id: string
  goal: string
  status: string
  duration_weeks: number
  ai_explanation: string | null
  created_at: string
}

export interface TrainingPlanDetail extends TrainingPlan {
  items: PlanItem[]
}

export interface PlanItem {
  id: string
  week_number: number
  day_of_week: number
  session_type: string
  title: string
  description: string | null
  duration_min: number | null
  target_distance_km: number | null
  is_completed: boolean
}

export interface CoachingResponse {
  answer: string
  sources: { title: string; relevance: number }[]
  suggested_actions: string[]
  token_usage: { input: number; output: number }
}
