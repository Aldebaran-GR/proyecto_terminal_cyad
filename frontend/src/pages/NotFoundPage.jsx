import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function NotFoundPage() {
  const { user } = useAuth()
  const home = !user ? '/login' : user.rol === 'ADMIN' ? '/admin' : '/profesor'

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center">
      <p className="text-6xl font-black text-slate-200">404</p>
      <h1 className="mt-4 text-xl font-bold text-slate-800">Página no encontrada</h1>
      <p className="mt-2 text-sm text-slate-500">
        La ruta que buscas no existe.
      </p>
      <Link
        to={home}
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
      >
        Volver al inicio
      </Link>
    </div>
  )
}
