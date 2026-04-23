import { cn } from '../lib/utils'

interface Props {
  children: React.ReactNode
  variant?: 'default' | 'run' | 'gym' | 'pending' | 'processed' | 'failed'
}

const variants = {
  default: 'bg-slate-700 text-slate-300',
  run: 'bg-blue-500/20 text-blue-300',
  gym: 'bg-purple-500/20 text-purple-300',
  pending: 'bg-yellow-500/20 text-yellow-300',
  processed: 'bg-green-500/20 text-green-300',
  failed: 'bg-red-500/20 text-red-300',
}

export function Badge({ children, variant = 'default' }: Props) {
  return (
    <span className={cn('inline-flex px-2 py-0.5 rounded text-xs font-medium', variants[variant])}>
      {children}
    </span>
  )
}
