import { useState } from 'react'
import { useAuth } from '../auth'

export default function Login() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await register(email, username, password)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="center">
      <form className="card login" onSubmit={submit}>
        <h1>Notetaker</h1>
        <div className="tabs">
          <button type="button" className={`btn small ${mode === 'login' ? 'primary' : ''}`} onClick={() => setMode('login')}>Вход</button>
          <button type="button" className={`btn small ${mode === 'register' ? 'primary' : ''}`} onClick={() => setMode('register')}>Регистрация</button>
        </div>
        <label className="field"><span>Email</span>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        {mode === 'register' && (
          <label className="field"><span>Имя пользователя</span>
            <input type="text" required value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
        )}
        <label className="field"><span>Пароль</span>
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="btn primary" disabled={busy} style={{ width: '100%' }}>
          {mode === 'login' ? 'Войти' : 'Создать аккаунт'}
        </button>
      </form>
    </div>
  )
}
