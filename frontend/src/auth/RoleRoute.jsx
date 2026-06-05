import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

/**
 * Redirige al dashboard correcto si el usuario tiene un rol diferente al requerido.
 * @param {string} role — 'ADMIN' | 'PROFESOR'
 */
export default function RoleRoute({ role, children }) {
  const { user } = useAuth()

  if (!user) return <Navigate to="/login" replace />

  if (user.rol !== role) {
    const redirect = user.rol === 'ADMIN' ? '/admin' : '/profesor'
    return <Navigate to={redirect} replace />
  }

  return children
}
