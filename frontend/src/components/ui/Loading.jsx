/**
 * Spinner de carga.
 * @param {boolean} fullscreen — ocupa toda la pantalla (para carga inicial)
 * @param {string}  text       — texto opcional debajo del spinner
 */
export default function Loading({ fullscreen = false, text = 'Cargando…' }) {
  const inner = (
    <div className="flex flex-col items-center gap-3">
      <svg
        className="h-8 w-8 animate-spin text-indigo-600"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
        />
      </svg>
      {text && <p className="text-sm text-slate-500">{text}</p>}
    </div>
  )

  if (fullscreen) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        {inner}
      </div>
    )
  }

  return <div className="flex items-center justify-center py-16">{inner}</div>
}
