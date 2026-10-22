import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import { fromLocalInput, nextHourLocal, toLocalInput } from '../time'

const REMINDERS = [
  [10, 'за 10 минут'],
  [60, 'за 1 час'],
  [1440, 'за 1 день'],
]
const FREQS = [
  ['', 'Не повторять'],
  ['daily', 'Каждый день'],
  ['weekly', 'Каждую неделю'],
  ['monthly', 'Каждый месяц'],
]

/**
 * target:
 *  { noteId?: number, occ?: OccurrenceRead, startLocal?: 'YYYY-MM-DDTHH:mm' }
 * Без noteId — создание. С occ у повторяющейся заметки можно править одно вхождение,
 * «это и следующие» или всю серию.
 */
export default function NoteModal({ target, onClose, onChanged }) {
  const { user } = useAuth()
  const tz = user.timezone
  const isNew = !target.noteId
  const occ = target.occ
  const recurringOcc = !!(occ && occ.is_recurring)

  const [allTags, setAllTags] = useState([])
  const [note, setNote] = useState(null)
  const [scope, setScope] = useState(recurringOcc ? 'this' : 'all')
  const [form, setForm] = useState(null)
  const [loading, setLoading] = useState(!isNew)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(null)
  const [busy, setBusy] = useState(false)

  const buildForm = (n, sc) => {
    const useOcc = occ && recurringOcc && sc !== 'all'
    return {
      title: useOcc ? occ.title : n.title,
      body: (useOcc ? occ.body : n.body) || '',
      start: toLocalInput(useOcc ? occ.starts_at : n.starts_at, tz),
      tagIds: n.tags.map((t) => t.id),
      freq: n.recurrence?.freq || '',
      until: n.recurrence?.until || '',
      reminders: n.reminders || [],
    }
  }

  useEffect(() => {
    api('/tags').then((r) => setAllTags(Array.isArray(r) ? r : r.items || [])).catch(() => {})
    if (isNew) {
      setForm({
        title: '',
        body: '',
        start: target.startLocal || nextHourLocal(tz),
        tagIds: [],
        freq: '',
        until: '',
        reminders: [],
      })
      return
    }
    api(`/notes/${target.noteId}`)
      .then((n) => {
        setNote(n)
        setForm(buildForm(n, recurringOcc ? 'this' : 'all'))
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const set = (patch) => setForm((f) => ({ ...f, ...patch }))
  const onlyOccFields = recurringOcc && scope !== 'all'

  const changeScope = (sc) => {
    setScope(sc)
    if (note) setForm(buildForm(note, sc))
  }

  const toggle = (list, v) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v])

  const request = async (version) => {
    const startsAt = fromLocalInput(form.start, tz)
    if (isNew) {
      return api('/notes', {
        method: 'POST',
        json: {
          title: form.title,
          body: form.body,
          starts_at: startsAt,
          tag_ids: form.tagIds,
          reminders: form.reminders,
          recurrence: form.freq ? { freq: form.freq, until: form.until || null } : null,
        },
      })
    }
    if (onlyOccFields) {
      return api(`/notes/${note.id}/occurrences/${encodeURIComponent(occ.occurrence_start)}`, {
        method: 'PATCH',
        json: { scope, version, title: form.title, body: form.body, starts_at: startsAt },
      })
    }
    return api(`/notes/${note.id}`, {
      method: 'PATCH',
      json: {
        version,
        title: form.title,
        body: form.body,
        starts_at: startsAt,
        tag_ids: form.tagIds,
        reminders: form.reminders,
        recurrence: form.freq ? { freq: form.freq, until: form.until || null } : null,
      },
    })
  }

  // Общая обработка: 409 никогда не теряет правки молча, пользователь выбирает, что делать.
  const run = async (fn) => {
    setBusy(true)
    setError('')
    try {
      await fn()
      onChanged?.()
      onClose()
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && e.body?.current) {
        setConflict(e.body.current)
      } else setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const save = (e) => {
    e?.preventDefault()
    run(() => request(note?.version))
  }

  const overwrite = () => {
    const current = conflict
    setConflict(null)
    setNote(current)
    run(() => request(current.version))
  }

  const reload = () => {
    setNote(conflict)
    setForm(buildForm(conflict, scope))
    setConflict(null)
  }

  const remove = () => {
    const what = onlyOccFields
      ? scope === 'this' ? 'это вхождение' : 'это и следующие вхождения'
      : 'заметку'
    if (!window.confirm(`Удалить ${what}?`)) return
    run(() => {
      if (onlyOccFields) {
        return api(`/notes/${note.id}/occurrences/${encodeURIComponent(occ.occurrence_start)}`, {
          method: 'DELETE',
          params: { scope, version: note.version },
        })
      }
      return api(`/notes/${note.id}`, { method: 'DELETE' })
    })
  }

  const toggleActive = () =>
    run(() =>
      api(`/notes/${note.id}/${note.is_active ? 'deactivate' : 'activate'}`, {
        method: 'POST',
        json: { version: note.version },
      }),
    )

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal" onSubmit={save}>
        <h2>{isNew ? 'Новая заметка' : 'Заметка'}</h2>
        {loading || !form ? (
          <div className="muted">{error || 'Загрузка…'}</div>
        ) : (
          <>
            {conflict && (
              <div className="conflict">
                <strong>Заметку уже изменили в другом месте.</strong>
                <div className="muted">
                  Актуальная версия: «{conflict.title}» (v{conflict.version}). Ваши правки пока не сохранены.
                </div>
                <div className="row" style={{ marginTop: 8 }}>
                  <button type="button" className="btn small" onClick={reload}>Загрузить актуальную</button>
                  <button type="button" className="btn small primary" onClick={overwrite}>Сохранить мои правки поверх</button>
                </div>
              </div>
            )}

            {recurringOcc && (
              <label className="field"><span>Что изменить</span>
                <select value={scope} onChange={(e) => changeScope(e.target.value)}>
                  <option value="this">Только это вхождение</option>
                  <option value="following">Это и все следующие</option>
                  <option value="all">Всю серию</option>
                </select>
              </label>
            )}

            <label className="field"><span>Заголовок</span>
              <input type="text" required maxLength={200} value={form.title} onChange={(e) => set({ title: e.target.value })} autoFocus />
            </label>
            <label className="field"><span>Текст</span>
              <textarea value={form.body} onChange={(e) => set({ body: e.target.value })} />
            </label>
            <label className="field"><span>Дата и время ({tz})</span>
              <input type="datetime-local" required value={form.start} onChange={(e) => set({ start: e.target.value })} />
            </label>

            {!onlyOccFields && (
              <>
                <div className="field">
                  <span className="muted" style={{ fontSize: 12 }}>Теги</span>
                  <div>
                    {allTags.length === 0 && <span className="muted">Тегов пока нет — создайте их на вкладке «Теги»</span>}
                    {allTags.map((t) => (
                      <button
                        type="button"
                        key={t.id}
                        className={`tag pick ${form.tagIds.includes(t.id) ? 'on' : ''}`}
                        style={{ background: t.color }}
                        onClick={() => set({ tagIds: toggle(form.tagIds, t.id) })}
                      >
                        {t.name}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="row">
                  <label className="field grow"><span>Повтор</span>
                    <select value={form.freq} onChange={(e) => set({ freq: e.target.value })}>
                      {FREQS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </label>
                  {form.freq && (
                    <label className="field grow"><span>Повторять до (включительно)</span>
                      <input type="date" value={form.until} onChange={(e) => set({ until: e.target.value })} />
                    </label>
                  )}
                </div>

                <div className="field">
                  <span className="muted" style={{ fontSize: 12 }}>Напоминания</span>
                  <div className="checks">
                    {REMINDERS.map(([v, l]) => (
                      <label key={v}>
                        <input type="checkbox" checked={form.reminders.includes(v)} onChange={() => set({ reminders: toggle(form.reminders, v) })} />
                        {l}
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}

            {error && <div className="error">{error}</div>}
            <div className="actions">
              <button className="btn primary" disabled={busy}>Сохранить</button>
              <button type="button" className="btn" onClick={onClose}>Отмена</button>
              <span className="spacer" />
              {!isNew && !onlyOccFields && (
                <button type="button" className="btn" disabled={busy} onClick={toggleActive}>
                  {note?.is_active ? 'Сделать неактивной' : 'Сделать активной'}
                </button>
              )}
              {!isNew && (
                <button type="button" className="btn danger" disabled={busy} onClick={remove}>Удалить</button>
              )}
            </div>
          </>
        )}
      </form>
    </div>
  )
}
