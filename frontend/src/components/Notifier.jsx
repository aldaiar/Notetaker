import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { subscribe } from '../realtime'
import { useAuth } from '../auth'
import { fmt } from '../time'

/**
 * Уведомления о напоминаниях. Приходят по SSE во все вкладки.
 * «Один раз»: сервер помечает уведомление seen; событие notification.seen
 * убирает тост и в остальных вкладках. Браузерное Notification показываем с tag=id,
 * поэтому повторно оно не всплывает.
 */
export default function Notifier() {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const shown = useRef(new Set())

  const show = useCallback((n) => {
    if (n.seen_at || shown.current.has(n.id)) return
    shown.current.add(n.id)
    setItems((cur) => [...cur, n])
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification(n.title, {
          body: `Начало: ${fmt(n.occurrence_starts_at, user.timezone)}`,
          tag: `note-notification-${n.id}`,
        })
      } catch {
        /* ignore */
      }
    }
  }, [user.timezone])

  const loadUnseen = useCallback(async () => {
    try {
      const list = await api('/notifications', { params: { unseen: true } })
      ;(Array.isArray(list) ? list : list.items || []).forEach(show)
    } catch {
      /* ignore */
    }
  }, [show])

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
    loadUnseen()
    return subscribe((type, data) => {
      if (type === 'hello') loadUnseen() // догоняем пропущенное при (пере)подключении
      if (type === 'notification.new') {
        if (data && data.id && data.title) show(data)
        else loadUnseen()
      }
      if (type === 'notification.seen' && data?.id) {
        setItems((cur) => cur.filter((x) => x.id !== data.id))
      }
    })
  }, [loadUnseen, show])

  const dismiss = async (n) => {
    setItems((cur) => cur.filter((x) => x.id !== n.id))
    try {
      await api(`/notifications/${n.id}/seen`, { method: 'POST' })
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="toasts">
      {items.map((n) => (
        <div className="toast" key={n.id}>
          <strong>🔔 {n.title}</strong>
          <div>Начало: {fmt(n.occurrence_starts_at, user.timezone)}</div>
          <div className="row">
            <button className="btn small" onClick={() => dismiss(n)}>Понятно</button>
          </div>
        </div>
      ))}
    </div>
  )
}
