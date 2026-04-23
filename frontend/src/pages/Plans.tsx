import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi } from '../api/agent'
import { useToast } from '../hooks/useToast'
import { Spinner } from '../components/Spinner'
import { Badge } from '../components/Badge'
import { formatDate } from '../lib/utils'
import { Sparkles, ChevronDown, ChevronRight, CheckCircle2, Circle, Zap } from 'lucide-react'
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

function PlanView({ plan }: { plan: TrainingPlanDetail }) {
  const [openWeeks, setOpenWeeks] = useState<Set<number>>(new Set([1]))

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
                {sessions.map(item => (
                  <div key={item.id} className="flex items-start gap-3">
                    {item.is_completed
                      ? <CheckCircle2 size={16} className="text-green-400 mt-0.5 flex-shrink-0" />
                      : <Circle size={16} className="text-slate-600 mt-0.5 flex-shrink-0" />
                    }
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-slate-500 w-7">{DAYS[item.day_of_week - 1]}</span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded border font-medium ${
                            SESSION_COLORS[item.session_type] ?? 'bg-slate-700 text-slate-300 border-slate-600'
                          }`}
                        >
                          {item.session_type.replace(/_/g, ' ')}
                        </span>
                        <span className="text-sm text-slate-200">{item.title}</span>
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
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function Plans() {
  const qc = useQueryClient()
  const { toast } = useToast()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [goal, setGoal] = useState('')
  const [weeks, setWeeks] = useState('4')
  const [hours, setHours] = useState('')
  const [constraints, setConstraints] = useState('')
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
        weeks: +weeks,
        weekly_hours: hours ? +hours : undefined,
        constraints: constraints ? constraints.split(',').map(s => s.trim()) : [],
      }),
    onSuccess: res => {
      qc.invalidateQueries({ queryKey: ['plans'] })
      setGenerating(false)
      setSelectedId(res.data.id)
      setGoal(''); setWeeks('4'); setHours(''); setConstraints('')
      toast('success', 'Training plan generated!')
    },
    onError: (err: any) => {
      setGenError(err.response?.data?.detail || 'Plan generation failed')
      toast('error', 'Failed to generate plan')
    },
  })

  const activateMutation = useMutation({
    mutationFn: (id: string) => agentApi.activatePlan(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plans'] })
      qc.invalidateQueries({ queryKey: ['plan', selectedId] })
      toast('success', 'Plan activated')
    },
    onError: () => toast('error', 'Failed to activate plan'),
  })

  const selectedPlan = plans?.find(p => p.id === selectedId)
  const isActive = selectedPlan?.status === 'active'

  const inputCls =
    'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors'

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Training Plans</h1>
          <p className="text-sm text-slate-400 mt-0.5">AI-generated personalised plans</p>
        </div>
        <button
          onClick={() => setGenerating(g => !g)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Sparkles size={14} />
          Generate plan
        </button>
      </div>

      {/* Generate form */}
      {generating && (
        <div className="bg-slate-800/60 border border-indigo-500/30 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">New training plan</h2>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Goal *</label>
            <input
              value={goal}
              onChange={e => setGoal(e.target.value)}
              className={inputCls}
              placeholder="Complete a half marathon in under 2 hours in 8 weeks"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Duration (weeks)</label>
              <input
                type="number" min={2} max={16}
                value={weeks}
                onChange={e => setWeeks(e.target.value)}
                className={inputCls}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Weekly hours</label>
              <input
                type="number"
                value={hours}
                onChange={e => setHours(e.target.value)}
                className={inputCls}
                placeholder="6"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Constraints</label>
              <input
                value={constraints}
                onChange={e => setConstraints(e.target.value)}
                className={inputCls}
                placeholder="no Mondays"
              />
            </div>
          </div>
          {genError && (
            <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
              {genError}
            </p>
          )}
          <div className="flex gap-2">
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
          </div>
          {generateMutation.isPending && (
            <p className="text-xs text-slate-500">
              Claude is designing your personalised plan… this takes ~30 seconds.
            </p>
          )}
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
              {/* Plan header with activate button */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-400">{planDetail.duration_weeks} weeks</span>
                  {isActive && (
                    <span className="flex items-center gap-1 text-xs font-medium text-green-400 bg-green-400/10 border border-green-400/20 rounded-full px-2.5 py-0.5">
                      <Zap size={10} /> Active
                    </span>
                  )}
                </div>
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
              </div>
              <PlanView plan={planDetail} />
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
