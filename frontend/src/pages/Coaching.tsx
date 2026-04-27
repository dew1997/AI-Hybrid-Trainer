import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { agentApi } from '../api/agent'
import { useToast } from '../hooks/useToast'
import { Spinner } from '../components/Spinner'
import { Send, Bot, User, Lightbulb, Plus, Trash2 } from 'lucide-react'
import type { ChatMessage } from '../types'

interface LocalMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: { title: string; relevance: number }[]
  actions?: string[]
}

const SUGGESTIONS = [
  'Why are my easy runs feeling hard lately?',
  'How should I structure my training this week?',
  'My legs are sore — should I train today?',
  'How do I improve my running pace without injury?',
]

function dateGroup(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays <= 7) return 'This week'
  return 'Earlier'
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown components={{
      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
      strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
      em: ({ children }) => <em className="italic text-slate-300">{children}</em>,
      ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>,
      ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>,
      li: ({ children }) => <li className="text-slate-200">{children}</li>,
      h3: ({ children }) => <h3 className="font-semibold text-white mt-3 mb-1">{children}</h3>,
      h4: ({ children }) => <h4 className="font-medium text-slate-100 mt-2 mb-0.5">{children}</h4>,
      code: ({ children }) => <code className="bg-slate-700 rounded px-1 py-0.5 text-xs font-mono text-slate-200">{children}</code>,
    }}>
      {content}
    </ReactMarkdown>
  )
}

function MessageBubble({ m }: { m: LocalMessage | ChatMessage }) {
  const actions = 'actions' in m ? m.actions : ('suggested_actions' in (m as any) ? (m as any).suggested_actions : [])
  return (
    <div className={`flex items-start gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
      {m.role === 'assistant' && (
        <div className="w-8 h-8 rounded-lg bg-indigo-600/30 flex items-center justify-center flex-shrink-0">
          <Bot size={16} className="text-indigo-400" />
        </div>
      )}

      <div className={`max-w-[80%] space-y-2 ${m.role === 'user' ? 'items-end' : ''}`}>
        <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
          m.role === 'user'
            ? 'bg-indigo-600 text-white'
            : 'bg-slate-800 border border-slate-700 text-slate-200'
        }`}>
          {m.role === 'user' ? m.content : <MarkdownContent content={m.content} />}
        </div>

        {actions && actions.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs text-slate-500 flex items-center gap-1">
              <Lightbulb size={11} /> Action items
            </p>
            {actions.map((a: string, j: number) => (
              <div key={j} className="flex items-start gap-2 bg-indigo-600/10 border border-indigo-500/20 rounded-lg px-3 py-2">
                <span className="w-4 h-4 rounded-full bg-indigo-600/40 text-indigo-300 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                  {j + 1}
                </span>
                <p className="text-xs text-indigo-200">{a.replace(/^Action\s*(?:item\s*)?:\s*/i, '')}</p>
              </div>
            ))}
          </div>
        )}

        {m.sources && m.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {m.sources.map((s, j) => (
              <span key={j} className="text-xs bg-slate-700/60 text-slate-400 rounded px-2 py-0.5">
                {s.title} · {s.relevance.toFixed(0)}%
              </span>
            ))}
          </div>
        )}
      </div>

      {m.role === 'user' && (
        <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0">
          <User size={15} className="text-slate-400" />
        </div>
      )}
    </div>
  )
}

