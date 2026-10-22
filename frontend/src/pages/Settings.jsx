import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { subscribe } from '../realtime'
import { TIMEZONES } from '../time'

export default function Settings() {
  const { user, refreshUser } = useAuth()
  const [email, setEmail] = useState(user.email)
  const [timezone, setTimezone] = useState(user.timezone)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  // Настройки изменили в другой вкладке — подтягиваем.
  useEffect(
    () =>
      subscribe((type) => {
        if (type === 'settings.updated') refreshUser()
      }),
    [refreshUser],
  )
  useEffect(() => {
    setEmail(user.email)
    setTimezone(user.timezone)
  }, [user.email, user.timezone])

  const save = async (e) => {
    e.preventDefault()
    setMsg('')
    setError('')
    try {
      await api('/users/me', { method: 'PATCH', json: { email, timezone } })
      await refreshUser()
      setMsg('Сохранено')
    } catch (err) {
      setError(err.message)
    }
  }

  const detect = () => setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone)

  return (
    <>
      <h1>Настройки</h1>
      <form className="card" onSubmit={save} style={{ maxWidth: 480 }}>
        <label className="field"><span>Email для напоминаний</span>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field"><span>Часовой пояс</span>
          <input type="text" list="tzlist" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          <datalist id="tzlist">
            {TIMEZONES.map((z) => <option key={z} value={z} />)}
          </datalist>
        </label>
        <div className="row">
          <button className="btn primary">Сохранить</button>
          <button type="button" className="btn" onClick={detect}>Определить по браузеру</button>
        </div>
        {msg && <div style={{ color: 'var(--ok)', marginTop: 8 }}>{msg}</div>}
        {error && <div className="error">{error}</div>}
        <p className="muted" style={{ marginTop: 16 }}>
          Время всех заметок хранится в UTC и показывается в выбранном поясе. У уже созданных
          повторяющихся серий пояс фиксируется при создании, поэтому их время не «плывёт» при смене пояса.
        </p>
      </form>
    </>
  )
}
