/**
 * AuthContext — gestión global de sesión JWT.
 *
 * Estado: user = { id, email, nombre, rol, is_active, perfil_profesor }
 *         loading = true mientras se verifica el token inicial.
 */

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { login as apiLogin, me as apiMe } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  /* Carga el usuario al montar si ya hay un token almacenado */
  useEffect(() => {
    const access = localStorage.getItem('access')
    if (!access) {
      setLoading(false)
      return
    }
    apiMe()
      // MeView devuelve { success: true, data: { id, email, rol, ... } }
      .then((res) => setUser(res.data?.data ?? res.data))
      .catch(() => {
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await apiLogin(email, password)
    const { access, refresh } = res.data
    localStorage.setItem('access', access)
    localStorage.setItem('refresh', refresh)
    // Cargar perfil completo (incluye perfil_profesor si aplica)
    const meRes = await apiMe()
    // MeView devuelve { success: true, data: { id, email, rol, ... } }
    const userData = meRes.data?.data ?? meRes.data
    setUser(userData)
    return userData
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
