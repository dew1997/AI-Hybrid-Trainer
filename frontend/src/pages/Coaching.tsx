import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { agentApi } from '../api/agent'
import { useToast } from '../hooks/useToast'
import { Spinner } from '../components/Spinner'
import { Send, Bot, User, Lightbulb } from 'lucide-react'

interface Message {
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

export function Coaching() {
  const { toast } = useToast()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const mutation = useMutation({
    mutationFn: (query: string) => agentApi.coachingQuery(query).then(r => r.data),
    onSuccess: (data, query) => {
      setMessages(prev => [
        ...prev,
        { role: 'user', content: query },
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
          actions: data.suggested_actions,
        },
      ])
    },
    onError: () => {
      toast('error', 'Coach query failed — please try again')
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ])
    },
  })

  const send = (query: string) => {
    if (!query.trim() || mutation.isPending) return
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setInput('')
    mutation.mutate(query)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-80px)]">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-white">AI Coaching</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Ask anything about your training — powered by Claude
        </p>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
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

        {messages.map((m, i) => (
          <div key={i} className={`flex items-start gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
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
                {m.content}
              </div>

              {m.actions && m.actions.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs text-slate-500 flex items-center gap-1">
                    <Lightbulb size={11} /> Action items
                  </p>
                  {m.actions.map((a, j) => (
                    <div key={j} className="flex items-start gap-2 bg-indigo-600/10 border border-indigo-500/20 rounded-lg px-3 py-2">
                      <span className="w-4 h-4 rounded-full bg-indigo-600/40 text-indigo-300 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                        {j + 1}
                      </span>
                      <p className="text-xs text-indigo-200">{a}</p>
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
        ))}

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

      {/* Input */}
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
  )
}
