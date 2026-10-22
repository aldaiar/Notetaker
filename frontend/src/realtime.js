import { useEffect, useState } from 'react'
import { api, apiBase } from './api'

// Простая шина: SSE-события раздаются подписчикам внутри вкладки.
const listeners = new Set()
export const subscribe = (fn) => {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
const emit = (type, data) => listeners.forEach((fn) => fn(type, data))

const EVENT_TYPES = [
  'hello',
  'note.created',
  'note.updated',
  'note.deleted',
  'note.restored',
  'note.purged',
  'trash.emptied',
  'tag.created',
  'tag.updated',
  'tag.deleted',
  'settings.updated',
  'notification.new',
  'notification.seen',
]

/** Подключение к /events. Токен живёт 60 секунд и нужен только при подключении. */
export function connectEvents() {
  let es = null
  let timer = null
  let closed = false

  const connect = async () => {
    if (closed) return
    try {
      const { token } = await api('/events/token', { method: 'POST' })
      es = new EventSource(`${apiBase}/events?token=${encodeURIComponent(token)}`)
      EVENT_TYPES.forEach((t) =>
        es.addEventListener(t, (e) => {
          let data = {}
          try {
            data = JSON.parse(e.data)
          } catch {
            /* ignore */
          }
          emit(t, data)
        }),
      )
      es.onerror = () => {
        // При 401 или потере соединения EventSource не переподключится с новым токеном сам.
        if (es && es.readyState === EventSource.CLOSED) {
          es.close()
          if (!closed) timer = setTimeout(connect, 3000)
        }
      }
    } catch {
      if (!closed) timer = setTimeout(connect, 5000)
    }
  }
  connect()

  return () => {
    closed = true
    clearTimeout(timer)
    if (es) es.close()
  }
}

/** Счётчик, который растёт при любом событии, меняющем данные: страницы перечитывают данные. */
export function useRefreshTick() {
  const [tick, setTick] = useState(0)
  useEffect(
    () =>
      subscribe((type) => {
        if (type !== 'notification.new' && type !== 'notification.seen') setTick((n) => n + 1)
      }),
    [],
  )
  return tick
}
