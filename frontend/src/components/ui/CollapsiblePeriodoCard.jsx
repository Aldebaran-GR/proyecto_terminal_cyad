import { useEffect, useState } from 'react'

/**
 * Card colapsable por periodo — usada en las listas del profesor para agrupar
 * documentos y formularios. Por defecto abierta si `isActivo=true` o si es la
 * primera del listado; el usuario puede alternar clickeando el encabezado.
 */
export default function CollapsiblePeriodoCard({
  clave, fechaInicio, count, isActivo, defaultOpen, children,
}) {
  const [open, setOpen] = useState(defaultOpen ?? isActivo)

  // `isActivo` llega en `false` en el primer render mientras getPeriodosActivos()
  // sigue resolviendo (useState solo evalúa su inicial una vez). Cuando el
  // fetch resuelve y esta card resulta ser la activa, forzamos su apertura.
  useEffect(() => {
    if (isActivo) setOpen(true)
  }, [isActivo])
  const fechaFmt = fechaInicio
    ? new Date(fechaInicio + 'T00:00:00').toLocaleDateString('es-MX', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : null
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-slate-50 transition"
        aria-expanded={open}
      >
        <div className="flex items-center gap-3">
          <span className={`text-slate-400 transition-transform ${open ? 'rotate-90' : ''}`}>▶</span>
          <div>
            <p className="text-sm font-semibold text-slate-800">
              Periodo {clave}
              {isActivo && (
                <span className="ml-2 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-0.5">
                  Activo
                </span>
              )}
            </p>
            {fechaFmt && (
              <p className="text-xs text-slate-400">Inicio: {fechaFmt}</p>
            )}
          </div>
        </div>
        <span className="text-xs text-slate-500">{count} {count === 1 ? 'documento' : 'documentos'}</span>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-5 py-4">
          {children}
        </div>
      )}
    </section>
  )
}
