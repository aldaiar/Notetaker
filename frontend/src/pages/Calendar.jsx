import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import luxon3Plugin from '@fullcalendar/luxon3'
import ruLocale from '@fullcalendar/core/locales/ru'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import { useRefreshTick } from '../realtime'
import { toUtcZ } from '../time'
import NoteModal from '../components/NoteModal'

const MAX_DAYS = 100

export default function CalendarPage() {
  const { user } = useAuth()
  const tz = user.timezone
  const tick = useRefreshTick()
  const [events, setEvents] = useState([])
  const [modal, setModal] = useState(null)
  const [error, setError] = useState('')
  const rangeRef = useRef(null)

  const load = useCallback(async () => {
    const r = rangeRef.current
    if (!r) return
    try {
      const data = await api('/calendar', {
        params: { from: toUtcZ(r.startStr, tz), to: toUtcZ(r.endStr, tz) },
      })
      setEvents(
        data.map((o) => ({
          id: `${o.note_id}:${o.occurrence_start}`,
          title: o.title,
          start: o.starts_at, // UTC ISO; FullCalendar покажет в timeZone пользователя
          backgroundColor: o.tags[0]?.color || '#3b6ef5',
          borderColor: o.tags[0]?.color || '#3b6ef5',
          classNames: o.is_active ? [] : ['ev-inactive'],
          extendedProps: { occ: o },
        })),
      )
    } catch (e) {
      setError(e.message)
    }
  }, [tz])

  // Любое событие с сервера (другая вкладка, смена пояса и т.д.) перечитывает видимый диапазон.
  useEffect(() => {
    load()
  }, [tick, load])

  const onDates = (arg) => {
    // Бэкенд ограничивает диапазон 100 днями; месячная сетка укладывается с запасом.
    const s = new Date(arg.start)
    const e = new Date(arg.end)
    if ((e - s) / 86400000 > MAX_DAYS) return
    rangeRef.current = { startStr: arg.startStr, endStr: arg.endStr }
    load()
  }

  const onDrop = async (info) => {
    const occ = info.event.extendedProps.occ
    try {
      // Версия нужна для оптимистичной блокировки: берём свежую
      const note = await api(`/notes/${occ.note_id}`)
      const newStart = toUtcZ(info.event.startStr, tz)
      if (occ.is_recurring) {
        const scope = window.confirm(
          'Перенести только это вхождение?\n\nOK — только это, Отмена — это и все следующие',
        )
          ? 'this'
          : 'following'
        await api(`/notes/${occ.note_id}/occurrences/${encodeURIComponent(occ.occurrence_start)}`, {
          method: 'PATCH',
          json: { scope, version: note.version, starts_at: newStart },
        })
      } else {
        await api(`/notes/${occ.note_id}`, {
          method: 'PATCH',
          json: { version: note.version, starts_at: newStart },
        })
      }
      setError('')
    } catch (e) {
      info.revert()
      setError(
        e instanceof ApiError && e.status === 409
          ? 'Заметка была изменена в другом месте — перенос отменён, данные обновлены.'
          : e.message,
      )
    }
    load()
  }

  const plugins = useMemo(() => [dayGridPlugin, timeGridPlugin, interactionPlugin, luxon3Plugin], [])

  return (
    <>
      <div className="row" style={{ marginBottom: 12 }}>
        <h1 style={{ margin: 0 }}>Календарь</h1>
        <span className="spacer" />
        <button className="btn primary" onClick={() => setModal({})}>+ Новая заметка</button>
      </div>
      {error && <div className="error">{error}</div>}
      <FullCalendar
        plugins={plugins}
        locales={[ruLocale]}
        locale="ru"
        timeZone={tz}
        initialView="dayGridMonth"
        firstDay={1}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay',
        }}
        height="auto"
        editable
        eventDurationEditable={false}
        events={events}
        datesSet={onDates}
        eventDrop={onDrop}
        dateClick={(a) => setModal({ startLocal: a.dateStr.length > 10 ? a.dateStr.slice(0, 16) : `${a.dateStr}T09:00` })}
        eventClick={(a) => {
          const occ = a.event.extendedProps.occ
          setModal({ noteId: occ.note_id, occ })
        }}
        eventTimeFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
        dayMaxEvents={4}
      />
      {modal && <NoteModal target={modal} onClose={() => setModal(null)} onChanged={load} />}
    </>
  )
}