export function Coaching() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [input, setInput] = useState('')
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const { data: sessions, isLoading: loadingSessions } = useQuery({
    queryKey: ['coaching-sessions'],
    queryFn: () => agentApi.listSessions().then(r => r.data),
  })

  const mutation = useMutation({
    mutationFn: ({ query, sessionId }: { query: string; sessionId: string | null }) =>
      agentApi.coachingQuery(query, 4, sessionId ?? undefined).then(r => r.data),
    onSuccess: (data) => {
      setCurrentSessionId(data.session_id)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
          actions: data.suggested_actions,
        },
      ])
      qc.invalidateQueries({ queryKey: ['coaching-sessions'] })
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : 'Coach query failed — please try again'
      toast('error', msg)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${msg}` },
      ])
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => agentApi.deleteSession(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['coaching-sessions'] })
      if (currentSessionId === id) startNewChat()
      toast('success', 'Conversation deleted')
    },
    onError: () => toast('error', 'Failed to delete conversation'),
  })

  const send = (query: string) => {
    if (!query.trim() || mutation.isPending) return
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setInput('')
    mutation.mutate({ query, sessionId: currentSessionId })
  }

  const startNewChat = () => {
    setCurrentSessionId(null)
    setMessages([])
  }

  const loadSession = async (sessionId: string) => {
    if (sessionId === currentSessionId) return
    try {
      const { data } = await agentApi.getSession(sessionId)
      setCurrentSessionId(sessionId)
      setMessages(data.messages.map(m => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
        sources: m.sources,
        actions: m.actions,
      })))
    } catch {
      toast('error', 'Failed to load conversation')
    }
  }

  // Group sessions by date label
  const grouped: Record<string, typeof sessions> = {}
  for (const s of sessions ?? []) {
    const g = dateGroup(s.updated_at)
    if (!grouped[g]) grouped[g] = []
    grouped[g]!.push(s)
  }
  const GROUP_ORDER = ['Today', 'Yesterday', 'This week', 'Earlier']

  return (
    <div className="flex h-[calc(100vh-80px)] gap-0">

      {/* ── Sidebar ── */}
      <div className="w-56 flex-shrink-0 flex flex-col border-r border-slate-800 pr-3 mr-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">Conversations</span>
          <button
            onClick={startNewChat}
            title="New conversation"
            className="w-6 h-6 flex items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          >
            <Plus size={14} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 min-h-0">
          {loadingSessions && <div className="flex justify-center py-4"><Spinner size={16} /></div>}

          {!loadingSessions && !sessions?.length && (
            <p className="text-xs text-slate-600 text-center py-4">No past conversations</p>
          )}

          {GROUP_ORDER.filter(g => grouped[g]?.length).map(group => (
            <div key={group}>
              <p className="text-xs text-slate-600 mb-1.5">{group}</p>
              <div className="space-y-1">
                {grouped[group]!.map(s => (
                  <div
                    key={s.id}
                    className={`group relative rounded-lg px-2.5 py-2 cursor-pointer transition-colors ${
                      currentSessionId === s.id
                        ? 'bg-indigo-600/20 border border-indigo-500/30'
                        : 'hover:bg-slate-800/60 border border-transparent'
                    }`}
                    onClick={() => loadSession(s.id)}
                  >
                    <p className="text-xs text-slate-300 leading-tight line-clamp-2 pr-5">{s.title}</p>
                    <p className="text-xs text-slate-600 mt-0.5">{s.message_count / 2 | 0} Q&A</p>
                    <button
                      onClick={e => { e.stopPropagation(); deleteMutation.mutate(s.id) }}
                      className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 w-5 h-5 flex items-center justify-center rounded text-slate-500 hover:text-red-400 transition-all"
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main chat ── */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="mb-4">
          <h1 className="text-xl font-bold text-white">AI Coaching</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Ask anything about your training — powered by AI
          </p>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 pb-4 min-h-0">
          {messages.length === 0 && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/30 flex items-center justify-center flex-shrink-0">
                  <Bot size={16} className="text-indigo-400" />
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">
                  Hi! I'm your AI fitness coach. I can analyse your training data, answer
                  questions about recovery, pacing, and periodisation, and help you train smarter.
                  What's on your mind?
                </p>
              </div>

              <p className="text-xs text-slate-500 uppercase tracking-wide">Suggested questions</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-left text-sm text-slate-300 bg-slate-800/40 border border-slate-700/60 rounded-xl px-4 py-3 hover:border-indigo-500/40 hover:text-white transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => <MessageBubble key={i} m={m} />)}

          {mutation.isPending && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/30 flex items-center justify-center">
                <Bot size={16} className="text-indigo-400" />
              </div>
              <div className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 flex items-center gap-2 text-slate-400 text-sm">
                <Spinner size={14} /> Thinking…
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="pt-3 border-t border-slate-800">
          <form
            onSubmit={e => { e.preventDefault(); send(input) }}
            className="flex items-center gap-2"
          >
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={mutation.isPending}
              placeholder="Ask your coach anything…"
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
            <button
              type="submit"
              disabled={!input.trim() || mutation.isPending}
              className="w-10 h-10 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-xl flex items-center justify-center transition-colors flex-shrink-0"
            >
              <Send size={16} className="text-white" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
