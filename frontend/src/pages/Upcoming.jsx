import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useRefreshTick } from '../realtime'
import { fmt } from '../time'
import NoteModal from '../components/NoteModal'

function Section({ title, items, tz, onOpen, empty }) {
  return (
    <>
      <h2>{title}</h2>
      <div className="list">
        {items.length === 0 && <div className="muted">{empty}</div>}
        {items.map((o) => (
          <div className="item" key={`${o.note_id}:${o.occurrence_start}`} onClick={() => onOpen(o)}>
            <div className="when">{fmt(o.starts_at, tz)}</div>
            <div className="what">
              <div className="t">
                {o.title}
                {o.is_recurring && <span className="badge">повтор</span>}
              </div>
              {o.body && <div className="b">{o.body}</div>}
            </div>
            <div>
              {o.tags.map((t) => (
                <span key={t.id} className="tag" style={{ background: t.color }}>{t.name}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

export default function Upcoming() {
  const { user } = useAuth()
  const tz = user.timezone
  const tick = useRefreshTick()
  const [data, setData] = useState(null)
  const [now, setNow] = useState(() => Date.now())
  const [modal, setModal] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    api('/upcoming')
      .then((d) => {
        setData(d)
        setError('')
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(load, [tick, load])

  // Раз в 10 секунд пересчитываем «сейчас»: прошедшие записи переезжают в «Прошедшие» без перезагрузки.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 10000)
    return () => clearInterval(id)
  }, [])

  const buckets = useMemo(() => {
    if (!data) return null
    const isFuture = (o) => new Date(o.starts_at).getTime() > now
    const moved = [...data.today, ...data.week].filter((o) => !isFuture(o))
    const key = (o) => `${o.note_id}:${o.occurrence_start}`
    const seen = new Set()
    const past = [...moved, ...data.past]
      .filter((o) => (seen.has(key(o)) ? false : seen.add(key(o))))
      .sort((a, b) => new Date(b.starts_at) - new Date(a.starts_at))
    return {
      today: data.today.filter(isFuture),
      week: data.week.filter(isFuture),
      past,
    }
  }, [data, now])

  const open = (o) => setModal({ noteId: o.note_id, occ: o })

  return (
    <>
      <h1>Ближайшее</h1>
      {error && <div className="error">{error}</div>}
      {!buckets ? (
        <div className="muted">Загрузка…</div>
      ) : (
        <>
          <Section title="Сегодня" items={buckets.today} tz={tz} onOpen={open} empty="На сегодня ничего не осталось" />
          <Section title="На этой неделе" items={buckets.week} tz={tz} onOpen={open} empty="Ничего не запланировано" />
          <Section title="Прошедшие (активные)" items={buckets.past} tz={tz} onOpen={open} empty="Пусто" />
        </>
      )}
      {modal && <NoteModal target={modal} onClose={() => setModal(null)} onChanged={load} />}
    </>
  )
}
