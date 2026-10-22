import { useEffect } from 'react'
import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import { connectEvents } from './realtime'
import Notifier from './components/Notifier'
import Login from './pages/Login'
import CalendarPage from './pages/Calendar'
import ListPage from './pages/List'
import Upcoming from './pages/Upcoming'
import Trash from './pages/Trash'
import Tags from './pages/Tags'
import Settings from './pages/Settings'

function Layout() {
  const { user, logout } = useAuth()

  // Одно SSE-соединение на вкладку, пока пользователь авторизован.
  useEffect(() => connectEvents(), [])

  const link = ({ isActive }) => (isActive ? 'active' : '')
  return (
    <div className="app">
      <header className="topbar">
        <strong className="brand">Notetaker</strong>
        <nav>
          <NavLink to="/" end className={link}>Календарь</NavLink>
          <NavLink to="/upcoming" className={link}>Ближайшее</NavLink>
          <NavLink to="/notes" className={link}>Список</NavLink>
          <NavLink to="/tags" className={link}>Теги</NavLink>
          <NavLink to="/trash" className={link}>Корзина</NavLink>
          <NavLink to="/settings" className={link}>Настройки</NavLink>
        </nav>
        <span className="spacer" />
        <span className="muted">{user.username}</span>
        <button className="btn small" onClick={logout}>Выйти</button>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<CalendarPage />} />
          <Route path="/upcoming" element={<Upcoming />} />
          <Route path="/notes" element={<ListPage />} />
          <Route path="/tags" element={<Tags />} />
          <Route path="/trash" element={<Trash />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
      <Notifier />
    </div>
  )
}

export default function App() {
  const { user, loading } = useAuth()
  if (loading) return <div className="center muted">Загрузка…</div>
  if (!user) return <Login />
  return <Layout />
}
