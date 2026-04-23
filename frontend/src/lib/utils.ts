import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatPace(secPerKm: number | null): string {
  if (!secPerKm) return '—'
  const min = Math.floor(secPerKm / 60)
  const sec = Math.round(secPerKm % 60)
  return `${min}:${sec.toString().padStart(2, '0')}/km`
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function formatDistance(meters: number | null): string {
  if (!meters) return '—'
  return `${(meters / 1000).toFixed(2)} km`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

export function paceZoneColor(zone: string | null): string {
  const map: Record<string, string> = {
    Z1_recovery: 'text-blue-400',
    Z2_aerobic: 'text-green-400',
    Z3_tempo: 'text-yellow-400',
    Z4_vo2max: 'text-orange-400',
    Z5_sprint: 'text-red-400',
  }
  return zone ? (map[zone] ?? 'text-slate-400') : 'text-slate-400'
}

export function tsbColor(tsb: number | null): string {
  if (tsb === null) return 'text-slate-400'
  if (tsb > 10) return 'text-green-400'
  if (tsb > -10) return 'text-yellow-400'
  return 'text-red-400'
}
