import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useRefreshTick } from '../realtime'
import { fmt } from '../time'

export default function Trash() {
  const { user } = useAuth()
  const tz = user.timezone
  const tick = useRefreshTick()
  const [items, setItems] = useState([])
  const [cursor, setCursor] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const page = await api('/trash', { params: { limit: 50 } })
      setItems(page.items)
      setCursor(page.next_cursor)
      setError('')
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load, tick])

  const more = async () => {
    const page = await api('/trash', { params: { limit: 50, cursor } })
    setItems((cur) => [...cur, ...page.items])
    setCursor(page.next_cursor)
  }

  const act = async (fn) => {
    try {
      await fn()
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  const restore = (n) => act(() => api(`/notes/${n.id}/restore`, { method: 'POST' }))
  const purge = (n) =>
    window.confirm(`Удалить «${n.title}» навсегда?`) && act(() => api(`/trash/${n.id}`, { method: 'DELETE' }))
  const empty = () =>
    window.confirm('Очистить корзину? Это необратимо.') && act(() => api('/trash', { method: 'DELETE' }))

  return (
    <>
      <div className="row" style={{ marginBottom: 12 }}>
        <h1 style={{ margin: 0 }}>Корзина</h1>
        <span className="muted">Заметки удаляются навсегда через 30 дней</span>
        <span className="spacer" />
        <button className="btn danger" disabled={items.length === 0} onClick={empty}>Очистить корзину</button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="list">
        {items.length === 0 && <div className="muted">Корзина пуста</div>}
        {items.map((n) => (
          <div className="item" key={n.id} style={{ cursor: 'default' }}>
            <div className="when">Удалена {fmt(n.deleted_at, tz)}</div>
            <div className="what">
              <div className="t">{n.title}</div>
              {n.body && <div className="b">{n.body}</div>}
            </div>
            <button className="btn small" onClick={() => restore(n)}>Восстановить</button>
            <button className="btn small danger" onClick={() => purge(n)}>Навсегда</button>
          </div>
        ))}
      </div>
      {cursor && (
        <div style={{ marginTop: 14 }}>
          <button className="btn" onClick={more}>Загрузить ещё</button>
        </div>
      )}
    </>
  )
}
