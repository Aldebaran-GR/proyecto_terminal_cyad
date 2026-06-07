/**
 * Layout compartido para las vistas públicas de documentos.
 *
 * No incluye sidebar ni nada de UAuth — está pensado para usuarios sin login.
 * Estilo print-friendly: fondo blanco, contenedor con maxWidth, tipografía
 * legible.
 */
export default function PublicDocumentLayout({ title, children }) {
  return (
    <div className="min-h-screen bg-slate-50 print:bg-white">
      {/* Header institucional simple */}
      <header className="border-b border-slate-200 bg-white print:border-0">
        <div className="mx-auto max-w-4xl px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-400">
              UAM Azcapotzalco · CyAD
            </p>
            <h1 className="text-sm font-semibold text-slate-800">{title}</h1>
          </div>
          <button
            onClick={() => window.print()}
            className="print:hidden text-xs text-indigo-600 hover:underline"
          >
            Imprimir
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8 print:py-2">{children}</main>

      <footer className="print:hidden mx-auto max-w-4xl px-6 py-6 text-center text-xs text-slate-400">
        Sistema de Proyecto Terminal CyAD — UAM Azcapotzalco
      </footer>
    </div>
  )
}

/* Bloque de campo (label + contenido) usado por ambas vistas públicas */
export function PublicField({ label, value, isLink = false, multiline = false }) {
  if (!value) return null
  return (
    <div className="border-b border-slate-100 py-3 last:border-0">
      <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">{label}</p>
      {isLink ? (
        <a
          href={value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-indigo-600 hover:underline break-all"
        >
          {value}
        </a>
      ) : (
        <p className={`text-sm text-slate-800 ${multiline ? 'whitespace-pre-wrap' : ''}`}>
          {value}
        </p>
      )}
    </div>
  )
}
