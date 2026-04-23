import { cn } from '../lib/utils'
import type { ReactNode } from 'react'

interface Props {
  label: string
  value: string | number
  sub?: string
  valueClass?: string
  icon?: ReactNode
}

export function StatCard({ label, value, sub, valueClass, icon }: Props) {
  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
        {icon && <span className="text-slate-500">{icon}</span>}
      </div>
      <p className={cn('text-2xl font-bold text-white', valueClass)}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}
