import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import Loading from '../components/ui/Loading'

/**
 * Redirige a /login si el usuario no está autenticado.
 * Guarda la ruta original para redirigir después del login.
 */
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <Loading fullscreen />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}
