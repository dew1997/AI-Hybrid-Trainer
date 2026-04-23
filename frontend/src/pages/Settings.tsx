import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'

const GOALS = ['marathon', 'strength', 'fat_loss', 'general']
const LEVELS = ['beginner', 'intermediate', 'advanced']

export function Settings() {
  const { user } = useAuth()
  const { toast } = useToast()

  const [displayName, setDisplayName] = useState(user?.display_name ?? '')
  const [weightKg, setWeightKg] = useState(user?.weight_kg?.toString() ?? '')
  const [maxHr, setMaxHr] = useState(user?.max_hr?.toString() ?? '')
  const [vo2max, setVo2max] = useState(user?.vo2max_estimate?.toString() ?? '')
  const [goal, setGoal] = useState(user?.primary_goal ?? 'general')
  const [experience, setExperience] = useState(user?.experience_level ?? 'intermediate')

  const mutation = useMutation({
    mutationFn: () =>
      authApi.updateProfile({
        display_name: displayName || undefined,
        weight_kg: weightKg ? +weightKg : undefined,
        max_hr: maxHr ? +maxHr : undefined,
        vo2max_estimate: vo2max ? +vo2max : undefined,
        primary_goal: goal || undefined,
        experience_level: experience || undefined,
      }),
    onSuccess: () => toast('success', 'Profile updated'),
    onError: () => toast('error', 'Failed to save profile'),
  })

  const inputCls =
    'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors'
  const labelCls = 'block text-xs text-slate-400 mb-1'

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-slate-400 mt-0.5">Manage your profile and training preferences</p>
      </div>

      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }} className="space-y-5">
        {/* Personal */}
        <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-4">
          <h2 className="text-sm font-medium text-slate-300">Personal</h2>
          <div>
            <label className={labelCls}>Display name</label>
            <input
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              className={inputCls}
              placeholder="Your name"
            />
          </div>
          <div>
            <label className={labelCls}>Email</label>
            <input
              value={user?.email ?? ''}
              disabled
              className={inputCls + ' opacity-50 cursor-not-allowed'}
            />
          </div>
          <div>
            <label className={labelCls}>Weight (kg)</label>
            <input
              type="number"
              step="0.1"
              value={weightKg}
              onChange={e => setWeightKg(e.target.value)}
              className={inputCls}
              placeholder="75"
            />
          </div>
        </section>

        {/* Training profile */}
        <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-4">
          <h2 className="text-sm font-medium text-slate-300">Training profile</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Primary goal</label>
              <select
                value={goal}
                onChange={e => setGoal(e.target.value)}
                className={inputCls}
              >
                {GOALS.map(g => (
                  <option key={g} value={g}>
                    {g.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Experience level</label>
              <select
                value={experience}
                onChange={e => setExperience(e.target.value)}
                className={inputCls}
              >
                {LEVELS.map(l => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        {/* Physiology */}
        <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-4">
          <h2 className="text-sm font-medium text-slate-300">Physiology</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Max heart rate (bpm)</label>
              <input
                type="number"
                value={maxHr}
                onChange={e => setMaxHr(e.target.value)}
                className={inputCls}
                placeholder="185"
              />
            </div>
            <div>
              <label className={labelCls}>VO₂ max estimate</label>
              <input
                type="number"
                step="0.1"
                value={vo2max}
                onChange={e => setVo2max(e.target.value)}
                className={inputCls}
                placeholder="52"
              />
            </div>
          </div>
        </section>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
        >
          {mutation.isPending ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </div>
  )
}
