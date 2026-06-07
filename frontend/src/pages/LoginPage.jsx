import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Button from '../components/ui/Button'
import Alert from '../components/ui/Alert'
import FormField, { inputCls } from '../components/ui/FormField'

const schema = z.object({
  email: z.string().email('Correo electrónico inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

export default function LoginPage() {
  const { login, user } = useAuth()
  const location = useLocation()
  // apiError = { type: 'error' | 'warning', title?: string, message: string } | null
  const [apiError, setApiError] = useState(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  /*
   * Si el usuario ya está autenticado, redirigir al dashboard correcto.
   * Usamos <Navigate> (declarativo) — nunca navigate() dentro del render.
   * La ruta "from" preserva el destino original antes de ser enviado al login.
   */
  if (user) {
    const from = location.state?.from?.pathname
    const dest = from ?? (user.rol === 'ADMIN' ? '/admin' : '/profesor')
    return <Navigate to={dest} replace />
  }

  /*
   * onSubmit: solo llama login() y maneja errores.
   * La redirección la hace el if(user) de arriba al re-renderizar
   * con el nuevo estado del AuthContext.
   */
  const onSubmit = async ({ email, password }) => {
    setApiError(null)
    try {
      await login(email, password)
      // No llamamos navigate() — el re-render con user!=null activa <Navigate> arriba
    } catch (err) {
      // El backend usa api_exception_handler que envuelve los errores en
      //   { success: false, status_code, errors: <payload original DRF> }
      // Para el login los dos casos posibles son:
      //  - Cuenta desactivada (credenciales válidas pero is_active=False):
      //      errors: { code: 'account_disabled', detail: '...' }
      //  - Credenciales incorrectas (SimpleJWT estándar):
      //      errors: { detail: 'No active account found ...' }
      const data = err?.response?.data
      const payload =
        (data && typeof data === 'object' && data.errors) || data || {}
      const code = payload?.code
      const detailMsg =
        typeof payload?.detail === 'string' ? payload.detail : null

      if (code === 'account_disabled') {
        setApiError({
          type: 'warning',
          title: 'Cuenta desactivada',
          message:
            detailMsg ||
            'Tu cuenta se encuentra desactivada. Contacta al administrador para reactivarla.',
        })
      } else {
        setApiError({
          type: 'error',
          title: 'Credenciales incorrectas',
          message:
            detailMsg ||
            payload?.non_field_errors?.[0] ||
            'Credenciales incorrectas. Verifica tu correo y contraseña.',
        })
      }
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="mb-8 text-center">
          <span className="inline-block rounded-xl bg-indigo-600 px-3 py-1 text-xs font-bold uppercase tracking-widest text-white">
            CyAD · UAM-A
          </span>
          <h1 className="mt-4 text-2xl font-bold text-slate-900">
            Sistema de Proyecto Terminal
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Inicia sesión con tu cuenta institucional
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
          {apiError && (
            <div className="mb-5">
              <Alert
                type={apiError.type}
                title={apiError.title}
                onClose={() => setApiError(null)}
              >
                {apiError.message}
              </Alert>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
            <FormField label="Correo electrónico" error={errors.email?.message} required>
              <input
                {...register('email')}
                type="email"
                autoComplete="email"
                placeholder="usuario@uam.mx"
                className={inputCls}
              />
            </FormField>

            <FormField label="Contraseña" error={errors.password?.message} required>
              <input
                {...register('password')}
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                className={inputCls}
              />
            </FormField>

            <Button type="submit" loading={isSubmitting} className="w-full mt-2" size="lg">
              Iniciar sesión
            </Button>
          </form>
        </div>

        <div className="mt-6 text-center space-y-2">
          <Link
            to="/"
            className="block text-xs text-indigo-600 hover:underline"
          >
            ← Volver a documentos públicos
          </Link>
          <p className="text-xs text-slate-400">
            División de Ciencias y Artes para el Diseño · UAM Azcapotzalco
          </p>
        </div>
      </div>
    </div>
  )
}
