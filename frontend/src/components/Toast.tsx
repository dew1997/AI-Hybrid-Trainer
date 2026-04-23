import { CheckCircle, AlertCircle, Info, X } from 'lucide-react'
import { useToast, type Toast } from '../hooks/useToast'

const ICON_MAP = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
}

const CONTAINER_CLS: Record<Toast['type'], string> = {
  success: 'bg-green-950/90 border-green-800 text-green-100',
  error: 'bg-red-950/90 border-red-800 text-red-100',
  info: 'bg-slate-800 border-slate-700 text-slate-200',
}

const ICON_CLS: Record<Toast['type'], string> = {
  success: 'text-green-400',
  error: 'text-red-400',
  info: 'text-indigo-400',
}

export function ToastContainer() {
  const { toasts, dismiss } = useToast()

  if (!toasts.length) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)]">
      {toasts.map(t => {
        const Icon = ICON_MAP[t.type]
        return (
          <div
            key={t.id}
            className={`flex items-start gap-3 border rounded-xl px-4 py-3 shadow-xl backdrop-blur-sm ${CONTAINER_CLS[t.type]}`}
          >
            <Icon size={16} className={`flex-shrink-0 mt-0.5 ${ICON_CLS[t.type]}`} />
            <p className="flex-1 text-sm leading-snug">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              className="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
