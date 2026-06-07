import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './auth/AuthContext'
import App from './App.jsx'
import './index.css'

/**
 * Configuración de TanStack Query orientada a **reactividad sin recargar**.
 *
 *   staleTime = 0           → tras cada respuesta el dato se marca "stale"
 *                              de inmediato; el siguiente render o focus lo
 *                              vuelve a pedir al backend.
 *   refetchOnWindowFocus    → al volver a la pestaña, refresca todas las
 *                              queries activas (clave para ver lo que el
 *                              admin acaba de publicar en otra sesión).
 *   refetchOnMount          → al montar un componente, refresca su query.
 *   refetchOnReconnect      → tras un corte de red, recupera al volver.
 *
 * Las páginas individuales pueden subir su `staleTime` cuando lo necesiten
 * (p. ej. catálogos que cambian poco) o agregar `refetchInterval` para
 * polling explícito.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 0,
      refetchOnWindowFocus: true,
      refetchOnMount: true,
      refetchOnReconnect: true,
    },
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>
)
