const BASE = '/api'

let token = localStorage.getItem('token')
let onUnauthorized = () => {}

export const getToken = () => token
export const setToken = (t) => {
  token = t
  if (t) localStorage.setItem('token', t)
  else localStorage.removeItem('token')
}
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn
}
export const apiBase = BASE

export class ApiError extends Error {
  constructor(status, body) {
    super(describe(body))
    this.status = status
    this.body = body
  }
}

function describe(body) {
  const d = body?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((e) => e.msg).join('; ')
  return 'Ошибка запроса'
}

export async function api(path, { method = 'GET', json, form, params } = {}) {
  const url = new URL(BASE + path, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null || v === '') continue
      if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, x))
      else url.searchParams.set(k, v)
    }
  }
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  let body
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form) {
    body = new URLSearchParams(form)
  }
  const res = await fetch(url, { method, headers, body })
  if (res.status === 204) return null
  let data = null
  try {
    data = await res.json()
  } catch {
    /* пустое тело */
  }
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    throw new ApiError(res.status, data)
  }
  return data
}
