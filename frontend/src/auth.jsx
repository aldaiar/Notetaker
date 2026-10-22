import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken, setUnauthorizedHandler } from './api'

const AuthContext = createContext(null)
export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!getToken()) return
    api('/users/me')
      .then(setUser)
      .catch(() => logout())
      .finally(() => setLoading(false))
  }, [logout])

  const login = async (email, password) => {
  const data = await api('/auth/login', {
    method: 'POST',
    json: {
      email,
      password,
    },
  })

  setToken(data.access_token)
  setUser(await api('/users/me'))
}

  const register = async (email, username, password) => {
    await api('/auth/register', { method: 'POST', json: { email, username, password } })
    await login(email, password)
  }

  const refreshUser = async () => setUser(await api('/users/me'))

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}
