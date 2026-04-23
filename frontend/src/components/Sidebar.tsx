import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Activity, Dumbbell, Bot, CalendarCheck, Settings, LogOut } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { cn } from '../lib/utils'

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/workouts', icon: Activity, label: 'Workouts' },
  { to: '/log', icon: Dumbbell, label: 'Log Workout' },
  { to: '/coaching', icon: Bot, label: 'AI Coaching' },
  { to: '/plans', icon: CalendarCheck, label: 'Training Plans' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-slate-900 border-r border-slate-800 flex flex-col z-10">
      <div className="px-5 py-6 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Activity size={16} className="text-white" />
          </div>
          <span className="font-semibold text-white text-sm">AI Trainer</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-indigo-600/20 text-indigo-400 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-200 truncate max-w-[130px]">
              {user?.display_name || user?.email}
            </p>
            <p className="text-xs text-slate-500 capitalize">{user?.primary_goal || 'athlete'}</p>
          </div>
          <button
            onClick={logout}
            className="p-1.5 rounded-md text-slate-500 hover:text-red-400 hover:bg-slate-800 transition-colors"
            title="Sign out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  )
}
