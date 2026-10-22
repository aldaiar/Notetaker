import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useRefreshTick } from '../realtime'
import { fmt } from '../time'
import NoteModal from '../components/NoteModal'

export default function ListPage() {
  const { user } = useAuth()
  const tz = user.timezone
  const tick = useRefreshTick()

  const [q, setQ] = useState('')
  const [dq, setDq] = useState('')
  const [tagIds, setTagIds] = useState([])
  const [active, setActive] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [sort, setSort] = useState('starts_at')
  const [order, setOrder] = useState('desc')

  const [tags, setTags] = useState([])
  const [items, setItems] = useState([])
  const [cursor, setCursor] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const reqId = useRef(0)

  // Поиск с задержкой, чтобы не слать запрос на каждую букву.
  useEffect(() => {
    const t = setTimeout(() => setDq(q), 300)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    api('/tags').then((r) => setTags(Array.isArray(r) ? r : r.items || [])).catch(() => {})
  }, [tick])

  const params = useCallback(
    (cur) => ({
      q: dq,
      tag_ids: tagIds,
      is_active: active,
      date_from: from ? `${from}T00:00:00Z` : '',
      date_to: to ? `${to}T23:59:59Z` : '',
      sort,
      order,
      cursor: cur,
      limit: 50,
    }),
    [dq, tagIds, active, from, to, sort, order],
  )

  const loadFirst = useCallback(async () => {
    const id = ++reqId.current
    setLoading(true)
    try {
      const page = await api('/notes', { params: params(null) })
      if (id !== reqId.current) return // устаревший ответ
      setItems(page.items)
      setCursor(page.next_cursor)
      setError('')
    } catch (e) {
      if (id === reqId.current) setError(e.message)
    } finally {
      if (id === reqId.current) setLoading(false)
    }
  }, [params])

  useEffect(() => {
    loadFirst()
  }, [loadFirst, tick])

  const more = async () => {
    setLoading(true)
    try {
      const page = await api('/notes', { params: params(cursor) })
      setItems((cur) => [...cur, ...page.items])
      setCursor(page.next_cursor)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleTag = (id) =>
    setTagIds((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))

  return (
    <>
      <div className="row" style={{ marginBottom: 12 }}>
        <h1 style={{ margin: 0 }}>Все заметки</h1>
        <span className="spacer" />
        <button className="btn primary" onClick={() => setModal({})}>+ Новая заметка</button>
      </div>

      <div className="filters">
        <input type="search" placeholder="Поиск по заголовку и тексту" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={active} onChange={(e) => setActive(e.target.value)}>
          <option value="">Любые</option>
          <option value="true">Активные</option>
          <option value="false">Неактивные</option>
        </select>
        <label className="muted">с <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} style={{ width: 'auto' }} /></label>
        <label className="muted">по <input type="date" value={to} onChange={(e) => setTo(e.target.value)} style={{ width: 'auto' }} /></label>
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="starts_at">По дате заметки</option>
          <option value="updated_at">По изменению</option>
        </select>
        <select value={order} onChange={(e) => setOrder(e.target.value)}>
          <option value="desc">Сначала новые</option>
          <option value="asc">Сначала старые</option>
        </select>
      </div>
      {tags.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          {tags.map((t) => (
            <button
              key={t.id}
              className={`tag pick ${tagIds.includes(t.id) ? 'on' : ''}`}
              style={{ background: t.color }}
              onClick={() => toggleTag(t.id)}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}

      {error && <div className="error">{error}</div>}
      <div className="list">
        {items.map((n) => (
          <div key={n.id} className={`item ${n.is_active ? '' : 'inactive'}`} onClick={() => setModal({ noteId: n.id })}>
            <div className="when">{fmt(n.starts_at, tz)}</div>
            <div className="what">
              <div className="t">
                {n.title}
                {n.recurrence && <span className="badge">повтор</span>}
                {!n.is_active && <span className="badge">неактивна</span>}
              </div>
              {n.body && <div className="b">{n.body}</div>}
            </div>
            <div>
              {n.tags.map((t) => (
                <span key={t.id} className="tag" style={{ background: t.color }}>{t.name}</span>
              ))}
            </div>
          </div>
        ))}
        {!loading && items.length === 0 && <div className="muted">Ничего не найдено</div>}
      </div>
      {cursor && (
        <div style={{ marginTop: 14 }}>
          <button className="btn" disabled={loading} onClick={more}>Загрузить ещё</button>
        </div>
      )}
      {loading && <div className="muted" style={{ marginTop: 10 }}>Загрузка…</div>}
      {modal && <NoteModal target={modal} onClose={() => setModal(null)} onChanged={loadFirst} />}
    </>
  )
}
