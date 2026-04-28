import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi } from '../api/agent'
import { useToast } from '../hooks/useToast'
import { Spinner } from '../components/Spinner'
import { Badge } from '../components/Badge'
import { formatDate } from '../lib/utils'
import { Sparkles, ChevronDown, ChevronRight, CheckCircle2, Circle, Zap, RefreshCw } from 'lucide-react'
import type { TrainingPlanDetail } from '../types'

const SESSION_COLORS: Record<string, string> = {
  easy_run: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  tempo_run: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  interval_run: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  long_run: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  strength: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
  mobility: 'bg-teal-500/20 text-teal-300 border-teal-500/30',
  rest: 'bg-slate-600/40 text-slate-400 border-slate-600/40',
  cross_training: 'bg-green-500/20 text-green-300 border-green-500/30',
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function PlanView({ plan, onToggleItem }: { plan: TrainingPlanDetail; onToggleItem?: (id: string) => void }) {
  const today = new Date().toISOString().slice(0, 10)
  // Auto-open the current week, or week 1 if no active plan
  const currentWeek = plan.items.find(i => i.actual_date && i.actual_date >= today)?.week_number ?? 1
  const [openWeeks, setOpenWeeks] = useState<Set<number>>(new Set([currentWeek]))

  const weeks = Array.from(new Set(plan.items.map(i => i.week_number))).sort()

  return (
    <div className="space-y-3">
      {plan.ai_explanation && (
        <div className="bg-indigo-600/10 border border-indigo-500/20 rounded-xl px-4 py-3">
          <p className="text-sm text-indigo-200 leading-relaxed">{plan.ai_explanation}</p>
        </div>
      )}

      {weeks.map(wk => {
        const sessions = plan.items
          .filter(i => i.week_number === wk)
          .sort((a, b) => a.day_of_week - b.day_of_week)
        const isOpen = openWeeks.has(wk)

        return (
          <div key={wk} className="bg-slate-800/60 border border-slate-700 rounded-xl overflow-hidden">
            <button
              onClick={() =>
                setOpenWeeks(prev => {
                  const next = new Set(prev)
                  isOpen ? next.delete(wk) : next.add(wk)
                  return next
                })
              }
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/40 transition-colors"
            >
              <div className="flex items-center gap-3">
                {isOpen
                  ? <ChevronDown size={15} className="text-slate-400" />
                  : <ChevronRight size={15} className="text-slate-400" />
                }
                <span className="text-sm font-medium text-white">Week {wk}</span>
                <span className="text-xs text-slate-400">{sessions.length} sessions</span>
              </div>
              <span className="text-xs text-slate-500">
                {sessions.filter(s => s.is_completed).length}/{sessions.length} done
              </span>
            </button>

            {isOpen && (
              <div className="px-4 pb-4 space-y-2">
                {sessions.map(item => {
                  const isToday = item.actual_date === today
                  const isPast = item.actual_date && item.actual_date < today
                  return (
                    <div key={item.id} className={`flex items-start gap-3 rounded-lg px-2 py-1.5 ${
                      isToday ? 'bg-indigo-600/10 border border-indigo-500/20' : ''
                    }`}>
                      <button
                        type="button"
                        onClick={() => onToggleItem?.(item.id)}
                        disabled={!onToggleItem}
                        className="mt-0.5 flex-shrink-0 disabled:cursor-default"
                        title={item.is_completed ? 'Mark incomplete' : 'Mark complete'}
                      >
                        {item.is_completed
                          ? <CheckCircle2 size={16} className="text-green-400" />
                          : <Circle size={16} className={isPast ? 'text-red-400/60' : 'text-slate-600'} />
                        }
                      </button>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-slate-500 w-7">{DAYS[item.day_of_week - 1]}</span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded border font-medium ${
                              SESSION_COLORS[item.session_type] ?? 'bg-slate-700 text-slate-300 border-slate-600'
                            } ${item.is_completed ? 'opacity-50' : ''}`}
                          >
                            {item.session_type.replace(/_/g, ' ')}
                          </span>
                          <span className={`text-sm ${item.is_completed ? 'text-slate-500 line-through' : 'text-slate-200'}`}>
                            {item.title}
                          </span>
                          {isToday && !item.is_completed && (
                            <span className="text-xs font-medium text-indigo-400 bg-indigo-600/20 px-1.5 py-0.5 rounded">Today</span>
                          )}
                        </div>
                        {item.description && (
                          <p className="text-xs text-slate-400 mt-1 ml-9">{item.description}</p>
                        )}
                        <div className="flex gap-3 mt-1 ml-9">
                          {item.duration_min && (
                            <span className="text-xs text-slate-500">{item.duration_min} min</span>
                          )}
                          {item.target_distance_km && (
                            <span className="text-xs text-slate-500">{item.target_distance_km} km</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

const GOALS = [
  { value: '2.4km',          label: '2.4 km',        sub: 'Fitness test' },
  { value: '5K',             label: '5K',             sub: 'Parkrun / starter' },
  { value: '10K',            label: '10K',            sub: 'Classic road race' },
  { value: 'half-marathon',  label: 'Half Marathon',  sub: '21.1 km' },
  { value: 'marathon',       label: 'Marathon',       sub: '42.2 km' },
]

const WEEK_OPTIONS = [4, 6, 8, 10, 12, 16]
const DAY_OPTIONS  = [2, 3, 4, 5, 6]

export function Plans() {
  const qc = useQueryClient()
  const { toast } = useToast()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [goal, setGoal] = useState('')
  const [weeks, setWeeks] = useState(8)
  const [trainingDays, setTrainingDays] = useState(4)
  const [genError, setGenError] = useState('')

  const { data: plans, isLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: () => agentApi.listPlans().then(r => r.data),
  })

  const { data: planDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['plan', selectedId],
    queryFn: () => agentApi.getPlan(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  })

  const generateMutation = useMutation({
    mutationFn: () =>
      agentApi.generatePlan({
        goal,
        weeks,
        training_days_per_week: trainingDays,
      }),
    onSuccess: res => {
      qc.invalidateQueries({ queryKey: ['plans'] })
      setGenerating(false)
      setSelectedId(res.data.id)
      setGoal('')
      toast('success', 'Training plan generated!')
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map((e: any) => e.msg).join('. ')
        : typeof detail === 'string'
          ? detail
          : 'Plan generation failed'
      setGenError(msg)
      toast('error', 'Failed to generate plan')
    },
  })

  const activateMutation = useMutation({
    mutationFn: (id: string) => agentApi.activatePlan(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plans'] })
      qc.invalidateQueries({ queryKey: ['plan', selectedId] })
      qc.invalidateQueries({ queryKey: ['active-plan'] })
      toast('success', 'Plan activated — scheduled from this Monday')
    },
    onError: () => toast('error', 'Failed to activate plan'),
  })

  const toggleItemMutation = useMutation({
    mutationFn: (itemId: string) => agentApi.toggleItemComplete(itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan', selectedId] })
      qc.invalidateQueries({ queryKey: ['active-plan'] })
    },
  })

  const selectedPlan = plans?.find(p => p.id === selectedId)
  const isActive = selectedPlan?.status === 'active'

  // Adherence stats for the selected plan
  const adherence = (() => {
    if (!planDetail) return null
    const items = planDetail.items ?? []
    const today = new Date().toISOString().slice(0, 10)
    const due = items.filter(i => i.actual_date && i.actual_date <= today && i.session_type !== 'rest')
    const done = due.filter(i => i.is_completed)
    const total = items.filter(i => i.session_type !== 'rest').length
    const currentWeek = planDetail.start_date
      ? Math.min(
          Math.floor((new Date().getTime() - new Date(planDetail.start_date).getTime()) / (7 * 86400000)) + 1,
          planDetail.duration_weeks
        )
      : null
    return { due: due.length, done: done.length, total, currentWeek }
  })()

  const chipCls = (active: boolean) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors cursor-pointer ${
      active
        ? 'bg-indigo-600 border-indigo-500 text-white'
        : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500'
    }`

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Training Plans</h1>
          <p className="text-sm text-slate-400 mt-0.5">AI-generated personalised plans</p>
        </div>
        <button
          onClick={() => { setGenerating(g => !g); setGenError('') }}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Sparkles size={14} />
          Generate plan
        </button>
      </div>

      {/* Generate form */}
      {generating && (
        <div className="bg-slate-800/60 border border-indigo-500/30 rounded-xl p-5 space-y-5">
          <h2 className="text-sm font-semibold text-white">New training plan</h2>

          {/* Goal selector */}
          <div>
            <p className="text-xs text-slate-400 mb-2">Race goal *</p>
            <div className="grid grid-cols-5 gap-2">
              {GOALS.map(g => (
                <button
                  key={g.value}
                  type="button"
                  onClick={() => setGoal(g.value)}
                  className={`flex flex-col items-center justify-center rounded-xl border py-3 px-2 transition-colors cursor-pointer ${
                    goal === g.value
                      ? 'bg-indigo-600/20 border-indigo-500 text-white'
                      : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500'
                  }`}
                >
                  <span className="text-base font-bold">{g.label}</span>
                  <span className="text-xs text-slate-400 mt-0.5">{g.sub}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Duration selector */}
          <div>
            <p className="text-xs text-slate-400 mb-2">Duration</p>
            <div className="flex flex-wrap gap-2">
              {WEEK_OPTIONS.map(w => (
                <button
                  key={w}
                  type="button"
                  onClick={() => setWeeks(w)}
                  className={chipCls(weeks === w)}
                >
                  {w} wks
                </button>
              ))}
            </div>
          </div>

          {/* Training days selector */}
          <div>
            <p className="text-xs text-slate-400 mb-2">Training days per week</p>
            <div className="flex gap-2">
              {DAY_OPTIONS.map(d => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setTrainingDays(d)}
                  className={chipCls(trainingDays === d)}
                >
                  {d}
                </button>
              ))}
              <span className="text-xs text-slate-500 self-center ml-1">days / week</span>
            </div>
          </div>

          {genError && (
            <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
              {genError}
            </p>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={() => generateMutation.mutate()}
              disabled={!goal || generateMutation.isPending}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              {generateMutation.isPending
                ? <><Spinner size={14} /> Generating…</>
                : <><Sparkles size={14} /> Generate</>
              }
            </button>
            <button
              onClick={() => setGenerating(false)}
              className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            {generateMutation.isPending && (
              <p className="text-xs text-slate-500">AI is designing your plan — this can take 1–3 minutes for longer plans…</p>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-[280px_1fr] gap-5">
        {/* Plan list */}
        <div className="space-y-2">
          {isLoading && <div className="flex justify-center py-8"><Spinner /></div>}
          {!isLoading && !plans?.length && (
            <p className="text-slate-500 text-sm py-4">No plans yet — generate one!</p>
          )}
          {plans?.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              className={`w-full text-left bg-slate-800/60 border rounded-xl p-3 transition-colors ${
                selectedId === p.id
                  ? 'border-indigo-500/50 bg-indigo-600/10'
                  : 'border-slate-700 hover:border-slate-600'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-white font-medium leading-tight line-clamp-2">{p.goal}</p>
                <Badge variant={p.status === 'active' ? 'processed' : 'default'}>{p.status}</Badge>
              </div>
              <p className="text-xs text-slate-500 mt-1">{p.duration_weeks} weeks · {formatDate(p.created_at)}</p>
            </button>
          ))}
        </div>

        {/* Plan detail */}
        <div>
          {!selectedId && (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
              Select a plan to view details
            </div>
          )}

          {selectedId && !loadingDetail && planDetail && (
            <div className="space-y-4">
              {/* Plan header */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-slate-400">{planDetail.duration_weeks} weeks</span>
                  {isActive && adherence?.currentWeek && (
                    <span className="text-xs text-slate-400">
                      · Week {adherence.currentWeek} of {planDetail.duration_weeks}
                    </span>
                  )}
                  {isActive && (
                    <span className="flex items-center gap-1 text-xs font-medium text-green-400 bg-green-400/10 border border-green-400/20 rounded-full px-2.5 py-0.5">
                      <Zap size={10} /> Active
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {!isActive && (
                    <button
                      onClick={() => activateMutation.mutate(selectedId)}
                      disabled={activateMutation.isPending}
                      className="flex items-center gap-1.5 text-xs font-medium text-indigo-400 hover:text-white border border-indigo-500/40 hover:bg-indigo-600 hover:border-indigo-600 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {activateMutation.isPending ? <Spinner size={12} /> : <Zap size={12} />}
                      Activate plan
                    </button>
                  )}
                  {/* Regenerate button — shown when ≥30% through plan */}
                  {isActive && adherence && adherence.due / Math.max(adherence.total, 1) >= 0.3 && (
                    <button
                      onClick={() => { setGenerating(true); setGoal(planDetail.goal) }}
                      className="flex items-center gap-1.5 text-xs font-medium text-amber-400 hover:text-white border border-amber-500/30 hover:bg-amber-500/20 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      <RefreshCw size={12} /> Regenerate plan
                    </button>
                  )}
                </div>
              </div>

              {/* Adherence bar */}
              {isActive && adherence && adherence.due > 0 && (
                <div className="bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-400">Sessions completed</span>
                    <span className="text-xs font-medium text-white">
                      {adherence.done}/{adherence.due} due · {adherence.total} total
                    </span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 rounded-full transition-all"
                      style={{ width: `${Math.min(100, (adherence.done / Math.max(adherence.due, 1)) * 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1.5">
                    {adherence.done >= adherence.due
                      ? '🎉 On track!'
                      : `${adherence.due - adherence.done} session${adherence.due - adherence.done > 1 ? 's' : ''} behind — keep going`}
                  </p>
                </div>
              )}

              <PlanView plan={planDetail} onToggleItem={id => toggleItemMutation.mutate(id)} />
            </div>
          )}

          {loadingDetail && (
            <div className="flex justify-center py-12"><Spinner size={28} /></div>
          )}
        </div>
      </div>
    </div>
  )
}
