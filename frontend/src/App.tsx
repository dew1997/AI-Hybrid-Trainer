import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { Sidebar } from './components/Sidebar'
import { Spinner } from './components/Spinner'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { Dashboard } from './pages/Dashboard'
import { Workouts } from './pages/Workouts'
import { LogWorkout } from './pages/LogWorkout'
import { Coaching } from './pages/Coaching'
import { Plans } from './pages/Plans'
import { Settings } from './pages/Settings'

function ProtectedLayout() {
  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar />
      <main className="ml-60 flex-1 p-6 max-w-5xl">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/workouts" element={<Workouts />} />
          <Route path="/log" element={<LogWorkout />} />
          <Route path="/coaching" element={<Coaching />} />
          <Route path="/plans" element={<Plans />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Spinner size={32} />
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/" replace /> : <Register />} />
      <Route path="/*" element={isAuthenticated ? <ProtectedLayout /> : <Navigate to="/login" replace />} />
    </Routes>
  )
}
