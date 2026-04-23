import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { useAuth } from '../hooks/useAuth'
import { Activity } from 'lucide-react'

export function Register() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    email: '', password: '', display_name: '',
    primary_goal: 'general', experience_level: 'beginner',
    weight_kg: '', max_hr: '', resting_hr: '',
  })

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.register({
        email: form.email,
        password: form.password,
        display_name: form.display_name || undefined,
        primary_goal: form.primary_goal,
        experience_level: form.experience_level,
        weight_kg: form.weight_kg ? +form.weight_kg : undefined,
        max_hr: form.max_hr ? +form.max_hr : undefined,
        resting_hr: form.resting_hr ? +form.resting_hr : undefined,
      })
      await login(form.email, form.password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const inputCls = 'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors'
  const labelCls = 'block text-sm text-slate-400 mb-1.5'

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
            <Activity size={20} className="text-white" />
          </div>
          <span className="text-xl font-bold text-white">AI Hybrid Trainer</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h1 className="text-lg font-semibold text-white mb-5">Create account</h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Email *</label>
                <input type="email" value={form.email} onChange={set('email')} required className={inputCls} placeholder="you@example.com" />
              </div>
              <div>
                <label className={labelCls}>Password *</label>
                <input type="password" value={form.password} onChange={set('password')} required minLength={8} className={inputCls} placeholder="8+ chars" />
              </div>
            </div>
            <div>
              <label className={labelCls}>Display name</label>
              <input value={form.display_name} onChange={set('display_name')} className={inputCls} placeholder="Your name" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Primary goal</label>
                <select value={form.primary_goal} onChange={set('primary_goal')} className={inputCls}>
                  <option value="general">General fitness</option>
                  <option value="marathon">Marathon</option>
                  <option value="strength">Strength</option>
                  <option value="fat_loss">Fat loss</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Experience</label>
                <select value={form.experience_level} onChange={set('experience_level')} className={inputCls}>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelCls}>Weight (kg)</label>
                <input type="number" value={form.weight_kg} onChange={set('weight_kg')} className={inputCls} placeholder="70" />
              </div>
              <div>
                <label className={labelCls}>Max HR</label>
                <input type="number" value={form.max_hr} onChange={set('max_hr')} className={inputCls} placeholder="185" />
              </div>
              <div>
                <label className={labelCls}>Resting HR</label>
                <input type="number" value={form.resting_hr} onChange={set('resting_hr')} className={inputCls} placeholder="55" />
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition-colors text-sm"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-4">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
