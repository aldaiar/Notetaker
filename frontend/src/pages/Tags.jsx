import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { useRefreshTick } from '../realtime'

function TagRow({ tag, onSave, onDelete }) {
  const [name, setName] = useState(tag.name)
  const [color, setColor] = useState(tag.color)
  useEffect(() => {
    setName(tag.name)
    setColor(tag.color)
  }, [tag.name, tag.color])
  const dirty = name !== tag.name || color !== tag.color
  return (
    <div className="item" style={{ cursor: 'default' }}>
      <input type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ width: 40, height: 30, padding: 0, border: 0 }} />
      <input type="text" value={name} onChange={(e) => setName(e.target.value)} style={{ maxWidth: 260 }} />
      <span className="tag" style={{ background: color }}>{name || '…'}</span>
      <span className="spacer" />
      <button className="btn small primary" disabled={!dirty} onClick={() => onSave(tag, { name, color })}>Сохранить</button>
      <button className="btn small danger" onClick={() => onDelete(tag)}>Удалить</button>
    </div>
  )
}

export default function Tags() {
  const tick = useRefreshTick()
  const [tags, setTags] = useState([])
  const [name, setName] = useState('')
  const [color, setColor] = useState('#3b6ef5')
  const [error, setError] = useState('')

  const load = useCallback(() => {
    api('/tags')
      .then((r) => setTags(Array.isArray(r) ? r : r.items || []))
      .catch((e) => setError(e.message))
  }, [])
  useEffect(load, [load, tick])

  const act = async (fn) => {
    try {
      await fn()
      setError('')
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const create = (e) => {
    e.preventDefault()
    act(async () => {
      await api('/tags', { method: 'POST', json: { name, color } })
      setName('')
    })
  }
  const save = (t, patch) => act(() => api(`/tags/${t.id}`, { method: 'PATCH', json: patch }))
  const remove = (t) =>
    window.confirm(`Удалить тег «${t.name}»? Он будет снят со всех заметок.`) &&
    act(() => api(`/tags/${t.id}`, { method: 'DELETE' }))

  return (
    <>
      <h1>Теги</h1>
      <form className="row card" onSubmit={create} style={{ marginBottom: 16 }}>
        <input type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ width: 40, height: 30, padding: 0, border: 0 }} />
        <input className="grow" type="text" required maxLength={50} placeholder="Название нового тега" value={name} onChange={(e) => setName(e.target.value)} />
        <button className="btn primary">Добавить</button>
      </form>
      {error && <div className="error">{error}</div>}
      <div className="list">
        {tags.length === 0 && <div className="muted">Тегов пока нет</div>}
        {tags.map((t) => <TagRow key={t.id} tag={t} onSave={save} onDelete={remove} />)}
      </div>
    </>
  )
}
